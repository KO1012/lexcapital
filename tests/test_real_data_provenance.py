from lexcapital.core.scenario_loader import load_scenario

from .conftest import SCENARIOS_EXTENDED


def test_real_data_provenance_rules():
    for path in sorted((SCENARIOS_EXTENDED / 'real_data').glob('*.yaml')):
        scenario = load_scenario(path)
        provenance = scenario.provenance
        assert provenance
        assert provenance['data_kind'].startswith('real_')
        assert provenance.get('sources')
        assert all(src['url'].startswith(('http://', 'https://')) for src in provenance['sources'])
        notes = provenance.get('source_notes', '').lower()
        assert 'synthetic' in notes or 'real' in notes
