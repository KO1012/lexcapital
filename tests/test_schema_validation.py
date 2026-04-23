from lexcapital.core.scenario_loader import load_scenario

from .conftest import scenario_paths


def test_all_mvp_scenarios_load():
    for path in scenario_paths():
        scenario = load_scenario(path)
        assert scenario.starting_cash == 100
        assert len({r.id for r in scenario.public_rules}) == len(scenario.public_rules)
        assert len({i.id for i in scenario.instruments}) == len(scenario.instruments)
        assert any(action.value == 'HOLD' for action in scenario.allowed_actions)
        rule_ids = {r.id for r in scenario.public_rules}
        assert set(scenario.scoring.key_rule_ids).issubset(rule_ids)
