from __future__ import annotations

import os

from finrulebench.core.errors import AdapterError
from finrulebench.core.models import ActionType, ModelDecision


class OpenAIResponsesAdapter:
    @property
    def name(self) -> str:
        return 'openai-responses'

    @property
    def provider(self) -> str:
        return 'openai'

    def decide(self, prompt, decision_schema, run_config):
        if not os.getenv('OPENAI_API_KEY'):
            raise AdapterError('OPENAI_API_KEY missing. Install optional deps with pip install -e ".[openai]" if needed.')
        return ModelDecision(
            step=prompt['step'],
            orders=[{'action': ActionType.HOLD}],
            rule_citations=[],
            confidence=0.5,
            rationale_summary='OpenAI adapter stub fallback HOLD.',
            evidence_timestamps=[prompt['step']],
            metadata={'provider': 'openai', 'stub': True},
        )
