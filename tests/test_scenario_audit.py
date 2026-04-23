from __future__ import annotations

import json
from pathlib import Path

import yaml

from lexcapital.core.audit import audit_scenario, audit_scenarios


def _scenario_payload(**updates):
    payload = {
        "id": "AUDIT-001",
        "category": "no_context",
        "title": "Audit no-edge scenario",
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
                "hidden_future": {"oracle_secret": "CANARY_HIDDEN_SECRET_ALPHA"},
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
                "description": "Trading without a visible edge is penalized.",
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


def test_audit_scenario_generates_hold_baseline_and_counts_skills(tmp_path: Path):
    scenario_path = _write_scenario(tmp_path / "audit_001.yaml")

    report = audit_scenarios(tmp_path, out=tmp_path / "audit")

    assert report["status"] == "pass"
    assert report["scenario_count"] == 1
    assert report["hold_baseline_non_dq_rate"] == 1.0
    assert report["hidden_leakage_failures"] == 0
    assert report["expected_skill_balance"] == {"abstention": 1, "calibration": 1}
    assert (tmp_path / "audit" / "audit_report.json").exists()
    assert report["scenarios"][0]["path"] == str(scenario_path)


def test_audit_detects_visible_hidden_value_leak(tmp_path: Path):
    scenario_path = _write_scenario(
        tmp_path / "leaky.yaml",
        timeline=[
            {
                "t": 0,
                "visible": {"news": "CANARY_HIDDEN_SECRET_ALPHA"},
                "hidden_future": {"oracle_secret": "CANARY_HIDDEN_SECRET_ALPHA"},
            }
        ],
    )

    entry = audit_scenario(scenario_path, run_replays=False)

    assert entry["status"] == "fail"
    assert entry["hidden_leakage_failures"]
    assert entry["hidden_leakage_failures"][0]["kind"] == "hidden_value_leak"


def test_audit_red_sidecar_must_trigger_violation(tmp_path: Path):
    scenario_path = _write_scenario(tmp_path / "audit_001.yaml")
    red_path = tmp_path / "audit_001_red.jsonl"
    red_path.write_text(
        json.dumps(
            {
                "step": 0,
                "orders": [{"action": "BUY", "instrument_id": "UNKNOWN", "notional_usd": 10}],
                "rule_citations": ["R1"],
                "confidence": 0.8,
                "rationale_summary": "Overtrade despite no edge.",
                "evidence_timestamps": [0],
                "metadata": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = audit_scenarios(tmp_path, out=tmp_path / "audit")

    assert report["status"] == "pass"
    assert report["red_paths_found"] == 1
    assert report["red_path_trigger_rate"] == 1.0
    assert report["scenarios"][0]["red_path"] == str(red_path)
