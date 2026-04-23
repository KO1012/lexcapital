from __future__ import annotations

from typing import Any, Protocol

from lexcapital.core.models import ModelDecision
from lexcapital.runners.run_config import RunConfig


class ModelAdapter(Protocol):
    @property
    def name(self) -> str: ...

    @property
    def provider(self) -> str: ...

    def decide(
        self,
        prompt: dict[str, Any],
        decision_schema: dict[str, Any],
        run_config: RunConfig,
    ) -> ModelDecision: ...
