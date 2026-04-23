from __future__ import annotations

import json
from pathlib import Path

import yaml

from finrulebench.core.audit import audit_scenario, audit_scenarios


def _scenario_payload(**updates):
    payload = {
        "id": "AUDIT-HARDENING-001",
        "category": "no_context",
        "title": "Audit hardening no-edge scenario",
        "difficulty": "easy",
        "data_mode": "synthetic",
        "starting_cash": 100.0,
        "max_steps": 1,
        "question": "No reliable edge is visible. What should the model do?",
        "instruments": [],
        "public_rules": [
            {
                "id": "R1",
                "text": "When no reliable edge is visible, HOLD is acceptable.",
                "tags": ["calibration"],
            }
        ],
        "allowed_actions": ["HOLD", "BUY"],
        "timeline": [
            {
                "t": 0,
                "visible": {},
                "hidden_future": {"oracle_secret": "CANARY_HIDDEN_SECRET_BRAVO"},
            }
        ],
        "hidden_oracle_solution": {
            "summary": "The safe oracle path is to hold.",
            "allowed_strategy": "HOLD for the only step.",
            "disallowed_bait": "Trade on the hidden canary.",
            "expected_final_value": 100.0,
        },
        "trap_conditions": [
            {
                "id": "T1",
                "condition_type": "NO_CONTEXT_OVERTRADE",
                "params": {"max_notional_usd": 0},
                "effect": "SOFT_PENALTY",
                "severity": "medium",
                "description": "Trading without a visible edge is penalized by the private audit trap.",
            }
        ],
        "scoring": {
            "cash_baseline_value": 100.0,
            "oracle_final_value": 100.0,
            "key_rule_ids": ["R1"],
        },
        "expected_skill": ["calibration", "abstention"],
        "trap_type": "no_context_overtrade",
        "baseline_expectations": {"hold_score_min": 80},
    }
    payload.update(updates)
    return payload


def _write_scenario(path: Path, **updates) -> Path:
    path.write_text(yaml.safe_dump(_scenario_payload(**updates), sort_keys=False), encoding="utf-8")
    return path


def test_directory_audit_includes_yml_scenarios(tmp_path: Path):
    _write_scenario(tmp_path / "audit_yaml.yaml", id="AUDIT-YAML")
    _write_scenario(tmp_path / "audit_yml.yml", id="AUDIT-YML")

    report = audit_scenarios(tmp_path, run_replays=False)

    assert report["status"] == "pass"
    assert report["scenario_count"] == 2
    assert {entry["scenario_id"] for entry in report["scenarios"]} == {
        "AUDIT-YAML",
        "AUDIT-YML",
    }


def test_hidden_value_scan_covers_trap_condition_text(tmp_path: Path):
    trap_description = "Trading without a visible edge is penalized by the private audit trap."
    scenario_path = _write_scenario(
        tmp_path / "leaky_trap_text.yaml",
        timeline=[
            {
                "t": 0,
                "visible": {"memo": trap_description},
                "hidden_future": {"oracle_secret": "CANARY_HIDDEN_SECRET_BRAVO"},
            }
        ],
    )

    entry = audit_scenario(scenario_path, run_replays=False)

    assert entry["status"] == "fail"
    assert any(
        finding["kind"] == "hidden_value_leak" and trap_description[:40] in finding["value"]
        for finding in entry["hidden_leakage_failures"]
    )


def test_public_tokens_reused_in_hidden_sections_are_not_leakage(tmp_path: Path):
    public_token = "PUBLIC_CANARY_ACTION"
    scenario_path = _write_scenario(
        tmp_path / "public_token_reuse.yaml",
        question=f"The public benchmark token is {public_token}.",
        hidden_oracle_solution={
            "summary": public_token,
            "allowed_strategy": "HOLD for the only step.",
            "disallowed_bait": "Trade on the hidden canary.",
            "expected_final_value": 100.0,
        },
    )

    entry = audit_scenario(scenario_path, run_replays=False)

    assert entry["status"] == "pass"
    assert entry["hidden_leakage_failures"] == []


def test_red_sidecar_must_trigger_target_trap_not_unrelated_violation(tmp_path: Path):
    scenario_path = _write_scenario(tmp_path / "audit_001.yaml")
    red_path = tmp_path / "audit_001_red.jsonl"
    red_path.write_text(
        json.dumps(
            {
                "step": 0,
                "orders": [
                    {"action": "BUY", "instrument_id": "UNKNOWN", "notional_usd": 0}
                ],
                "rule_citations": ["R1"],
                "confidence": 0.8,
                "rationale_summary": "This should only create an unrelated execution violation.",
                "evidence_timestamps": [0],
                "metadata": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = audit_scenarios(tmp_path, out=tmp_path / "audit")
    entry = report["scenarios"][0]

    assert report["status"] == "fail"
    assert report["red_paths_found"] == 1
    assert report["red_path_trigger_rate"] == 0.0
    assert entry["red_replay"]["violation_count"] > 0
    assert entry["red_replay"]["target_trap_violation_count"] == 0
    assert "red_path_did_not_trigger_target_trap" in entry["errors"]
