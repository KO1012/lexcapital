import json
import subprocess
import sys

from .conftest import ROOT


def test_cli_help():
    result = subprocess.run([sys.executable, '-m', 'finrulebench', '--help'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0


def test_cli_validate():
    result = subprocess.run([sys.executable, '-m', 'finrulebench', 'validate', 'scenarios/mvp'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0


def test_cli_render_prompt_hides_hidden():
    result = subprocess.run([sys.executable, '-m', 'finrulebench', 'render-prompt', '--scenario', 'scenarios/mvp/noctx_001_no_edge_hold.yaml', '--step', '0'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0
    assert 'hidden_oracle_solution' not in result.stdout
