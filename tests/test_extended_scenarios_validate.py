from finrulebench.core.scenario_loader import load_scenario

from .conftest import extended_scenario_paths


def test_extended_scenarios_validate():
    paths = extended_scenario_paths()
    assert paths, 'extended scenarios missing'
    for path in paths:
        scenario = load_scenario(path)
        assert scenario.starting_cash == 100
        assert scenario.trap_conditions
        assert scenario.hidden_oracle_solution.summary
