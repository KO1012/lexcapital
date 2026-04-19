from __future__ import annotations

from finrulebench.core.models import ActionType, ModelDecision


class LocalHTTPAdapter:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url

    @property
    def name(self) -> str:
        return 'local-http'

    @property
    def provider(self) -> str:
        return 'local_http'

    def decide(self, prompt, decision_schema, run_config):
        return ModelDecision(
            step=prompt['step'],
            orders=[{'action': ActionType.HOLD}],
            rule_citations=[],
            confidence=0.5,
            rationale_summary='Local HTTP adapter stub defaults to HOLD.',
            evidence_timestamps=[prompt['step']],
            metadata={'stub': True},
        )
