from __future__ import annotations

import json
import re
from typing import Any

from lexcapital.core.models import ActionType, ModelDecision

_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def default_hold_decision(
    step: int,
    reason: str,
    *,
    metadata: dict[str, Any] | None = None,
    confidence: float = 0.5,
) -> ModelDecision:
    meta: dict[str, Any] = {
        "defaulted_to_hold": True,
        "fallback_reason": reason,
        "invalid_output": True,
    }
    if metadata:
        meta.update(metadata)
    return ModelDecision(
        step=step,
        orders=[{"action": ActionType.HOLD}],
        rule_citations=[],
        risk_limit=None,
        confidence=max(0.0, min(1.0, confidence)),
        rationale_summary=f"Default HOLD because {reason}.",
        evidence_timestamps=[step],
        metadata=meta,
    )


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = _CODE_FENCE_RE.sub("", stripped).strip()
    return stripped


def extract_json_payload(raw: Any) -> dict[str, Any]:
    if isinstance(raw, ModelDecision):
        return raw.model_dump()
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise TypeError(f"Expected dict or JSON string, got {type(raw).__name__}")

    text = _strip_code_fence(raw)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        payload = json.loads(text[start : end + 1])
    if not isinstance(payload, dict):
        raise TypeError("Model output JSON must be an object")
    return payload


def parse_model_decision(raw: Any, expected_step: int) -> ModelDecision:
    payload = extract_json_payload(raw)
    decision = ModelDecision.model_validate(payload)

    update: dict[str, Any] = {}
    metadata = dict(decision.metadata or {})
    if decision.step != expected_step:
        metadata["step_mismatch_corrected"] = True
        metadata["original_step"] = decision.step
        update["step"] = expected_step
    if not decision.orders:
        metadata["empty_orders_defaulted_to_hold"] = True
        update["orders"] = [{"action": ActionType.HOLD}]
    if metadata != decision.metadata:
        update["metadata"] = metadata
    if update:
        data = decision.model_dump()
        data.update(update)
        return ModelDecision.model_validate(data)
    return decision
