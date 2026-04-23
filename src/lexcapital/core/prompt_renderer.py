from __future__ import annotations

from typing import Any

FORBIDDEN_KEYS = {'hidden_oracle_solution', 'trap_conditions', 'hidden_future', 'scoring', 'notes_for_authors', 'private_tip'}


def _scrub_visible(value):
    if isinstance(value, dict):
        cleaned = {}
        for key, item in value.items():
            if key in FORBIDDEN_KEYS or 'private_tip' in key or 'hidden_' in key:
                continue
            cleaned[key] = _scrub_visible(item)
        return cleaned
    if isinstance(value, list):
        return [_scrub_visible(item) for item in value]
    return value

from lexcapital.core.legal_rules import load_rule_pack_registry
from lexcapital.core.models import ModelDecision, PortfolioState, Scenario


def _rule_pack_summaries(scenario: Scenario) -> list[dict[str, str]]:
    registry = load_rule_pack_registry()
    refs = scenario.rule_packs or [{'id': rid} for rid in scenario.legal_rule_pack_ids]
    out: list[dict[str, str]] = []
    for ref in refs:
        rid = ref.id if hasattr(ref, 'id') else ref.get('id')
        pack = registry.get(rid)
        if pack:
            out.append({'id': pack.id, 'version': pack.version, 'public_summary': pack.public_summary})
    return out


def render_model_prompt(scenario: Scenario, step: int, portfolio: PortfolioState) -> dict[str, Any]:
    visible = _scrub_visible(scenario.timeline[step].visible)
    return {
        'scenario_id': scenario.id,
        'category': scenario.category.value,
        'title': scenario.title,
        'difficulty': scenario.difficulty.value,
        'data_mode': scenario.data_mode.value,
        'question': scenario.question,
        'step': step,
        'cash': portfolio.cash,
        'positions': {k: v.model_dump() for k, v in portfolio.positions.items()},
        'portfolio_value': portfolio.portfolio_value,
        'max_drawdown': portfolio.max_drawdown,
        'visible_state': visible,
        'public_rules': [rule.model_dump() for rule in scenario.public_rules],
        'rule_packs': _rule_pack_summaries(scenario),
        'allowed_actions': [action.value for action in scenario.allowed_actions],
        'required_output_schema': ModelDecision.model_json_schema(),
    }
