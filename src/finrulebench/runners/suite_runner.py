from __future__ import annotations

import json
from pathlib import Path

from finrulebench.core.leaderboard import build_leaderboard
from finrulebench.runners.agent_runner import run_and_replay_agent_scenario
from finrulebench.runners.policy_runner import run_and_replay_scenario


def iter_scenario_paths(scenarios_path: str | Path):
    root = Path(scenarios_path)
    if root.is_file() and root.suffix in {".yaml", ".yml"}:
        yield root
        return
    for scenario_path in sorted(root.rglob("*.yaml")):
        if "rule_packs" in scenario_path.parts:
            continue
        yield scenario_path


def run_suite(scenarios_dir: str, adapter, run_config, out_dir: str) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "run_config.json").write_text(run_config.model_dump_json(indent=2), encoding="utf-8")
    (out / "model_card.json").write_text(
        json.dumps(
            {
                "model_name": run_config.model_name,
                "adapter_name": adapter.name,
                "provider": adapter.provider,
                "mode": run_config.mode,
                "temperature": run_config.temperature,
                "max_output_tokens": run_config.max_output_tokens,
                "tool_access": "benchmark_visible_tools" if run_config.mode == "agent" else "none",
                "internet_access": False,
                "filesystem_access": False,
                "real_trading_access": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    runner = run_and_replay_agent_scenario if run_config.mode == "agent" else run_and_replay_scenario
    for scenario_path in iter_scenario_paths(scenarios_dir):
        runner(scenario_path, adapter, run_config, out / scenario_path.stem)

    summary = build_leaderboard(str(out))
    summary.update({"provider": adapter.provider, "mode": run_config.mode, "model_name": run_config.model_name})
    (out / "suite_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (out / "leaderboard_row.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
