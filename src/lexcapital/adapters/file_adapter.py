from __future__ import annotations

import json
from pathlib import Path

from lexcapital.core.models import ModelDecision


class FileAdapter:
    def __init__(self, path: str) -> None:
        self._lines = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
        self._idx = 0

    @property
    def name(self) -> str:
        return 'file-adapter'

    @property
    def provider(self) -> str:
        return 'file'

    def decide(self, prompt, decision_schema, run_config):
        payload = self._lines[self._idx]
        self._idx += 1
        return ModelDecision.model_validate(payload)
