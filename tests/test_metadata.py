"""Package name, import name, esoi scope and the default install agree (design doc R10, adoption checklist)."""
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]


def test_the_default_install_brings_esoi_only():
    assert PROJECT["dependencies"] == ["esoi"]


def test_distribution_import_name_and_esoi_package_agree():
    assert PROJECT["name"] == "hubofhubs" == tomllib.loads((ROOT / "esoi.toml").read_text())["package"]
    assert (ROOT / "hubofhubs" / "__init__.py").is_file() and not (ROOT / "ai_hub_of_hubs").exists()
    assert tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["setuptools"]["packages"] == ["hubofhubs", "hubofhubs.ports", "hubofhubs.websearch"]


def test_the_version_is_a_literal_in_pyproject():
    assert PROJECT["version"].count(".") == 2 and "dynamic" not in PROJECT
