from __future__ import annotations

import csv
import json
from pathlib import Path

from finrulebench.core.execution import execute_decision
from finrulebench.core.hashing import canonical_json, sha256_json
from finrulebench.core.models import ActionType, ModelDecision
from finrulebench.core.portfolio import Portfolio
from finrulebench.core.prompt_renderer import render_model_prompt
from finrulebench.core.rule_engine import evaluate_post_trade_traps, evaluate_pre_trade_traps
from finrulebench.core.scenario_loader import load_scenario
from finrulebench.core.scorer import score_result


def _default_hold(step: int) -> ModelDecision:
    return ModelDecision(
        step=step,
        orders=[{'action': ActionType.HOLD}],
        rule_citations=[],
        risk_limit=None,
        confidence=0.5,
        rationale_summary='Missing decision; default HOLD.',
        evidence_timestamps=[step],
        metadata={'defaulted_to_hold': True},
    )


def _load_actions(path: str | Path) -> dict[int, ModelDecision]:
    decisions: dict[int, ModelDecision] = {}
    with Path(path).open('r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            decision = ModelDecision.model_validate(payload)
            decisions[decision.step] = decision
    return decisions


def replay_scenario(scenario_path: str, actions_jsonl: str, out_dir: str):
    scenario = load_scenario(scenario_path)
    decisions_by_step = _load_actions(actions_jsonl)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prompt_f = (out / 'rendered_prompts.jsonl').open('w', encoding='utf-8')
    prompt_hash_f = (out / 'prompt_hashes.jsonl').open('w', encoding='utf-8')
    action_hash_f = (out / 'action_hashes.jsonl').open('w', encoding='utf-8')
    normalized_f = (out / 'actions.normalized.jsonl').open('w', encoding='utf-8')
    trades_f = (out / 'executed_trades.jsonl').open('w', encoding='utf-8')
    violations_f = (out / 'rule_violations.jsonl').open('w', encoding='utf-8')
    portfolio_csv = (out / 'portfolio_timeseries.csv').open('w', encoding='utf-8', newline='')
    writer = csv.DictWriter(portfolio_csv, fieldnames=['step', 'cash', 'portfolio_value', 'peak_value', 'max_drawdown', 'turnover', 'gross_exposure', 'invalid_action_count'])
    writer.writeheader()

    portfolio = Portfolio(scenario.starting_cash)
    all_decisions = []
    all_violations = []
    for step in range(scenario.max_steps):
        visible_prices = scenario.timeline[step].visible.get('prices', {})
        state_before = portfolio.state(step, visible_prices)
        prompt = render_model_prompt(scenario, step, state_before)
        prompt_f.write(canonical_json(prompt) + '\n')
        prompt_hash_f.write(canonical_json({'step': step, 'sha256': sha256_json(prompt)}) + '\n')

        decision = decisions_by_step.get(step, _default_hold(step))
        all_decisions.append(decision)
        normalized_f.write(canonical_json(decision.model_dump()) + '\n')
        action_hash_f.write(canonical_json({'step': step, 'sha256': sha256_json(decision.model_dump())}) + '\n')

        pre = evaluate_pre_trade_traps(scenario, state_before, decision, step)
        trades, exec_violations = execute_decision(scenario, portfolio, decision, step)
        state_after = portfolio.mark_to_market(step, visible_prices)
        post = evaluate_post_trade_traps(scenario, state_after, decision, trades, step)
        violations = pre + exec_violations + post
        all_violations.extend(violations)
        for trade in trades:
            trades_f.write(canonical_json(trade.model_dump()) + '\n')
        for violation in violations:
            violations_f.write(canonical_json(violation.model_dump()) + '\n')
        writer.writerow({key: getattr(state_after, key) for key in writer.fieldnames})

    final_state = portfolio.state(scenario.max_steps - 1, scenario.timeline[scenario.max_steps - 1].visible.get('prices', {}))
    result = score_result(scenario, final_state, all_decisions, all_violations)
    (out / 'score.json').write_text(canonical_json(result.model_dump()), encoding='utf-8')
    for handle in [prompt_f, prompt_hash_f, action_hash_f, normalized_f, trades_f, violations_f, portfolio_csv]:
        handle.close()
    return result
