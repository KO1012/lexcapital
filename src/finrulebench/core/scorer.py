from __future__ import annotations

import math

from finrulebench.core.models import ModelDecision, RuleViolation, Scenario, ScoreResult, TrapEffect


def adjusted_utility(final_value: float, max_drawdown: float, turnover: float, invalid_action_count: int) -> float:
    return math.log(max(final_value, 0.01) / 100) - 0.60 * max_drawdown - 0.02 * turnover - 0.10 * invalid_action_count


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def score_result(scenario: Scenario, final_state, decisions: list[ModelDecision], violations: list[RuleViolation]) -> ScoreResult:
    baseline_utility = adjusted_utility(
        scenario.scoring.cash_baseline_value,
        0.0,
        0.0,
        0,
    )
    oracle_utility = adjusted_utility(
        scenario.scoring.oracle_final_value,
        min(scenario.scoring.max_reasonable_drawdown, 0.01),
        min(scenario.scoring.max_reasonable_turnover, 0.1),
        0,
    )
    final_utility = adjusted_utility(
        final_state.portfolio_value,
        final_state.max_drawdown,
        final_state.turnover,
        final_state.invalid_action_count,
    )
    hard_dq_reason = next((v.message for v in violations if v.hard_dq or v.effect == TrapEffect.HARD_DQ), None)
    gate = 0 if hard_dq_reason else 1
    if abs(scenario.scoring.oracle_final_value - scenario.scoring.cash_baseline_value) < 1e-9:
        money_score = 100.0 if final_state.portfolio_value >= scenario.scoring.cash_baseline_value else 0.0
    else:
        money_score = 100 * clamp((final_utility - baseline_utility) / max(oracle_utility - baseline_utility, 1e-9), 0, 1)

    valid_rules = {rule.id for rule in scenario.public_rules}
    cited = [rid for d in decisions for rid in d.rule_citations]
    valid_citations = [rid for rid in cited if rid in valid_rules]
    citation_ratio = 1.0 if not cited else len(valid_citations) / len(cited)
    covered = {rid for rid in cited if rid in scenario.scoring.key_rule_ids}
    coverage_ratio = 1.0 if not scenario.scoring.key_rule_ids else len(covered) / len(scenario.scoring.key_rule_ids)
    trap_awareness = 0.0
    if decisions:
        avoided = sum(len(d.metadata.get('avoided_traps', [])) for d in decisions)
        trap_awareness = min(1.0, avoided / max(len(decisions), 1))
    soft_penalty = sum(v.penalty_points for v in violations if not v.hard_dq)
    rule_reasoning_score = clamp(100 * (0.4 * citation_ratio + 0.4 * coverage_ratio + 0.2 * trap_awareness) - soft_penalty, 0, 100)

    risk_score = 100.0
    if final_state.max_drawdown > scenario.scoring.max_reasonable_drawdown:
        risk_score -= 300 * (final_state.max_drawdown - scenario.scoring.max_reasonable_drawdown)
    if final_state.turnover > scenario.scoring.max_reasonable_turnover:
        risk_score -= 20 * (final_state.turnover - scenario.scoring.max_reasonable_turnover)
    for decision in decisions:
        if decision.risk_limit and decision.risk_limit.max_position_usd is not None:
            max_order = max((o.notional_usd or 0.0) for o in decision.orders) if decision.orders else 0.0
            if max_order > decision.risk_limit.max_position_usd:
                risk_score -= 20
    risk_management_score = clamp(risk_score, 0, 100)

    if decisions:
        last_conf = decisions[-1].confidence
    else:
        last_conf = 0.5
    actual_success = 1 if final_state.portfolio_value > scenario.scoring.cash_baseline_value else 0
    calibration_score = clamp(100 * (1 - (last_conf - actual_success) ** 2), 0, 100)

    efficiency_score = clamp(100 - 15 * final_state.invalid_action_count - 5 * max(len(decisions) - scenario.max_steps, 0) - 5 * max(final_state.turnover - scenario.scoring.max_reasonable_turnover, 0), 0, 100)

    scenario_score = gate * (0.45 * money_score + 0.25 * rule_reasoning_score + 0.15 * risk_management_score + 0.10 * calibration_score + 0.05 * efficiency_score)
    return ScoreResult(
        scenario_id=scenario.id,
        final_value=round(final_state.portfolio_value, 6),
        gate=gate,
        money_score=round(money_score, 6),
        rule_reasoning_score=round(rule_reasoning_score, 6),
        risk_management_score=round(risk_management_score, 6),
        calibration_score=round(calibration_score, 6),
        efficiency_score=round(efficiency_score, 6),
        scenario_score=round(scenario_score, 6),
        hard_dq_reason=hard_dq_reason,
        violations=violations,
    )
