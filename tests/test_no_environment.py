"""The hub reads no environment, and where it is run from or installed changes nothing (design doc R2, R5)."""
import ast
import json
import sys
import tomllib
from pathlib import Path

import pytest
from esoi import config as esoi_config
from esoi import runtime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import hubofhubs  # noqa: E402
from hubofhubs import AssemblyConfig, AssemblyError, choice, resolve  # noqa: E402
from support import ROOT, run_vendored, vendor  # noqa: E402

SEAT = "reason-and-answer"
HOSTILE = '[selection]\nreason-and-answer = "evil"\n'


def test_no_module_reads_the_environment():
    bad = []
    for path in (ROOT / "hubofhubs").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Attribute) and node.attr in ("environ", "getenv", "putenv"):
                bad.append(f"{path.name}:{node.lineno}")
            if isinstance(node, ast.ImportFrom) and node.module == "os" and {a.name for a in node.names} & {"environ", "getenv"}:
                bad.append(f"{path.name}:{node.lineno}")
    assert not bad, f"environment reads in the hub: {bad}"


def test_the_hub_default_resolves_and_names_its_layer():
    picked = choice(SEAT)
    assert (picked.name, picked.layer) == ("tier_selector", "hubofhubs default")
    assert resolve(SEAT).__name__ == "TierSelector"


def test_an_environment_variable_changes_nothing(monkeypatch, tmp_path):
    monkeypatch.setenv("ESOI_SELECT_HUBOFHUBS_REASON_AND_ANSWER", "evil")
    monkeypatch.setenv("ESOI_SELECT_REASON_AND_ANSWER", "evil")
    monkeypatch.setenv("ESOI_ROOT", str(tmp_path))
    monkeypatch.setenv("ESOI_SNAPSHOT", str(tmp_path / "nope.json"))
    assert choice(SEAT).name == "tier_selector"
    assert resolve(SEAT).__name__ == "TierSelector"


def test_selection_environ_is_the_only_control():
    config = AssemblyConfig(selection_environ={"ESOI_SELECT_HUBOFHUBS_REASON_AND_ANSWER": "tier_selector"})
    assert choice(SEAT, config=config).layer == "selection environ"
    for bad in ({"ESOI_ROOT": "/x"}, {"ESOI_SNAPSHOT": "/x"}, {"ESOI_SELECT_HUBOFHUBS_REASON_AND_ANSWER": "os:system"}):
        with pytest.raises(AssemblyError):
            choice(SEAT, config=AssemblyConfig(selection_environ=bad))


def test_a_hostile_esoi_toml_in_the_working_directory_is_ignored(monkeypatch, tmp_path):
    (tmp_path / "esoi.toml").write_text('package = "hubofhubs"\nselection = "evil.py:TABLE"\n' + HOSTILE)
    (tmp_path / "evil.py").write_text("raise SystemExit('executed')\nTABLE = {}\n")
    monkeypatch.chdir(tmp_path)
    before = list(sys.path)
    assert choice(SEAT).name == "tier_selector"
    assert resolve(SEAT).__name__ == "TierSelector"
    assert sys.path == before


def test_resolve_from_a_vendored_copy_outside_any_repo(tmp_path):
    site = vendor(tmp_path / "copy")
    work = tmp_path / "work"
    work.mkdir()
    (work / "esoi.toml").write_text(HOSTILE)    # hostile file in the working directory
    out = run_vendored(site, """
import json
before = list(sys.path)
import hubofhubs
picked = hubofhubs.choice('reason-and-answer')
obj = hubofhubs.resolve('reason-and-answer')
print(json.dumps(dict(name=picked.name, layer=picked.layer, cls=obj.__name__, file=hubofhubs.__file__,
                      same_path=before == list(sys.path), names=hubofhubs.names('reason-and-answer'))))
""", work)
    assert out["file"].startswith(str(site)) and (out["name"], out["cls"]) == ("tier_selector", "TierSelector")
    assert out["same_path"] and out["names"] == ["tier_selector"]
    assert out["layer"] == choice(SEAT).layer


def test_sys_path_is_unchanged_by_resolve():
    before = list(sys.path)
    resolve(SEAT)
    names = hubofhubs.names(SEAT)
    assert sys.path == before and "tier_selector" in names


def test_the_hubs_own_esoi_toml_has_no_selection_table():
    assert "selection" not in tomllib.loads((ROOT / "esoi.toml").read_text())


def test_the_packaged_snapshot_equals_the_records():
    packaged = json.loads((ROOT / "hubofhubs" / "esoi_selection.json").read_text())
    assert packaged == runtime.snapshot(esoi_config.load(ROOT))


def test_the_snapshot_ships_as_package_data():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["setuptools"]["package-data"]["hubofhubs"]
    assert "esoi_selection.json" in data
