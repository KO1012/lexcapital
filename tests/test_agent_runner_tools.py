import pytest

from finrulebench.agent_tools.calculator import calculate
from finrulebench.agent_tools.submit_decision import submit_decision
from finrulebench.core.portfolio import Portfolio
from finrulebench.core.prompt_renderer import render_model_prompt
from finrulebench.core.scenario_loader import load_scenario

from .conftest import ROOT


def test_visible_state_hides_hidden():
    scenario = load_scenario(ROOT / 'scenarios' / 'mvp' / 'legal_001_information_boundary.yaml')
    prompt = render_model_prompt(scenario, 0, Portfolio().state(0, scenario.timeline[0].visible['prices']))
    assert 'hidden_future' not in str(prompt)


def test_calculator_blocks_python_names():
    with pytest.raises(ValueError):
        calculate('__import__("os").system("whoami")')


def test_submit_decision_validates_schema():
    decision = submit_decision({'step': 0, 'orders': [{'action': 'HOLD'}], 'rule_citations': [], 'confidence': 0.5, 'rationale_summary': 'hold', 'evidence_timestamps': [0], 'metadata': {}})
    assert decision.step == 0
