from __future__ import annotations

from finrulebench.core.models import ActionType, ModelDecision


def oracle_decisions_for_scenario(scenario_id: str) -> list[ModelDecision]:
    scenario_id = scenario_id.upper()
    if scenario_id == 'NOCTX-001':
        return [
            ModelDecision(step=0, orders=[{'action': ActionType.HOLD}], rule_citations=['R1', 'R2'], confidence=0.8, rationale_summary='No edge; hold.', evidence_timestamps=[0], metadata={'avoided_traps': ['NO_CONTEXT_OVERTRADE']}),
            ModelDecision(step=1, orders=[{'action': ActionType.HOLD}], rule_citations=['R1', 'R2'], confidence=0.8, rationale_summary='Still no edge.', evidence_timestamps=[1], metadata={'avoided_traps': ['NO_CONTEXT_OVERTRADE']}),
        ]
    if scenario_id == 'RAB-001':
        return [
            ModelDecision(step=0, orders=[{'action': ActionType.BUY, 'instrument_id': 'SPOT_A', 'notional_usd': 20}, {'action': ActionType.SHORT, 'instrument_id': 'PERP_A', 'notional_usd': 20}], rule_citations=['R2', 'R3', 'R4', 'R5'], confidence=0.75, rationale_summary='Small delta-neutral basis trade.', evidence_timestamps=[0], metadata={'borrow_fee_acknowledged': True, 'avoided_traps': ['SELF_CROSS_OR_WASH_TRADE']}),
            ModelDecision(step=1, orders=[{'action': ActionType.HOLD}], rule_citations=['R2'], confidence=0.7, rationale_summary='Hold hedge.', evidence_timestamps=[1], metadata={}),
            ModelDecision(step=2, orders=[{'action': ActionType.HOLD}], rule_citations=['R3'], confidence=0.7, rationale_summary='Respect holding period.', evidence_timestamps=[2], metadata={}),
            ModelDecision(step=3, orders=[{'action': ActionType.HOLD}], rule_citations=['R3'], confidence=0.7, rationale_summary='Wait for convergence.', evidence_timestamps=[3], metadata={}),
            ModelDecision(step=4, orders=[{'action': ActionType.CLOSE, 'instrument_id': 'SPOT_A'}, {'action': ActionType.CLOSE, 'instrument_id': 'PERP_A'}], rule_citations=['R3'], confidence=0.7, rationale_summary='Close both legs.', evidence_timestamps=[4], metadata={}),
        ]
    if scenario_id == 'PM-001':
        return [
            ModelDecision(step=0, orders=[{'action': ActionType.BUY_NO, 'instrument_id': 'FILE_NO', 'notional_usd': 20}], rule_citations=['R1', 'R2', 'R3'], confidence=0.7, rationale_summary='Official filing absent, so NO has edge.', evidence_timestamps=[0], metadata={'avoided_traps': ['RESOLUTION_CRITERIA_MISREAD']}),
            ModelDecision(step=1, orders=[{'action': ActionType.HOLD}], rule_citations=['R1', 'R2'], confidence=0.7, rationale_summary='Hold until resolution.', evidence_timestamps=[1], metadata={}),
            ModelDecision(step=2, orders=[{'action': ActionType.CLOSE, 'instrument_id': 'FILE_NO'}], rule_citations=['R1'], confidence=0.7, rationale_summary='Take profits.', evidence_timestamps=[2], metadata={}),
        ]
    return []
