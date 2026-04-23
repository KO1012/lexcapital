from __future__ import annotations

import pathlib
import subprocess
import sys

import tomllib


ROOT = pathlib.Path(__file__).resolve().parents[1]
LEGACY_NAME = "fin" + "rulebench"


def test_wheel_only_packages_lexcapital():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == [
        "src/lexcapital"
    ]


def test_legacy_package_is_removed():
    assert not (ROOT / "src" / LEGACY_NAME).exists()


def test_legacy_module_command_is_removed():
    result = subprocess.run(
        [sys.executable, "-m", LEGACY_NAME, "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode != 0


def test_lexcapital_module_command_still_works():
    result = subprocess.run(
        [sys.executable, "-m", "lexcapital", "validate", "scenarios/mvp"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "'validated': 14" in result.stdout
