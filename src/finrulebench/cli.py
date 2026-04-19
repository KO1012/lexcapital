from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print as rprint

from finrulebench.adapters.file_adapter import FileAdapter
from finrulebench.adapters.local_http import LocalHTTPAdapter
from finrulebench.adapters.mock_adapter import MockAdapter
from finrulebench.adapters.openai_responses import OpenAIResponsesAdapter
from finrulebench.adapters.utils import default_hold_decision, parse_model_decision
from finrulebench.agent_integration import (
    load_agent_eval_config,
    save_agent_eval_request,
    write_agent_eval_template,
)
from finrulebench.core.hashing import canonical_json
from finrulebench.core.leaderboard import build_leaderboard
from finrulebench.core.portfolio import Portfolio
from finrulebench.core.prompt_renderer import render_model_prompt
from finrulebench.core.replay import replay_scenario
from finrulebench.core.scenario_loader import load_scenario, load_scenarios_dir
from finrulebench.policies.baseline_hold import make_hold_decisions
from finrulebench.runners.agent_runner import (
    collect_agent_actions_for_scenario,
    run_and_replay_agent_scenario,
)
from finrulebench.runners.policy_runner import collect_actions_for_scenario, run_and_replay_scenario
from finrulebench.runners.run_config import RunConfig
from finrulebench.runners.suite_runner import run_suite as run_suite_impl

app = typer.Typer(no_args_is_help=True)


def _adapter_from_name(
    adapter: str,
    model: str,
    file_path: str | None = None,
    base_url: str | None = None,
):
    key = adapter.lower().replace("-", "_")
    if key == "mock":
        return MockAdapter(model)
    if key == "file":
        if not file_path:
            raise typer.BadParameter("--file-path is required for file adapter")
        return FileAdapter(file_path)
    if key in {"local_http", "local"}:
        return LocalHTTPAdapter(base_url or "http://localhost:8000")
    if key in {"openai", "openai_responses", "responses"}:
        return OpenAIResponsesAdapter()
    raise typer.BadParameter(f"Unknown adapter: {adapter}")


def _run_config(
    model: str,
    adapter: str,
    mode: str,
    temperature: float,
    max_output_tokens: int,
    timeout_seconds: int,
    max_retries: int,
    base_url: str | None,
) -> RunConfig:
    if mode not in {"policy", "agent"}:
        raise typer.BadParameter("--mode must be policy or agent")
    return RunConfig(
        model_name=model,
        provider=adapter,
        mode=mode,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        base_url=base_url,
    )


@app.command()
def validate(paths: list[str] = typer.Argument(...)):
    count = 0
    for raw_path in paths:
        entries = load_scenarios_dir(raw_path)
        count += len(entries)
    rprint({"validated": count})


@app.command("render-prompt")
def render_prompt(
    scenario: str = typer.Option(..., "--scenario"),
    step: int = typer.Option(0, "--step"),
):
    loaded = load_scenario(scenario)
    portfolio = Portfolio(loaded.starting_cash)
    prompt = render_model_prompt(
        loaded, step, portfolio.state(step, loaded.timeline[step].visible.get("prices", {}))
    )
    typer.echo(json.dumps(prompt, ensure_ascii=False, indent=2))


@app.command()
def replay(
    scenario: str = typer.Option(..., "--scenario"),
    actions: str = typer.Option(..., "--actions"),
    out: str = typer.Option(..., "--out"),
):
    result = replay_scenario(scenario, actions, out)
    typer.echo(result.model_dump_json(indent=2))


@app.command("score-dir")
def score_dir(path: str):
    summary = build_leaderboard(path)
    typer.echo(json.dumps(summary, indent=2))


@app.command("make-hold-actions")
def make_hold_actions(
    scenario: str = typer.Option(..., "--scenario"),
    out: str = typer.Option(..., "--out"),
):
    loaded = load_scenario(scenario)
    decisions = make_hold_decisions(loaded.max_steps)
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for decision in decisions:
            f.write(json.dumps(decision.model_dump(), ensure_ascii=False) + "\n")
    typer.echo(str(out_path))


@app.command("write-agent-template")
def write_agent_template(
    out: str = typer.Option("agent_eval.example.yaml", "--out"),
):
    path = write_agent_eval_template(out)
    typer.echo(str(path))


@app.command("agent-eval")
def agent_eval(
    config: str = typer.Option(..., "--config"),
):
    cfg = load_agent_eval_config(config)
    run_config = _run_config(
        cfg.model,
        cfg.adapter,
        cfg.mode,
        cfg.temperature,
        cfg.max_output_tokens,
        cfg.timeout_seconds,
        cfg.max_retries,
        cfg.base_url,
    )
    adapter_obj = _adapter_from_name(
        cfg.adapter,
        cfg.model,
        file_path=cfg.file_path,
        base_url=cfg.base_url,
    )
    save_agent_eval_request(cfg, cfg.out)
    run_suite_impl(cfg.scenarios, adapter_obj, run_config, cfg.out)
    summary = build_leaderboard(cfg.out)
    typer.echo(json.dumps(summary, indent=2))


@app.command("collect-actions")
def collect_actions(
    scenario: str = typer.Option(..., "--scenario"),
    adapter: str = typer.Option("mock", "--adapter"),
    model: str = typer.Option("mock-hold", "--model"),
    out_actions: str = typer.Option(..., "--out-actions"),
    out_log: str = typer.Option(..., "--out-log"),
    file_path: str | None = typer.Option(None, "--file-path"),
    base_url: str | None = typer.Option(None, "--base-url"),
    mode: str = typer.Option("policy", "--mode"),
    temperature: float = typer.Option(0.0, "--temperature"),
    max_output_tokens: int = typer.Option(1200, "--max-output-tokens"),
    timeout_seconds: int = typer.Option(60, "--timeout-seconds"),
    max_retries: int = typer.Option(1, "--max-retries"),
):
    run_config = _run_config(
        model, adapter, mode, temperature, max_output_tokens, timeout_seconds, max_retries, base_url
    )
    adapter_obj = _adapter_from_name(adapter, model, file_path=file_path, base_url=base_url)
    collector = collect_agent_actions_for_scenario if mode == "agent" else collect_actions_for_scenario
    collector(scenario, adapter_obj, run_config, out_actions, out_log)
    typer.echo(out_actions)


@app.command("run-scenario")
def run_scenario(
    scenario: str = typer.Option(..., "--scenario"),
    adapter: str = typer.Option("mock", "--adapter"),
    model: str = typer.Option("mock-hold", "--model"),
    out: str = typer.Option("runs/mock_scenario", "--out"),
    file_path: str | None = typer.Option(None, "--file-path"),
    base_url: str | None = typer.Option(None, "--base-url"),
    mode: str = typer.Option("policy", "--mode"),
    temperature: float = typer.Option(0.0, "--temperature"),
    max_output_tokens: int = typer.Option(1200, "--max-output-tokens"),
    timeout_seconds: int = typer.Option(60, "--timeout-seconds"),
    max_retries: int = typer.Option(1, "--max-retries"),
):
    run_config = _run_config(
        model, adapter, mode, temperature, max_output_tokens, timeout_seconds, max_retries, base_url
    )
    adapter_obj = _adapter_from_name(adapter, model, file_path=file_path, base_url=base_url)
    runner = run_and_replay_agent_scenario if mode == "agent" else run_and_replay_scenario
    result = runner(scenario, adapter_obj, run_config, out)
    typer.echo(result.model_dump_json(indent=2))


@app.command("run-suite")
def run_suite(
    scenarios: str = typer.Option(..., "--scenarios"),
    adapter: str = typer.Option("mock", "--adapter"),
    model: str = typer.Option("mock-hold", "--model"),
    out: str = typer.Option("runs/mock_suite", "--out"),
    file_path: str | None = typer.Option(None, "--file-path"),
    base_url: str | None = typer.Option(None, "--base-url"),
    mode: str = typer.Option("policy", "--mode"),
    temperature: float = typer.Option(0.0, "--temperature"),
    max_output_tokens: int = typer.Option(1200, "--max-output-tokens"),
    timeout_seconds: int = typer.Option(60, "--timeout-seconds"),
    max_retries: int = typer.Option(1, "--max-retries"),
):
    run_config = _run_config(
        model, adapter, mode, temperature, max_output_tokens, timeout_seconds, max_retries, base_url
    )
    adapter_obj = _adapter_from_name(adapter, model, file_path=file_path, base_url=base_url)
    run_suite_impl(scenarios, adapter_obj, run_config, out)
    typer.echo(out)


@app.command()
def play(
    scenario: str = typer.Option(..., "--scenario"),
    out: str = typer.Option("runs/human_play", "--out"),
):
    loaded = load_scenario(scenario)
    portfolio = Portfolio(loaded.starting_cash)
    out_dir = Path(out) / loaded.id
    out_dir.mkdir(parents=True, exist_ok=True)
    actions_path = out_dir / "actions.jsonl"
    with actions_path.open("w", encoding="utf-8") as f:
        for step in range(loaded.max_steps):
            prompt = render_model_prompt(
                loaded,
                step,
                portfolio.state(step, loaded.timeline[step].visible.get("prices", {})),
            )
            typer.echo(json.dumps(prompt, ensure_ascii=False, indent=2))
            raw = typer.prompt("Paste ModelDecision JSON for this step")
            try:
                decision = parse_model_decision(raw, step)
            except Exception as exc:
                decision = default_hold_decision(
                    step,
                    "invalid human JSON",
                    metadata={"human_input_error": f"{type(exc).__name__}: {exc}"},
                )
            f.write(canonical_json(decision.model_dump()) + "\n")
    result = replay_scenario(scenario, str(actions_path), str(out_dir))
    typer.echo(result.model_dump_json(indent=2))
