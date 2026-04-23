from lexcapital.adapters.mock_adapter import MockAdapter
from lexcapital.core.replay import replay_scenario
from lexcapital.runners.policy_runner import collect_actions_for_scenario
from lexcapital.runners.run_config import RunConfig

from .conftest import ROOT


def test_collect_then_replay_roundtrip(tmp_path):
    scenario = ROOT / 'scenarios' / 'mvp' / 'rab_001_qualified_hedge_rebate.yaml'
    actions = tmp_path / 'actions.jsonl'
    collect_actions_for_scenario(str(scenario), MockAdapter('mock-hold'), RunConfig(model_name='mock-hold'), actions, tmp_path / 'log.jsonl', tmp_path / 'prompts.jsonl')
    result = replay_scenario(str(scenario), str(actions), str(tmp_path / 'replay'))
    assert result.scenario_id == 'RAB-001'
