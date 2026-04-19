from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class LegalRulePack:
    id: str
    version: str
    public_summary: str
    rule_ids: list[str]
    trap_condition_types: list[str]


def load_rule_pack_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open('r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def _pack_from_dict(data: dict[str, Any]) -> LegalRulePack:
    public_summary = data.get('public_summary')
    if not public_summary:
        public_summary = ' '.join(rule.get('text', '') for rule in data.get('public_rules', [])[:4]).strip()
    return LegalRulePack(
        id=data['id'],
        version=data.get('version', 'v1'),
        public_summary=public_summary,
        rule_ids=[rule['id'] for rule in data.get('rules', data.get('public_rules', []))],
        trap_condition_types=list(data.get('trap_condition_types', [])),
    )


def rule_pack_directories(base_dir: str | Path | None = None) -> list[Path]:
    candidates = []
    if base_dir is not None:
        candidates.append(Path(base_dir))
    candidates.extend([
        Path('src/finrulebench/legal_rule_packs'),
        Path('scenarios/rule_packs'),
    ])
    seen: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved not in seen and candidate.exists():
            seen.append(resolved)
    return [Path(p) for p in seen]


def load_rule_pack_registry(base_dir: str | Path | None = None) -> dict[str, LegalRulePack]:
    registry: dict[str, LegalRulePack] = {}
    for directory in rule_pack_directories(base_dir):
        for path in sorted(directory.glob('*.yaml')):
            data = load_rule_pack_yaml(path)
            if data:
                pack = _pack_from_dict(data)
                registry[pack.id] = pack
    return registry
