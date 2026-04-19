from __future__ import annotations

from finrulebench.core.models import ActionType, ModelDecision, RiskLimit


def make_hold_decisions(max_steps: int) -> list[ModelDecision]:
    decisions = []
    for step in range(max_steps):
        decisions.append(
            ModelDecision(
                step=step,
                orders=[{'action': ActionType.HOLD}],
                rule_citations=[],
                risk_limit=RiskLimit(max_loss_usd=0, max_drawdown_pct=0, max_position_usd=0),
                confidence=0.5,
                rationale_summary='No trade; preserving cash.',
                evidence_timestamps=[step],
                metadata={},
            )
        )
    return decisions
