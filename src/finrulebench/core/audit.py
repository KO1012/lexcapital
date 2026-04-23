from __future__ import annotations

import json
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from finrulebench.core.hashing import canonical_json
from finrulebench.core.models import ActionType, ModelDecision, Scenario
from finrulebench.core.portfolio import Portfolio
from finrulebench.core.prompt_renderer import render_model_prompt
from finrulebench.core.replay import replay_scenario
from finrulebench.core.scenario_loader import load_scenario

FORBIDDEN_PROMPT_KEYS = {
    "hidden_oracle_solution",
    "trap_conditions",
    "hidden_future",
    "scoring",
    "notes_for_authors",
    "private_tip",
}

ORACLE_ACTION_SUFFIXES = (
    ".oracle.jsonl",
    "_oracle.jsonl",
    ".oracle_actions.jsonl",
    "_oracle_actions.jsonl",
)
RED_ACTION_SUFFIXES = (
    ".red.jsonl",
    "_red.jsonl",
    ".red_actions.jsonl",
    "_red_actions.jsonl",
)


class ScenarioAuditError(RuntimeError):
    """Raised when a scenario audit cannot be completed."""


def iter_scenario_yaml_paths(path: str | Path) -> list[Path]:
    """Return scenario YAML files under *path*, excluding rule-pack registries."""

    root = Path(path)
    if root.is_file() and root.suffix in {".yaml", ".yml"}:
        return [root]
    if not root.exists():
        raise ScenarioAuditError(f"Scenario path does not exist: {root}")
    scenario_paths = {
        scenario_path
        for pattern in ("*.yaml", "*.yml")
        for scenario_path in root.rglob(pattern)
    }
    return [
        scenario_path
        for scenario_path in sorted(scenario_paths)
        if "rule_packs" not in scenario_path.parts
    ]


def _jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return value


def _iter_keys(value: Any) -> Iterable[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _iter_keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_keys(item)


def _iter_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        if len(cleaned) >= 12:
            yield cleaned
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_strings(item)


def _hidden_payload(scenario: Scenario) -> dict[str, Any]:
    return {
        "hidden_oracle_solution": scenario.hidden_oracle_solution,
        "hidden_future": [step.hidden_future for step in scenario.timeline[: scenario.max_steps]],
        "trap_conditions": scenario.trap_conditions,
        "scoring": scenario.scoring,
        "notes_for_authors": scenario.notes_for_authors,
        "private_tip": getattr(scenario, "private_tip", None),
    }


def _render_prompt_leak_findings(scenario: Scenario) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    portfolio = Portfolio(scenario.starting_cash)
    hidden_strings = set(_iter_strings(_jsonable(_hidden_payload(scenario))))

    for step in range(scenario.max_steps):
        prices = scenario.timeline[step].visible.get("prices", {})
        prompt = render_model_prompt(scenario, step, portfolio.state(step, prices))
        prompt_payload = _jsonable(prompt)
        prompt_keys = set(_iter_keys(prompt_payload))
        rendered = canonical_json(prompt_payload)

        leaked_keys = sorted(prompt_keys & FORBIDDEN_PROMPT_KEYS)
        for key in leaked_keys:
            findings.append(
                {
                    "step": step,
                    "kind": "forbidden_prompt_key",
                    "value": key,
                    "message": f"Forbidden hidden key rendered into prompt: {key}",
                }
            )

        for hidden_value in sorted(hidden_strings):
            if hidden_value and hidden_value in rendered:
                findings.append(
                    {
                        "step": step,
                        "kind": "hidden_value_leak",
                        "value": hidden_value[:160],
                        "message": "Hidden oracle/future/trap/scoring text was rendered into the prompt.",
                    }
                )

    return findings


def _hold_decisions(max_steps: int) -> list[ModelDecision]:
    return [
        ModelDecision(
            step=step,
            orders=[{"action": ActionType.HOLD}],
            rule_citations=[],
            risk_limit=None,
            confidence=0.5,
            rationale_summary="Audit baseline HOLD.",
            evidence_timestamps=[step],
            metadata={"audit_baseline": "hold"},
        )
        for step in range(max_steps)
    ]


def _write_actions(path: Path, decisions: list[ModelDecision] | list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for decision in decisions:
            if hasattr(decision, "model_dump"):
                payload = decision.model_dump(mode="json")
            else:
                payload = decision
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _sidecar_candidates(
    scenario_path: Path, scenario: Scenario, suffixes: tuple[str, ...]
) -> list[Path]:
    candidates: list[Path] = []
    stems = {scenario_path.stem, scenario.id, scenario.id.lower()}
    for stem in sorted(stems):
        for suffix in suffixes:
            candidates.append(scenario_path.with_name(f"{stem}{suffix}"))
            candidates.append(scenario_path.parent / "actions" / f"{stem}{suffix}")
    return candidates


def _first_existing_sidecar(
    scenario_path: Path, scenario: Scenario, suffixes: tuple[str, ...]
) -> Path | None:
    for candidate in _sidecar_candidates(scenario_path, scenario, suffixes):
        if candidate.exists():
            return candidate
    return None


def _counter_to_dict(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _violation_to_dict(violation: Any) -> dict[str, Any]:
    payload = _jsonable(violation)
    return {
        "step": payload.get("step"),
        "trap_id": payload.get("trap_id"),
        "condition_type": payload.get("condition_type"),
        "effect": payload.get("effect"),
        "message": payload.get("message"),
        "hard_dq": payload.get("hard_dq"),
        "penalty_points": payload.get("penalty_points"),
    }


def _target_trap_violations(
    violations: Iterable[dict[str, Any]], scenario: Scenario
) -> list[dict[str, Any]]:
    target_ids = {trap.id for trap in scenario.trap_conditions}
    target_types = {trap.condition_type.value for trap in scenario.trap_conditions}
    return [
        violation
        for violation in violations
        if violation.get("trap_id") in target_ids
        and violation.get("condition_type") in target_types
    ]


def _audit_replay(
    scenario_path: Path,
    actions_path: Path,
    out_root: Path,
    run_name: str,
) -> dict[str, Any]:
    result = replay_scenario(str(scenario_path), str(actions_path), str(out_root / run_name))
    violations = [_violation_to_dict(violation) for violation in result.violations]
    return {
        "gate": result.gate,
        "final_value": result.final_value,
        "scenario_score": result.scenario_score,
        "violation_count": len(result.violations),
        "hard_dq_reason": result.hard_dq_reason,
        "violations": violations,
    }


def audit_scenario(
    scenario_path: str | Path,
    *,
    out_dir: str | Path | None = None,
    run_replays: bool = True,
) -> dict[str, Any]:
    """Audit one scenario and return a JSON-serializable report entry."""

    path = Path(scenario_path)
    entry: dict[str, Any] = {
        "path": str(path),
        "scenario_id": None,
        "status": "fail",
        "errors": [],
        "warnings": [],
        "hidden_leakage_failures": [],
        "hold_baseline": None,
        "oracle_path": None,
        "oracle_replay": None,
        "red_path": None,
        "red_replay": None,
        "red_target_trap_violations": [],
    }

    try:
        scenario = load_scenario(path)
    except Exception as exc:  # noqa: BLE001 - reports should capture validation details.
        entry["errors"].append(f"load_failed: {type(exc).__name__}: {exc}")
        return entry

    entry.update(
        {
            "scenario_id": scenario.id,
            "category": scenario.category.value,
            "difficulty": scenario.difficulty.value,
            "data_mode": scenario.data_mode.value,
            "trap_condition_types": [
                trap.condition_type.value for trap in scenario.trap_conditions
            ],
            "target_trap_ids": [trap.id for trap in scenario.trap_conditions],
            "expected_skill": list(scenario.expected_skill),
            "trap_type": scenario.trap_type,
        }
    )

    leak_findings = _render_prompt_leak_findings(scenario)
    entry["hidden_leakage_failures"] = leak_findings
    if leak_findings:
        entry["errors"].append(f"hidden_prompt_leakage: {len(leak_findings)} finding(s)")

    if ActionType.HOLD not in scenario.allowed_actions:
        entry["errors"].append("HOLD is not in allowed_actions")

    if scenario.data_mode.value != "synthetic" and not scenario.provenance:
        entry["errors"].append("non-synthetic scenario is missing provenance")

    if run_replays:
        with tempfile.TemporaryDirectory(prefix="lexcapital_audit_") as tmp:
            tmp_root = Path(tmp)
            run_root = Path(out_dir) / "replays" if out_dir else tmp_root / "replays"

            hold_actions_path = tmp_root / f"{path.stem}.hold.jsonl"
            _write_actions(hold_actions_path, _hold_decisions(scenario.max_steps))
            hold = _audit_replay(path, hold_actions_path, run_root, f"{path.stem}_hold")
            entry["hold_baseline"] = hold
            if hold["gate"] != 1:
                entry["errors"].append("hold_baseline_dq")

            oracle_path = _first_existing_sidecar(path, scenario, ORACLE_ACTION_SUFFIXES)
            if oracle_path:
                entry["oracle_path"] = str(oracle_path)
                oracle = _audit_replay(path, oracle_path, run_root, f"{path.stem}_oracle")
                entry["oracle_replay"] = oracle
                if oracle["gate"] != 1:
                    entry["errors"].append("oracle_path_dq")
                if hold and oracle["scenario_score"] <= hold["scenario_score"]:
                    entry["warnings"].append("oracle_score_not_above_hold")

            red_path = _first_existing_sidecar(path, scenario, RED_ACTION_SUFFIXES)
            if red_path:
                entry["red_path"] = str(red_path)
                red = _audit_replay(path, red_path, run_root, f"{path.stem}_red")
                target_violations = _target_trap_violations(red["violations"], scenario)
                red["target_trap_violation_count"] = len(target_violations)
                red["target_trap_violations"] = target_violations
                entry["red_replay"] = red
                entry["red_target_trap_violations"] = target_violations
                if red["violation_count"] == 0:
                    entry["errors"].append("red_path_did_not_trigger_violation")
                if not target_violations:
                    entry["errors"].append("red_path_did_not_trigger_target_trap")
            else:
                entry["warnings"].append("no_red_path_sidecar_found")

    cash_baseline = float(scenario.scoring.cash_baseline_value)
    oracle_final = float(scenario.scoring.oracle_final_value)
    if abs(oracle_final - cash_baseline) < 0.01 and scenario.category.value != "no_context":
        entry["warnings"].append("oracle_final_value_close_to_cash_baseline")

    entry["status"] = "pass" if not entry["errors"] else "fail"
    return entry


def audit_scenarios(
    path: str | Path,
    *,
    out: str | Path | None = None,
    run_replays: bool = True,
) -> dict[str, Any]:
    """Audit all scenario YAML files under *path*."""

    scenario_paths = iter_scenario_yaml_paths(path)
    out_path = Path(out) if out else None
    if out_path:
        out_path.mkdir(parents=True, exist_ok=True)

    scenarios = [
        audit_scenario(scenario_path, out_dir=out_path, run_replays=run_replays)
        for scenario_path in scenario_paths
    ]

    difficulty_counter: Counter[str] = Counter()
    category_counter: Counter[str] = Counter()
    data_mode_counter: Counter[str] = Counter()
    trap_counter: Counter[str] = Counter()
    skill_counter: Counter[str] = Counter()

    for entry in scenarios:
        if entry.get("category"):
            category_counter[str(entry["category"])] += 1
        if entry.get("difficulty"):
            difficulty_counter[str(entry["difficulty"])] += 1
        if entry.get("data_mode"):
            data_mode_counter[str(entry["data_mode"])] += 1
        for trap_type in entry.get("trap_condition_types") or []:
            trap_counter[str(trap_type)] += 1
        for skill in entry.get("expected_skill") or []:
            skill_counter[str(skill)] += 1

    scenario_count = len(scenarios)
    failures = [entry for entry in scenarios if entry["status"] != "pass"]
    hidden_leak_failures = sum(len(entry["hidden_leakage_failures"]) for entry in scenarios)
    hold_runs = [entry["hold_baseline"] for entry in scenarios if entry.get("hold_baseline")]
    oracle_runs = [entry["oracle_replay"] for entry in scenarios if entry.get("oracle_replay")]
    red_runs = [entry["red_replay"] for entry in scenarios if entry.get("red_replay")]

    report = {
        "scenario_count": scenario_count,
        "status": "pass" if not failures else "fail",
        "failure_count": len(failures),
        "warning_count": sum(len(entry["warnings"]) for entry in scenarios),
        "hidden_leakage_failures": hidden_leak_failures,
        "hold_baseline_non_dq_rate": (
            sum(1 for run in hold_runs if run["gate"] == 1) / len(hold_runs) if hold_runs else None
        ),
        "oracle_paths_found": len(oracle_runs),
        "oracle_non_dq_rate": (
            sum(1 for run in oracle_runs if run["gate"] == 1) / len(oracle_runs)
            if oracle_runs
            else None
        ),
        "red_paths_found": len(red_runs),
        "red_path_trigger_rate": (
            sum(1 for run in red_runs if run.get("target_trap_violation_count", 0) > 0) / len(red_runs)
            if red_runs
            else None
        ),
        "difficulty_balance": _counter_to_dict(difficulty_counter),
        "category_balance": _counter_to_dict(category_counter),
        "data_mode_balance": _counter_to_dict(data_mode_counter),
        "trap_condition_balance": _counter_to_dict(trap_counter),
        "expected_skill_balance": _counter_to_dict(skill_counter),
        "scenarios": scenarios,
    }

    if out_path:
        (out_path / "audit_report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (out_path / "audit_summary.md").write_text(
            _audit_summary_markdown(report), encoding="utf-8"
        )

    return report


def _audit_summary_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# LexCapital scenario audit",
        "",
        f"Status: **{report['status']}**",
        f"Scenarios: **{report['scenario_count']}**",
        f"Failures: **{report['failure_count']}**",
        f"Warnings: **{report['warning_count']}**",
        f"Hidden leakage findings: **{report['hidden_leakage_failures']}**",
        "",
        "## Replay checks",
        "",
        f"Hold non-DQ rate: `{report['hold_baseline_non_dq_rate']}`",
        f"Oracle paths found: `{report['oracle_paths_found']}`",
        f"Oracle non-DQ rate: `{report['oracle_non_dq_rate']}`",
        f"Red paths found: `{report['red_paths_found']}`",
        f"Red target-trap trigger rate: `{report['red_path_trigger_rate']}`",
        "",
        "## Failed scenarios",
        "",
    ]
    failures = [entry for entry in report["scenarios"] if entry["status"] != "pass"]
    if not failures:
        lines.append("None.")
    else:
        for entry in failures:
            errors = "; ".join(entry["errors"])
            lines.append(f"- `{entry.get('scenario_id') or entry['path']}`: {errors}")
    lines.append("")
    return "\n".join(lines)
