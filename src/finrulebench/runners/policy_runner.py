from __future__ import annotations

import json
from pathlib import Path

from finrulebench.core.execution import execute_decision
from finrulebench.core.hashing import canonical_json, sha256_json
from finrulebench.core.prompt_renderer import render_model_prompt
from finrulebench.core.replay import replay_scenario
from finrulebench.core.scenario_loader import load_scenario
from finrulebench.core.portfolio import Portfolio


def collect_actions_for_scenario(scenario_path, adapter, run_config, out_actions_jsonl, out_model_log_jsonl, out_rendered_prompts_jsonl=None):
    scenario = load_scenario(scenario_path)
    portfolio = Portfolio(scenario.starting_cash)
    actions_path = Path(out_actions_jsonl)
    actions_path.parent.mkdir(parents=True, exist_ok=True)
    model_log_path = Path(out_model_log_jsonl)
    model_log_path.parent.mkdir(parents=True, exist_ok=True)
    rendered_handle = Path(out_rendered_prompts_jsonl).open('w', encoding='utf-8') if out_rendered_prompts_jsonl else None
    with actions_path.open('w', encoding='utf-8') as actions_f, model_log_path.open('w', encoding='utf-8') as log_f:
        for step in range(scenario.max_steps):
            prices = scenario.timeline[step].visible.get('prices', {})
            state = portfolio.state(step, prices)
            prompt = render_model_prompt(scenario, step, state)
            decision = adapter.decide(prompt, prompt['required_output_schema'], run_config)
            actions_f.write(canonical_json(decision.model_dump()) + '\n')
            log_f.write(canonical_json({'step': step, 'prompt_hash': sha256_json(prompt), 'decision': decision.model_dump(), 'adapter': adapter.name}) + '\n')
            if rendered_handle:
                rendered_handle.write(canonical_json(prompt) + '\n')
            execute_decision(scenario, portfolio, decision, step)
            portfolio.mark_to_market(step, prices)
    if rendered_handle:
        rendered_handle.close()


def run_and_replay_scenario(scenario_path, adapter, run_config, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    collect_actions_for_scenario(
        scenario_path=scenario_path,
        adapter=adapter,
        run_config=run_config,
        out_actions_jsonl=out / 'actions.jsonl',
        out_model_log_jsonl=out / 'model_log.jsonl',
        out_rendered_prompts_jsonl=out / 'rendered_prompts.jsonl',
    )
    return replay_scenario(str(scenario_path), str(out / 'actions.jsonl'), str(out))
