from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_MVP = ROOT / 'scenarios' / 'mvp'


def scenario_paths():
    return sorted(SCENARIOS_MVP.glob('*.yaml'))

SCENARIOS_EXTENDED = ROOT / 'scenarios_extended'

def extended_scenario_paths():
    return sorted(SCENARIOS_EXTENDED.rglob('*.yaml'))
