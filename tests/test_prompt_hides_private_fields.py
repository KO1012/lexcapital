import json

from lexcapital.core.portfolio import Portfolio
from lexcapital.core.prompt_renderer import render_model_prompt
from lexcapital.core.scenario_loader import load_scenario

from .conftest import ROOT, scenario_paths


FORBIDDEN = [
    'hidden_oracle_solution',
    'trap_conditions',
    'hidden_future',
    'scoring',
    'notes_for_authors',
    'CANARY_HIDDEN_ORACLE_DO_NOT_EXPOSE',
    'CANARY_HIDDEN_TRAP_DO_NOT_EXPOSE',
    'CANARY_HIDDEN_FUTURE_DO_NOT_EXPOSE',
]


def test_render_prompt_hides_private_fields():
    for path in scenario_paths():
        scenario = load_scenario(path)
        scenario.hidden_oracle_solution.summary = 'CANARY_HIDDEN_ORACLE_DO_NOT_EXPOSE'
        if scenario.trap_conditions:
            scenario.trap_conditions[0].description = 'CANARY_HIDDEN_TRAP_DO_NOT_EXPOSE'
        state = Portfolio().state(0, scenario.timeline[0].visible.get('prices', {}))
        prompt = render_model_prompt(scenario, 0, state)
        blob = json.dumps(prompt, ensure_ascii=False)
        for forbidden in FORBIDDEN:
            assert forbidden not in blob
