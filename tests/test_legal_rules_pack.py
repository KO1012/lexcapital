from lexcapital.core.legal_rules import load_rule_pack_registry
from lexcapital.core.models import TrapConditionType
from lexcapital.core.scenario_loader import load_scenario

from .conftest import extended_scenario_paths


def test_legal_rule_pack_registry_and_refs():
    registry = load_rule_pack_registry()
    for required in ['SIM-REGSHO-LITE', 'SIM-INTRADAY-MARGIN', 'SIM-FUND-LIQUIDITY', 'SIM-EVENT-RESOLUTION', 'SIM-MNPI-EXCLUSION']:
        assert required in registry
        assert registry[required].trap_condition_types
        for trap_name in registry[required].trap_condition_types:
            assert trap_name in TrapConditionType.__members__
    for path in extended_scenario_paths():
        scenario = load_scenario(path)
        rule_ids = [rule.id for rule in scenario.public_rules]
        assert len(rule_ids) == len(set(rule_ids))
        for ref in scenario.rule_packs:
            assert ref.id in registry
