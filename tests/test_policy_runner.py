from lexcapital.adapters.mock_adapter import MockAdapter
from lexcapital.core.replay import replay_scenario
from lexcapital.runners.policy_runner import collect_actions_for_scenario
from lexcapital.runners.run_config import RunConfig

from .conftest import ROOT


def test_policy_runner_generates_files(tmp_path):
    scenario = ROOT / 'scenarios' / 'mvp' / 'noctx_001_no_edge_hold.yaml'
    actions = tmp_path / 'actions.jsonl'
    model_log = tmp_path / 'model_log.jsonl'
    prompts = tmp_path / 'rendered_prompts.jsonl'
    collect_actions_for_scenario(str(scenario), MockAdapter('mock-hold'), RunConfig(model_name='mock-hold'), actions, model_log, prompts)
    assert actions.exists()
    assert model_log.exists()
    assert prompts.exists()
    result = replay_scenario(str(scenario), str(actions), str(tmp_path / 'replay'))
    assert result.scenario_id == 'NOCTX-001'
