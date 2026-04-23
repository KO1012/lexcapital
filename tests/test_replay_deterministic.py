from lexcapital.core.hashing import sha256_json
from lexcapital.core.replay import replay_scenario

from .conftest import ROOT


def test_replay_is_deterministic(tmp_path):
    scenario = ROOT / 'scenarios' / 'mvp' / 'noctx_001_no_edge_hold.yaml'
    actions = ROOT / 'examples' / 'actions' / 'hold_actions.jsonl'
    out1 = tmp_path / 'run1'
    out2 = tmp_path / 'run2'
    replay_scenario(str(scenario), str(actions), str(out1))
    replay_scenario(str(scenario), str(actions), str(out2))
    assert sha256_json((out1 / 'score.json').read_text()) == sha256_json((out2 / 'score.json').read_text())
