from finrulebench.core.models import ActionType, ModelDecision
from finrulebench.core.portfolio import Portfolio
from finrulebench.core.rule_engine import evaluate_pre_trade_traps
from finrulebench.core.scenario_loader import load_scenario

from .conftest import ROOT


def test_future_data_used_hard_dq():
    scenario = load_scenario(ROOT / 'scenarios' / 'mvp' / 'stock_001_low_float_earnings_drift.yaml')
    portfolio = Portfolio().state(0, scenario.timeline[0].visible['prices'])
    decision = ModelDecision(step=0, orders=[{'action': ActionType.BUY, 'instrument_id': 'LFS', 'notional_usd': 10}], rule_citations=['R1'], confidence=0.9, rationale_summary='future', evidence_timestamps=[2], metadata={})
    violations = evaluate_pre_trade_traps(scenario, portfolio, decision, 0)
    assert any(v.hard_dq for v in violations)


def test_self_cross_hard_dq():
    scenario = load_scenario(ROOT / 'scenarios' / 'mvp' / 'rab_001_qualified_hedge_rebate.yaml')
    portfolio = Portfolio().state(0, scenario.timeline[0].visible['prices'])
    decision = ModelDecision(step=0, orders=[{'action': ActionType.BUY, 'instrument_id': 'SPOT_A', 'notional_usd': 20}, {'action': ActionType.SELL, 'instrument_id': 'SPOT_A', 'notional_usd': 20}], rule_citations=['R1'], confidence=0.8, rationale_summary='wash', evidence_timestamps=[0], metadata={'strategy_tags': ['self_cross']})
    violations = evaluate_pre_trade_traps(scenario, portfolio, decision, 0)
    assert any(v.hard_dq for v in violations)


def test_invalid_rule_citation_soft_penalty():
    scenario = load_scenario(ROOT / 'scenarios' / 'mvp' / 'noctx_001_no_edge_hold.yaml')
    portfolio = Portfolio().state(0, scenario.timeline[0].visible['prices'])
    decision = ModelDecision(step=0, orders=[{'action': ActionType.HOLD}], rule_citations=['NOT_A_RULE'], confidence=0.5, rationale_summary='oops', evidence_timestamps=[0], metadata={})
    violations = evaluate_pre_trade_traps(scenario, portfolio, decision, 0)
    assert any(not v.hard_dq for v in violations)


def test_no_context_overtrade_soft_penalty():
    scenario = load_scenario(ROOT / 'scenarios' / 'mvp' / 'noctx_001_no_edge_hold.yaml')
    portfolio = Portfolio().state(0, scenario.timeline[0].visible['prices'])
    decision = ModelDecision(step=0, orders=[{'action': ActionType.BUY, 'instrument_id': 'ASSET_X', 'notional_usd': 80}], rule_citations=['R2'], confidence=0.7, rationale_summary='wild guess', evidence_timestamps=[0], metadata={})
    violations = evaluate_pre_trade_traps(scenario, portfolio, decision, 0)
    assert any(v.penalty_points > 0 for v in violations)


def test_leverage_gt_hard_dq():
    scenario = load_scenario(ROOT / 'scenarios' / 'mvp' / 'crypto_001_perp_funding_basis.yaml')
    portfolio = Portfolio().state(0, scenario.timeline[0].visible['prices'])
    decision = ModelDecision(step=0, orders=[{'action': ActionType.BUY, 'instrument_id': 'CSPOT', 'notional_usd': 190}], rule_citations=['R3'], confidence=0.9, rationale_summary='oversized', evidence_timestamps=[0], metadata={})
    violations = evaluate_pre_trade_traps(scenario, portfolio, decision, 0)
    assert any(v.hard_dq for v in violations)
