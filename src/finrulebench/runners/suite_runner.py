from __future__ import annotations

import json
from pathlib import Path

from finrulebench.core.leaderboard import build_leaderboard
from finrulebench.core.scenario_loader import load_scenarios_dir
from finrulebench.runners.policy_runner import run_and_replay_scenario


def run_suite(scenarios_dir: str, adapter, run_config, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'run_config.json').write_text(run_config.model_dump_json(indent=2), encoding='utf-8')
    (out / 'model_card.json').write_text(json.dumps({'model_name': adapter.name, 'provider': adapter.provider, 'mode': run_config.mode}, indent=2), encoding='utf-8')
    for scenario_path in sorted(Path(scenarios_dir).glob('*.yaml')):
        run_and_replay_scenario(scenario_path, adapter, run_config, out / scenario_path.stem)
    summary = build_leaderboard(str(out))
    (out / 'suite_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (out / 'leaderboard_row.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
