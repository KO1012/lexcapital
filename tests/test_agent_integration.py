from __future__ import annotations

import json
from pathlib import Path

import yaml
from typer.testing import CliRunner

from finrulebench.agent_integration import (
    CURRENT_AGENT_ADAPTER,
    CURRENT_AGENT_MODEL,
    AgentEvalConfig,
    config_has_placeholders,
    default_self_eval_config,
    load_agent_eval_config,
    save_agent_eval_request,
    write_agent_eval_template,
)
from finrulebench.cli import app

from .conftest import ROOT

runner = CliRunner()


def test_write_and_load_agent_eval_template(tmp_path: Path):
    config_path = tmp_path / "agent_eval.yaml"
    write_agent_eval_template(config_path)
    cfg = load_agent_eval_config(config_path)
    assert cfg.adapter == CURRENT_AGENT_ADAPTER
    assert cfg.mode == "agent"
    assert cfg.model == CURRENT_AGENT_MODEL
    assert config_has_placeholders(cfg) is True


def test_default_self_eval_config_infers_env(monkeypatch):
    monkeypatch.setenv("FINRULEBENCH_AGENT_ADAPTER", "mock")
    monkeypatch.setenv("FINRULEBENCH_AGENT_MODEL", "mock-hold")
    cfg = default_self_eval_config()
    assert cfg.adapter == "mock"
    assert cfg.model == "mock-hold"
    assert config_has_placeholders(cfg) is False


def test_save_agent_eval_request(tmp_path: Path):
    cfg = AgentEvalConfig(model="mock-hold", adapter="mock", out=str(tmp_path / "runs"))
    request_path = save_agent_eval_request(cfg, cfg.out)
    payload = json.loads(request_path.read_text(encoding="utf-8"))
    assert payload["model"] == "mock-hold"
    assert payload["adapter"] == "mock"


def test_agent_eval_cli_writes_request_and_prints_summary(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "agent_eval.yaml"
    config_payload = {
        "adapter": "mock",
        "model": "mock-hold",
        "mode": "agent",
        "scenarios": str(ROOT / "scenarios" / "mvp"),
        "out": str(tmp_path / "runs"),
    }
    config_path.write_text(yaml.safe_dump(config_payload, sort_keys=False), encoding="utf-8")

    def fake_run_suite(scenarios, adapter_obj, run_config, out):
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "suite_summary.json").write_text(json.dumps({"overall_score": 12.34}), encoding="utf-8")

    monkeypatch.setattr("finrulebench.cli.run_suite_impl", fake_run_suite)
    monkeypatch.setattr("finrulebench.cli.build_leaderboard", lambda path: {"overall_score": 12.34})

    result = runner.invoke(app, ["agent-eval", "--config", str(config_path)])
    assert result.exit_code == 0
    assert "12.34" in result.stdout
    assert (tmp_path / "runs" / "agent_eval_request.json").exists()


def test_self_eval_cli_uses_env_and_writes_request(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FINRULEBENCH_AGENT_ADAPTER", "mock")
    monkeypatch.setenv("FINRULEBENCH_AGENT_MODEL", "mock-hold")

    def fake_run_suite(scenarios, adapter_obj, run_config, out):
        out_path = Path(out)
        out_path.mkdir(parents=True, exist_ok=True)
        (out_path / "suite_summary.json").write_text(json.dumps({"overall_score": 7.89}), encoding="utf-8")

    monkeypatch.setattr("finrulebench.cli.run_suite_impl", fake_run_suite)
    monkeypatch.setattr("finrulebench.cli.build_leaderboard", lambda path: {"overall_score": 7.89})

    out_dir = tmp_path / "self_eval"
    result = runner.invoke(
        app,
        [
            "self-eval",
            "--scenarios",
            str(ROOT / "scenarios" / "mvp"),
            "--out",
            str(out_dir),
        ],
    )
    assert result.exit_code == 0
    assert "7.89" in result.stdout
    assert (out_dir / "agent_eval_request.json").exists()


def test_render_next_cli_returns_first_prompt(tmp_path: Path):
    scenario = ROOT / "scenarios" / "mvp" / "noctx_001_no_edge_hold.yaml"
    actions = tmp_path / "actions.jsonl"
    result = runner.invoke(
        app,
        [
            "render-next",
            "--scenario",
            str(scenario),
            "--actions",
            str(actions),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["done"] is False
    assert payload["next_step"] == 0
    assert payload["prompt"]["scenario_id"] == "NOCTX-001"


def test_render_next_cli_advances_after_one_action(tmp_path: Path):
    scenario = ROOT / "scenarios" / "mvp" / "noctx_001_no_edge_hold.yaml"
    actions = tmp_path / "actions.jsonl"
    actions.write_text(
        json.dumps(
            {
                "step": 0,
                "orders": [{"action": "HOLD"}],
                "rule_citations": [],
                "risk_limit": None,
                "confidence": 0.5,
                "rationale_summary": "Hold.",
                "evidence_timestamps": [0],
                "metadata": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "render-next",
            "--scenario",
            str(scenario),
            "--actions",
            str(actions),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["done"] is False
    assert payload["next_step"] == 1
