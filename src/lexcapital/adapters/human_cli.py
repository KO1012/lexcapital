from __future__ import annotations

from lexcapital.core.models import ActionType, ModelDecision


class HumanCLIAdapter:
    @property
    def name(self) -> str:
        return 'human-cli'

    @property
    def provider(self) -> str:
        return 'human'

    def decide(self, prompt, decision_schema, run_config):
        return ModelDecision(
            step=prompt['step'],
            orders=[{'action': ActionType.HOLD}],
            rule_citations=[],
            confidence=0.5,
            rationale_summary='Human CLI stub.',
            evidence_timestamps=[prompt['step']],
            metadata={'stub': True},
        )
