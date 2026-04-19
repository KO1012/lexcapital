from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import httpx

from finrulebench.adapters.utils import default_hold_decision, parse_model_decision
from finrulebench.core.models import ModelDecision


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class LocalHTTPAdapter:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    @property
    def name(self) -> str:
        return "local-http"

    @property
    def provider(self) -> str:
        return "local_http"

    def _chat_url(self, run_config: Any) -> str:
        base = (getattr(run_config, "base_url", None) or self.base_url).rstrip("/")
        if base.endswith("/v1/chat/completions"):
            return base
        return f"{base}/v1/chat/completions"

    def _post_json(self, url: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    def _extract_content(self, data: dict[str, Any]) -> str:
        if "choices" in data:
            message = data["choices"][0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, list):
                return "".join(
                    str(item.get("text") or item.get("content") or "")
                    if isinstance(item, dict)
                    else str(item)
                    for item in content
                )
            return str(content)
        if "response" in data:
            return str(data["response"])
        if "output" in data:
            return json.dumps(data["output"], ensure_ascii=False)
        return json.dumps(data, ensure_ascii=False)

    def decide(self, prompt, decision_schema, run_config) -> ModelDecision:
        step = int(prompt["step"])
        errors: list[str] = []
        attempts = max(0, int(getattr(run_config, "max_retries", 1))) + 1
        payload = {
            "model": run_config.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are being evaluated in FinRuleBench. Return only JSON matching "
                        "the ModelDecision schema. Do not output markdown or chain-of-thought."
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
            "temperature": run_config.temperature,
            "max_tokens": run_config.max_output_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ModelDecision",
                    "schema": decision_schema,
                    "strict": False,
                },
            },
        }
        for attempt in range(attempts):
            started = time.monotonic()
            try:
                data = self._post_json(
                    self._chat_url(run_config),
                    payload,
                    float(getattr(run_config, "timeout_seconds", 60)),
                )
                raw_text = self._extract_content(data)
                decision = parse_model_decision(raw_text, step)
                metadata = dict(decision.metadata or {})
                metadata.update(
                    {
                        "provider": "local_http",
                        "adapter": self.name,
                        "attempt": attempt,
                        "latency_seconds": round(time.monotonic() - started, 6),
                        "raw_response_sha256": _sha256(raw_text),
                        "usage": data.get("usage", {}),
                    }
                )
                model_payload = decision.model_dump()
                model_payload["metadata"] = metadata
                return ModelDecision.model_validate(model_payload)
            except Exception as exc:
                errors.append(f"attempt {attempt}: {type(exc).__name__}: {exc}")
        return default_hold_decision(
            step,
            "Local HTTP adapter failed to produce a valid ModelDecision",
            metadata={"provider": "local_http", "adapter": self.name, "errors": errors},
        )
