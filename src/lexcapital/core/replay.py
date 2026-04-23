from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from lexcapital.adapters.utils import default_hold_decision, parse_model_decision
from lexcapital.core.execution import execute_decision
from lexcapital.core.hashing import canonical_json, sha256_json
from lexcapital.core.models import ModelDecision, RuleViolation, TrapConditionType, TrapEffect
from lexcapital.core.portfolio import Portfolio
from lexcapital.core.prompt_renderer import render_model_prompt
from lexcapital.core.rule_engine import evaluate_post_trade_traps, evaluate_pre_trade_traps
from lexcapital.core.scenario_loader import load_scenario
from lexcapital.core.scorer import score_result


def _invalid_output_violation(step: int, message: str) -> RuleViolation:
    return RuleViolation(
        step=step,
        trap_id="INVALID_MODEL_OUTPUT",
        condition_type=TrapConditionType.INVALID_RULE_CITATION,
        effect=TrapEffect.SOFT_PENALTY,
        message=message,
        hard_dq=False,
        penalty_points=8.0,
    )


def _missing_decision_violation(step: int) -> RuleViolation:
    return RuleViolation(
        step=step,
        trap_id="MISSING_MODEL_DECISION",
        condition_type=TrapConditionType.INVALID_RULE_CITATION,
        effect=TrapEffect.SOFT_PENALTY,
        message="No action was supplied for this step; defaulted to HOLD.",
        hard_dq=False,
        penalty_points=4.0,
    )


def _step_from_payload(payload: Any, fallback: int) -> int:
    if isinstance(payload, dict):
        raw_step = payload.get("step", fallback)
        try:
            return int(raw_step)
        except Exception:
            return fallback
    return fallback


def _load_actions(path: str | Path, max_steps: int) -> tuple[dict[int, ModelDecision], list[RuleViolation]]:
    decisions: dict[int, ModelDecision] = {}
    violations: list[RuleViolation] = []
    action_path = Path(path)
    if not action_path.exists():
        return decisions, [_invalid_output_violation(0, f"Actions file does not exist: {action_path}")]
    with action_path.open("r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            fallback_step = min(line_number, max(max_steps - 1, 0))
            try:
                payload = json.loads(raw_line)
                step = _step_from_payload(payload, fallback_step)
                if step < 0 or step >= max_steps:
                    step = fallback_step
                decision = parse_model_decision(payload, step)
                decisions[decision.step] = decision
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                step = fallback_step
                violations.append(
                    _invalid_output_violation(
                        step,
                        f"Invalid model output on line {line_number + 1}: {type(exc).__name__}: {exc}",
                    )
                )
                decisions[step] = default_hold_decision(
                    step,
                    "invalid action file line",
                    metadata={"line_number": line_number + 1},
                )
    return decisions, violations


def replay_scenario(scenario_path: str, actions_jsonl: str, out_dir: str):
    scenario = load_scenario(scenario_path)
    decisions_by_step, action_file_violations = _load_actions(actions_jsonl, scenario.max_steps)

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prompt_f = (out / "rendered_prompts.jsonl").open("w", encoding="utf-8")
    prompt_hash_f = (out / "prompt_hashes.jsonl").open("w", encoding="utf-8")
    action_hash_f = (out / "action_hashes.jsonl").open("w", encoding="utf-8")
    normalized_f = (out / "actions.normalized.jsonl").open("w", encoding="utf-8")
    trades_f = (out / "executed_trades.jsonl").open("w", encoding="utf-8")
    violations_f = (out / "rule_violations.jsonl").open("w", encoding="utf-8")
    portfolio_csv = (out / "portfolio_timeseries.csv").open("w", encoding="utf-8", newline="")
    writer = csv.DictWriter(
        portfolio_csv,
        fieldnames=[
            "step",
            "cash",
            "portfolio_value",
            "peak_value",
            "max_drawdown",
            "turnover",
            "gross_exposure",
            "invalid_action_count",
        ],
    )
    writer.writeheader()

    portfolio = Portfolio(scenario.starting_cash)
    all_decisions: list[ModelDecision] = []
    all_violations: list[RuleViolation] = list(action_file_violations)

    for violation in action_file_violations:
        violations_f.write(canonical_json(violation.model_dump()) + "\n")

    try:
        for step in range(scenario.max_steps):
            visible_prices = scenario.timeline[step].visible.get("prices", {})
            state_before = portfolio.state(step, visible_prices)
            prompt = render_model_prompt(scenario, step, state_before)
            prompt_f.write(canonical_json(prompt) + "\n")
            prompt_hash_f.write(canonical_json({"step": step, "sha256": sha256_json(prompt)}) + "\n")

            if step in decisions_by_step:
                decision = decisions_by_step[step]
            else:
                decision = default_hold_decision(step, "missing step in actions file")
                missing_violation = _missing_decision_violation(step)
                all_violations.append(missing_violation)
                violations_f.write(canonical_json(missing_violation.model_dump()) + "\n")

            all_decisions.append(decision)
            normalized_f.write(canonical_json(decision.model_dump()) + "\n")
            action_hash_f.write(canonical_json({"step": step, "sha256": sha256_json(decision.model_dump())}) + "\n")

            pre = evaluate_pre_trade_traps(scenario, state_before, decision, step)
            trades, exec_violations = execute_decision(scenario, portfolio, decision, step)
            state_after = portfolio.mark_to_market(step, visible_prices)
            post = evaluate_post_trade_traps(scenario, state_after, decision, trades, step)
            violations = pre + exec_violations + post
            all_violations.extend(violations)

            for trade in trades:
                trades_f.write(canonical_json(trade.model_dump()) + "\n")
            for violation in violations:
                violations_f.write(canonical_json(violation.model_dump()) + "\n")
            writer.writerow({key: getattr(state_after, key) for key in writer.fieldnames})

        final_state = portfolio.state(
            scenario.max_steps - 1,
            scenario.timeline[scenario.max_steps - 1].visible.get("prices", {}),
        )
        result = score_result(scenario, final_state, all_decisions, all_violations)
        (out / "score.json").write_text(canonical_json(result.model_dump()), encoding="utf-8")
        return result
    finally:
        for handle in [
            prompt_f,
            prompt_hash_f,
            action_hash_f,
            normalized_f,
            trades_f,
            violations_f,
            portfolio_csv,
        ]:
            handle.close()
