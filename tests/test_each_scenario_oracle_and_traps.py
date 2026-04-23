import json
from pathlib import Path

from lexcapital.core.replay import replay_scenario
from lexcapital.policies.scripted_oracles import oracle_decisions_for_scenario

from .conftest import ROOT, scenario_paths


def _write_decisions(path: Path, decisions):
    with path.open('w', encoding='utf-8') as f:
        for d in decisions:
            f.write(json.dumps(d.model_dump()) + '\n')


def test_each_scenario_baseline_replays(tmp_path):
    hold_actions = ROOT / 'examples' / 'actions' / 'hold_actions.jsonl'
    for path in scenario_paths():
        result = replay_scenario(str(path), str(hold_actions), str(tmp_path / path.stem))
        assert result.scenario_id


def test_red_paths_trigger_violations(tmp_path):
    targets = [
        ('stock_001_low_float_earnings_drift.yaml', ROOT / 'examples' / 'actions' / 'invalid_future_data_actions.jsonl'),
        ('rab_001_qualified_hedge_rebate.yaml', ROOT / 'examples' / 'actions' / 'invalid_self_cross_actions.jsonl'),
        ('noctx_001_no_edge_hold.yaml', ROOT / 'examples' / 'actions' / 'invalid_no_context_overtrade.jsonl'),
    ]
    for scenario_name, action_path in targets:
        result = replay_scenario(str(ROOT / 'scenarios' / 'mvp' / scenario_name), str(action_path), str(tmp_path / scenario_name.replace('.yaml', '')))
        assert result.violations


def test_oracle_like_paths_are_non_dq(tmp_path):
    for scenario_id in ['NOCTX-001', 'RAB-001', 'PM-001']:
        decisions = oracle_decisions_for_scenario(scenario_id)
        action_path = tmp_path / f'{scenario_id}.jsonl'
        _write_decisions(action_path, decisions)
        mapping = {'NOCTX-001': 'noctx_001_no_edge_hold.yaml', 'RAB-001': 'rab_001_qualified_hedge_rebate.yaml', 'PM-001': 'pm_001_official_filing_contract.yaml'}
        result = replay_scenario(str(ROOT / 'scenarios' / 'mvp' / mapping[scenario_id]), str(action_path), str(tmp_path / scenario_id))
        assert result.gate == 1
