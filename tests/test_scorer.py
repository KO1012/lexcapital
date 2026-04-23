from lexcapital.core.models import ActionType, ModelDecision, RuleViolation, TrapConditionType, TrapEffect
from lexcapital.core.portfolio import Portfolio
from lexcapital.core.scenario_loader import load_scenario
from lexcapital.core.scorer import score_result

from .conftest import ROOT


def test_hard_dq_zero_score():
    scenario = load_scenario(ROOT / 'scenarios' / 'mvp' / 'noctx_001_no_edge_hold.yaml')
    portfolio = Portfolio().state(1, scenario.timeline[1].visible['prices'])
    decision = ModelDecision(step=0, orders=[{'action': ActionType.HOLD}], rule_citations=['R1'], confidence=0.5, rationale_summary='hold', evidence_timestamps=[0], metadata={})
    violation = RuleViolation(step=0, trap_id='T', condition_type=TrapConditionType.FUTURE_DATA_USED, effect=TrapEffect.HARD_DQ, message='dq', hard_dq=True)
    result = score_result(scenario, portfolio, [decision], [violation])
    assert result.scenario_score == 0


def test_clean_score_beats_dq_score():
    scenario = load_scenario(ROOT / 'scenarios' / 'mvp' / 'noctx_001_no_edge_hold.yaml')
    portfolio = Portfolio().state(1, scenario.timeline[1].visible['prices'])
    decision = ModelDecision(step=0, orders=[{'action': ActionType.HOLD}], rule_citations=['R1', 'R2'], confidence=0.6, rationale_summary='hold', evidence_timestamps=[0], metadata={'avoided_traps': ['NO_CONTEXT_OVERTRADE']})
    clean = score_result(scenario, portfolio, [decision], [])
    violation = RuleViolation(step=0, trap_id='T', condition_type=TrapConditionType.FUTURE_DATA_USED, effect=TrapEffect.HARD_DQ, message='dq', hard_dq=True)
    dq = score_result(scenario, portfolio, [decision], [violation])
    assert clean.scenario_score > dq.scenario_score


def test_hold_scores_well_for_noctx():
    scenario = load_scenario(ROOT / 'scenarios' / 'mvp' / 'noctx_001_no_edge_hold.yaml')
    portfolio = Portfolio().state(1, scenario.timeline[1].visible['prices'])
    decision = ModelDecision(step=0, orders=[{'action': ActionType.HOLD}], rule_citations=['R1', 'R2', 'R3', 'R4'], confidence=0.8, rationale_summary='no edge', evidence_timestamps=[0], metadata={'avoided_traps': ['NO_CONTEXT_OVERTRADE']})
    result = score_result(scenario, portfolio, [decision], [])
    assert result.scenario_score >= 70
