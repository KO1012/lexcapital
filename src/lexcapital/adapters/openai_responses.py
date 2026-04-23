from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any

from lexcapital.adapters.utils import default_hold_decision, parse_model_decision
from lexcapital.core.errors import AdapterError
from lexcapital.core.models import ModelDecision


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _usage_to_dict(response: Any) -> dict[str, Any]:
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if usage is None:
        return {}
    if hasattr(usage, "model_dump"):
        return usage.model_dump()
    if isinstance(usage, dict):
        return dict(usage)
    return {k: getattr(usage, k) for k in dir(usage) if k.endswith("tokens") and not k.startswith("_")}


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    if hasattr(response, "model_dump"):
        response = response.model_dump()

    if isinstance(response, dict):
        if response.get("output_text"):
            return str(response["output_text"])
        if response.get("choices"):
            choice = response["choices"][0]
            message = choice.get("message", {})
            content = message.get("content", "")
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict):
                        parts.append(str(item.get("text") or item.get("content") or ""))
                    else:
                        parts.append(str(item))
                return "".join(parts)
            return str(content)
        if response.get("output"):
            parts = []
            for output_item in response["output"]:
                for content in output_item.get("content", []):
                    if isinstance(content, dict):
                        parts.append(str(content.get("text") or content.get("content") or ""))
            if parts:
                return "".join(parts)
    raise AdapterError("Could not extract text from OpenAI response")


class OpenAIResponsesAdapter:
    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    @property
    def name(self) -> str:
        return "openai-responses"

    @property
    def provider(self) -> str:
        return "openai"

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not os.getenv("OPENAI_API_KEY"):
            raise AdapterError(
                "OPENAI_API_KEY missing. Install optional deps with pip install -e '.[openai]'."
            )
        try:
            from openai import OpenAI  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise AdapterError("openai package is not installed. Run: pip install -e '.[openai]'.") from exc
        self._client = OpenAI()
        return self._client

    def _call_responses_api(
        self,
        client: Any,
        prompt: dict[str, Any],
        decision_schema: dict[str, Any],
        run_config: Any,
    ) -> tuple[str, dict[str, Any]]:
        if not hasattr(client, "responses"):
            raise AttributeError("client.responses unavailable")
        response = client.responses.create(
            model=run_config.model_name,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are being evaluated in LexCapital. Return only a JSON object "
                        "matching the supplied ModelDecision schema. Do not reveal chain-of-thought."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"visible_prompt": prompt, "decision_schema": decision_schema},
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=run_config.temperature,
            max_output_tokens=run_config.max_output_tokens,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "ModelDecision",
                    "schema": decision_schema,
                    "strict": False,
                }
            },
        )
        return _extract_response_text(response), _usage_to_dict(response)

    def _call_chat_fallback(
        self,
        client: Any,
        prompt: dict[str, Any],
        decision_schema: dict[str, Any],
        run_config: Any,
    ) -> tuple[str, dict[str, Any]]:
        if not hasattr(client, "chat"):
            raise AttributeError("client.chat unavailable")
        response = client.chat.completions.create(
            model=run_config.model_name,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only JSON matching the ModelDecision schema. "
                        "No markdown, no chain-of-thought."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"visible_prompt": prompt, "decision_schema": decision_schema},
                        ensure_ascii=False,
                    ),
                },
            ],
            temperature=run_config.temperature,
            max_tokens=run_config.max_output_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "ModelDecision",
                    "schema": decision_schema,
                    "strict": False,
                },
            },
        )
        return _extract_response_text(response), _usage_to_dict(response)

    def _call_model(
        self,
        client: Any,
        prompt: dict[str, Any],
        decision_schema: dict[str, Any],
        run_config: Any,
    ) -> tuple[str, dict[str, Any]]:
        try:
            return self._call_responses_api(client, prompt, decision_schema, run_config)
        except (AttributeError, TypeError):
            return self._call_chat_fallback(client, prompt, decision_schema, run_config)

    def decide(self, prompt, decision_schema, run_config) -> ModelDecision:
        step = int(prompt["step"])
        client = self._get_client()
        errors: list[str] = []
        attempts = max(0, int(getattr(run_config, "max_retries", 1))) + 1
        for attempt in range(attempts):
            started = time.monotonic()
            try:
                raw_text, usage = self._call_model(client, prompt, decision_schema, run_config)
                decision = parse_model_decision(raw_text, step)
                metadata = dict(decision.metadata or {})
                metadata.update(
                    {
                        "provider": "openai",
                        "adapter": self.name,
                        "attempt": attempt,
                        "latency_seconds": round(time.monotonic() - started, 6),
                        "usage": usage,
                        "raw_response_sha256": _hash_text(raw_text),
                    }
                )
                data = decision.model_dump()
                data["metadata"] = metadata
                return ModelDecision.model_validate(data)
            except Exception as exc:
                errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
        return default_hold_decision(
            step,
            "OpenAI adapter failed to produce a valid ModelDecision",
            metadata={"provider": "openai", "adapter": self.name, "errors": errors},
        )
