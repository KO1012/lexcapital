from __future__ import annotations

from lexcapital.core.models import ActionType, ModelDecision


class MockAdapter:
    def __init__(self, model_name: str = 'mock-hold') -> None:
        self._model_name = model_name

    @property
    def name(self) -> str:
        return self._model_name

    @property
    def provider(self) -> str:
        return 'mock'

    def decide(self, prompt, decision_schema, run_config):
        step = int(prompt['step'])
        prices = prompt['visible_state'].get('prices', {})
        first_instrument = next(iter(prices.keys())) if prices else None
        if self._model_name == 'mock-overtrade' and first_instrument:
            return ModelDecision(
                step=step,
                orders=[{'action': ActionType.BUY, 'instrument_id': first_instrument, 'notional_usd': 80}],
                rule_citations=['R2'],
                confidence=0.8,
                rationale_summary='Aggressive mock overtrade.',
                evidence_timestamps=[step],
                metadata={},
            )
        if self._model_name == 'mock-invalid-json':
            return ModelDecision(
                step=step,
                orders=[{'action': ActionType.HOLD}],
                rule_citations=[],
                confidence=0.2,
                rationale_summary='Recovered from invalid output by holding.',
                evidence_timestamps=[step],
                metadata={'invalid_output': True},
            )
        return ModelDecision(
            step=step,
            orders=[{'action': ActionType.HOLD}],
            rule_citations=[],
            confidence=0.5,
            rationale_summary='Mock hold policy.',
            evidence_timestamps=[step],
            metadata={},
        )
