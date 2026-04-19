from __future__ import annotations

from pathlib import Path

import yaml

from finrulebench.core.errors import ScenarioValidationError
from finrulebench.core.legal_rules import load_rule_pack_registry
from finrulebench.core.models import ActionType, DataMode, Scenario, TrapConditionType


def _normalize_keys(raw: dict) -> dict:
    data = dict(raw)
    if 'rule_packs' not in data and data.get('legal_rule_pack_ids'):
        data['rule_packs'] = [{'id': rid} for rid in data['legal_rule_pack_ids']]
    if 'provenance' not in data and data.get('data_provenance'):
        data['provenance'] = data['data_provenance']
    if 'data_mode' not in data:
        provenance = data.get('data_provenance') or data.get('provenance') or {}
        kind = provenance.get('data_kind')
        if kind:
            mapping = {
                'synthetic': DataMode.synthetic.value,
                'real_rule_plus_synthetic_prices': DataMode.real_rule_plus_synthetic_prices.value,
                'real_public_snapshot': DataMode.real_public_snapshot.value,
                'real_fact_plus_synthetic_prices': DataMode.real_fact_plus_synthetic_prices.value,
            }
            data['data_mode'] = mapping.get(kind, kind)
    return data


def load_scenario(path: str | Path) -> Scenario:
    with Path(path).open('r', encoding='utf-8') as f:
        raw = yaml.safe_load(f) or {}
    try:
        scenario = Scenario.model_validate(_normalize_keys(raw))
    except Exception as exc:
        raise ScenarioValidationError(f'Failed to parse {path}: {exc}') from exc
    validate_scenario(scenario)
    return scenario


def validate_scenario(scenario: Scenario) -> None:
    if scenario.starting_cash != 100:
        raise ScenarioValidationError('starting_cash must be 100')
    rule_ids = [rule.id for rule in scenario.public_rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise ScenarioValidationError('public rule ids must be unique')
    instrument_ids = [instrument.id for instrument in scenario.instruments]
    if len(instrument_ids) != len(set(instrument_ids)):
        raise ScenarioValidationError('instrument ids must be unique')
    if ActionType.HOLD not in scenario.allowed_actions:
        raise ScenarioValidationError('allowed_actions must include HOLD')
    missing = [rid for rid in scenario.scoring.key_rule_ids if rid not in set(rule_ids)]
    if missing:
        raise ScenarioValidationError(f'key_rule_ids missing from public_rules: {missing}')
    for idx, trap in enumerate(scenario.trap_conditions):
        if trap.condition_type not in TrapConditionType:
            raise ScenarioValidationError(f'invalid trap condition at index {idx}')
    if len(scenario.timeline) < scenario.max_steps:
        raise ScenarioValidationError('timeline shorter than max_steps')
    for idx, step in enumerate(scenario.timeline[: scenario.max_steps]):
        if step.t != idx:
            raise ScenarioValidationError(f'timeline step mismatch at index {idx}: got {step.t}')
    if scenario.data_mode.value != DataMode.synthetic.value and not scenario.provenance:
        raise ScenarioValidationError('non-synthetic scenarios require provenance')
    if scenario.data_mode.value != DataMode.synthetic.value:
        sources = scenario.provenance.get('sources') or scenario.provenance.get('public_sources') or []
        if not sources:
            raise ScenarioValidationError('real-data scenario requires at least one source')
    if not scenario.hidden_oracle_solution:
        raise ScenarioValidationError('hidden_oracle_solution required')
    if not scenario.trap_conditions:
        raise ScenarioValidationError('trap_conditions required')
    registry = load_rule_pack_registry()
    ref_ids = [ref.id for ref in scenario.rule_packs] + list(scenario.legal_rule_pack_ids)
    for rule_pack_id in ref_ids:
        if rule_pack_id not in registry:
            raise ScenarioValidationError(f'unknown legal rule pack: {rule_pack_id}')


def _iter_yaml_paths(path: Path):
    if path.is_file() and path.suffix in {'.yaml', '.yml'}:
        yield path
    elif path.is_dir():
        for scenario_path in sorted(path.rglob('*.yaml')):
            if 'rule_packs' in scenario_path.parts:
                continue
            yield scenario_path


def load_scenarios_dir(path: str | Path) -> list[Scenario]:
    scenarios = []
    for scenario_path in _iter_yaml_paths(Path(path)):
        scenarios.append(load_scenario(scenario_path))
    return scenarios
