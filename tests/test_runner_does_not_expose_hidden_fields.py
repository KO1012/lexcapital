import json

from lexcapital.adapters.mock_adapter import MockAdapter
from lexcapital.runners.policy_runner import collect_actions_for_scenario
from lexcapital.runners.run_config import RunConfig

from .conftest import ROOT


def test_runner_prompts_hide_hidden_fields(tmp_path):
    scenario = ROOT / 'scenarios' / 'mvp' / 'legal_001_information_boundary.yaml'
    prompts = tmp_path / 'rendered_prompts.jsonl'
    collect_actions_for_scenario(str(scenario), MockAdapter('mock-hold'), RunConfig(model_name='mock-hold'), tmp_path / 'actions.jsonl', tmp_path / 'model_log.jsonl', prompts)
    blob = prompts.read_text(encoding='utf-8')
    assert 'private_tip' not in blob
    assert 'hidden_oracle_solution' not in blob
