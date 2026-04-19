from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print as rprint

from lexcapital.adapters.file_adapter import FileAdapter
from lexcapital.adapters.local_http import LocalHTTPAdapter
from lexcapital.adapters.mock_adapter import MockAdapter
from lexcapital.adapters.openai_responses import OpenAIResponsesAdapter
from lexcapital.adapters.utils import default_hold_decision, parse_model_decision
from lexcapital.agent_integration import (
    config_has_placeholders,
    default_self_eval_config,
    load_agent_eval_config,
    save_agent_eval_request,
    write_agent_eval_template,
)
from lexcapital.core.execution import execute_decision
from lexcapital.core.hashing import canonical_json
from lexcapital.core.leaderboard import build_leaderboard
from lexcapital.core.portfolio import Portfolio
from lexcapital.core.prompt_renderer import render_model_prompt
from lexcapital.core.replay import replay_scenario
from lexcapital.core.scenario_loader import load_scenario, load_scenarios_dir
from lexcapital.policies.baseline_hold import make_hold_decisions
from lexcapital.runners.agent_runner import (
    collect_agent_actions_for_scenario,
    run_and_replay_agent_scenario,
)
from lexcapital.runners.policy_runner import collect_actions_for_scenario, run_and_replay_scenario
from lexcapital.runners.run_config import RunConfig
from lexcapital.runners.suite_runner import run_suite as run_suite_impl

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


def _load_existing_decisions(actions_path: Path, max_steps: int):
    decisions = {}
    if not actions_path.exists():
        return decisions
    with actions_path.open("r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f):
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                payload = json.loads(raw_line)
                step = int(payload.get("step", line_number)) if isinstance(payload, dict) else line_number
                if step < 0 or step >= max_steps:
                    step = min(line_number, max_steps - 1)
                decisions[step] = parse_model_decision(payload, step)
            except Exception:
                continue
    return decisions


def _next_prompt_from_actions(scenario_path: str, actions_path: Path):
    scenario = load_scenario(scenario_path)
    decisions = _load_existing_decisions(actions_path, scenario.max_steps)
    portfolio = Portfolio(scenario.starting_cash)
    for step in range(scenario.max_steps):
        prices = scenario.timeline[step].visible.get("prices", {})
        if step not in decisions:
            state = portfolio.state(step, prices)
            prompt = render_model_prompt(scenario, step, state)
            return {"done": False, "next_step": step, "prompt": prompt}
        decision = decisions[step]
        execute_decision(scenario, portfolio, decision, step)
        portfolio.mark_to_market(step, prices)
    return {"done": True, "next_step": None, "prompt": None}


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


@app.command("render-next")
def render_next(
    scenario: str = typer.Option(..., "--scenario"),
    actions: str = typer.Option(..., "--actions"),
    create_if_missing: bool = typer.Option(True, "--create-if-missing/--no-create-if-missing"),
):
    actions_path = Path(actions)
    if create_if_missing:
        actions_path.parent.mkdir(parents=True, exist_ok=True)
        if not actions_path.exists():
            actions_path.write_text("", encoding="utf-8")
    payload = _next_prompt_from_actions(scenario, actions_path)
    typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))


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
    if config_has_placeholders(cfg):
        raise typer.BadParameter(
            "agent_eval config still contains __CURRENT_AGENT_*__ placeholders. "
            "Replace them or use `python -m lexcapital self-eval ...`."
        )
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


@app.command("self-eval")
def self_eval(
    adapter: str | None = typer.Option(None, "--adapter"),
    model: str | None = typer.Option(None, "--model"),
    scenarios: str = typer.Option("scenarios/mvp", "--scenarios"),
    out: str | None = typer.Option(None, "--out"),
    file_path: str | None = typer.Option(None, "--file-path"),
    base_url: str | None = typer.Option(None, "--base-url"),
    mode: str = typer.Option("agent", "--mode"),
    temperature: float = typer.Option(0.0, "--temperature"),
    max_output_tokens: int = typer.Option(1200, "--max-output-tokens"),
    timeout_seconds: int = typer.Option(60, "--timeout-seconds"),
    max_retries: int = typer.Option(1, "--max-retries"),
):
    cfg = default_self_eval_config(
        adapter=adapter,
        model=model,
        mode=mode,
        scenarios=scenarios,
        out=out,
        file_path=file_path,
        base_url=base_url,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )
    if config_has_placeholders(cfg):
        raise typer.BadParameter(
            "Could not infer the current coding agent's provider/model. "
            "Pass --adapter/--model, or set LEXCAPITAL_AGENT_ADAPTER and LEXCAPITAL_AGENT_MODEL. "
            "If you want to evaluate the current coding agent without a provider API, use the render-next loop documented in AGENTS.md."
        )
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
