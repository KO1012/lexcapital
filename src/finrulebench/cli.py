from __future__ import annotations

import json
from pathlib import Path

import typer
from rich import print as rprint

from finrulebench.adapters.file_adapter import FileAdapter
from finrulebench.adapters.local_http import LocalHTTPAdapter
from finrulebench.adapters.mock_adapter import MockAdapter
from finrulebench.adapters.openai_responses import OpenAIResponsesAdapter
from finrulebench.core.leaderboard import build_leaderboard
from finrulebench.core.prompt_renderer import render_model_prompt
from finrulebench.core.replay import replay_scenario
from finrulebench.core.scenario_loader import load_scenario, load_scenarios_dir, validate_scenario
from finrulebench.core.portfolio import Portfolio
from finrulebench.policies.baseline_hold import make_hold_decisions
from finrulebench.runners.policy_runner import run_and_replay_scenario
from finrulebench.runners.run_config import RunConfig
from finrulebench.runners.suite_runner import run_suite as run_suite_impl

app = typer.Typer(no_args_is_help=True)


def _adapter_from_name(adapter: str, model: str, file_path: str | None = None, base_url: str | None = None):
    if adapter == 'mock':
        return MockAdapter(model)
    if adapter == 'file':
        if not file_path:
            raise typer.BadParameter('--file-path is required for file adapter')
        return FileAdapter(file_path)
    if adapter == 'local_http':
        return LocalHTTPAdapter(base_url or 'http://localhost:8000')
    if adapter == 'openai':
        return OpenAIResponsesAdapter()
    raise typer.BadParameter(f'Unknown adapter: {adapter}')


@app.command()
def validate(paths: list[str] = typer.Argument(...)):
    count = 0
    for raw_path in paths:
        entries = load_scenarios_dir(raw_path)
        count += len(entries)
    rprint({'validated': count})


@app.command('render-prompt')
def render_prompt(scenario: str = typer.Option(..., '--scenario'), step: int = typer.Option(0, '--step')):
    loaded = load_scenario(scenario)
    portfolio = Portfolio(loaded.starting_cash)
    prompt = render_model_prompt(loaded, step, portfolio.state(step, loaded.timeline[step].visible.get('prices', {})))
    typer.echo(json.dumps(prompt, ensure_ascii=False, indent=2))


@app.command()
def replay(scenario: str = typer.Option(..., '--scenario'), actions: str = typer.Option(..., '--actions'), out: str = typer.Option(..., '--out')):
    result = replay_scenario(scenario, actions, out)
    typer.echo(result.model_dump_json(indent=2))


@app.command('score-dir')
def score_dir(path: str):
    summary = build_leaderboard(path)
    typer.echo(json.dumps(summary, indent=2))


@app.command('make-hold-actions')
def make_hold_actions(scenario: str = typer.Option(..., '--scenario'), out: str = typer.Option(..., '--out')):
    loaded = load_scenario(scenario)
    decisions = make_hold_decisions(loaded.max_steps)
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        for decision in decisions:
            f.write(json.dumps(decision.model_dump(), ensure_ascii=False) + '\n')
    typer.echo(str(out_path))


@app.command('run-scenario')
def run_scenario(scenario: str = typer.Option(..., '--scenario'), adapter: str = typer.Option('mock', '--adapter'), model: str = typer.Option('mock-hold', '--model'), out: str = typer.Option('runs/mock_scenario', '--out'), file_path: str | None = typer.Option(None, '--file-path'), base_url: str | None = typer.Option(None, '--base-url')):
    run_config = RunConfig(model_name=model, provider=adapter)
    adapter_obj = _adapter_from_name(adapter, model, file_path=file_path, base_url=base_url)
    result = run_and_replay_scenario(scenario, adapter_obj, run_config, out)
    typer.echo(result.model_dump_json(indent=2))


@app.command('run-suite')
def run_suite(scenarios: str = typer.Option(..., '--scenarios'), adapter: str = typer.Option('mock', '--adapter'), model: str = typer.Option('mock-hold', '--model'), out: str = typer.Option('runs/mock_suite', '--out'), file_path: str | None = typer.Option(None, '--file-path'), base_url: str | None = typer.Option(None, '--base-url')):
    run_config = RunConfig(model_name=model, provider=adapter)
    adapter_obj = _adapter_from_name(adapter, model, file_path=file_path, base_url=base_url)
    run_suite_impl(scenarios, adapter_obj, run_config, out)
    typer.echo(out)


@app.command()
def play(scenario: str = typer.Option(..., '--scenario')):
    loaded = load_scenario(scenario)
    typer.echo(json.dumps({'scenario_id': loaded.id, 'question': loaded.question, 'steps': loaded.max_steps}, indent=2))
