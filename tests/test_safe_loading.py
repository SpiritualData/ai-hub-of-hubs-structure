"""Safe loading: names only, and an import target only from consumer code or the hub's own packaged records."""
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import toy  # noqa: E402
from toy import MemoryStore, toys  # noqa: E402,F401
from hubofhubs import HubConfig, HubError, assemble, choice, names, register, resolve  # noqa: E402
from hubofhubs.resolution import safe_module  # noqa: E402
from support import ROOT, run_vendored, vendor  # noqa: E402

SEAT = "reason-and-answer"
HOSTILE_NAMES = ("os:system", "os.system", "json.tool", "../x.py", "a/b", "evil;rm", "x:y")


@pytest.fixture
def no_system(monkeypatch):
    """Any call of os.system fails the test: a rejected name must never reach an import or a call."""
    def boom(*args, **kwargs):
        raise AssertionError("os.system was reached")
    monkeypatch.setattr(os, "system", boom)


@pytest.mark.parametrize("bad", HOSTILE_NAMES)
def test_a_config_value_that_is_an_import_path_is_rejected_before_esoi(bad, no_system, monkeypatch):
    from esoi import runtime
    def esoi_must_not_see_it(*args, **kwargs):
        raise AssertionError("esoi saw the value")
    monkeypatch.setattr(runtime, "choose", esoi_must_not_see_it)
    monkeypatch.setattr(runtime, "resolve", esoi_must_not_see_it)
    for config in (HubConfig(names={SEAT: bad}), HubConfig(selections={SEAT: bad}),
                   HubConfig(selection_environ={"ESOI_SELECT_HUBOFHUBS_REASON_AND_ANSWER": bad})):
        with pytest.raises(HubError, match="rejected"):
            choice(SEAT, config=config)
        with pytest.raises(HubError, match="rejected"):
            resolve(SEAT, config=config)
        with pytest.raises(HubError, match="rejected"):
            assemble(HubConfig(seats=(SEAT,), names=config.names, selections=config.selections,
                               selection_environ=config.selection_environ))
    with pytest.raises(HubError, match="rejected"):
        resolve(SEAT, bad)


def test_a_valid_looking_name_that_is_not_listed_is_refused_not_imported(no_system):
    with pytest.raises(HubError, match="unknown implementation"):
        resolve(SEAT, "os")
    assert names(SEAT) == ["tier_selector"]


def test_a_consumer_registered_object_is_never_looked_up_by_path(toys):
    register("toy-store", "acme-memory", MemoryStore)
    with pytest.raises(HubError):
        resolve("toy-store", "toy.MemoryStore")


@pytest.mark.parametrize("module", ["os", "json", "hubofhubs", "hubofhubs_evil", "hubofhubs..x", ".hubofhubs.tiers", "", None])
def test_safe_module_rejects_anything_not_inside_the_package(module):
    with pytest.raises(HubError):
        safe_module(module)


def test_safe_module_accepts_the_hubs_own_modules():
    assert safe_module("hubofhubs.tiers") == "hubofhubs.tiers"


def tamper(site: Path, module: str) -> None:
    path = site / "hubofhubs" / "esoi_selection.json"
    data = json.loads(path.read_text())
    data[SEAT]["modules"]["tier_selector"] = module
    path.write_text(json.dumps(data))


ATTEMPT = """
import json, os
marker = {marker!r}
attacker = {attacker!r}
{setup}
import hubofhubs
{after}
try:
    hubofhubs.resolve('reason-and-answer')
    raised = ''
except hubofhubs.HubError as error:
    raised = str(error)
print(json.dumps(dict(raised=raised, executed=os.path.exists(marker))))
"""


def attempt(tmp_path, module, evil_name, setup="", after=""):
    site = vendor(tmp_path / "copy")
    tamper(site, module)
    attacker = tmp_path / "attacker"
    (attacker / "hubofhubs").mkdir(parents=True)
    marker = tmp_path / "executed"
    payload = f"open({str(marker)!r}, 'w').write('x')\n"
    (attacker / evil_name).write_text(payload)
    (attacker / "hubofhubs" / "evil.py").write_text(payload)
    work = tmp_path / "work"
    work.mkdir()
    code = ATTEMPT.format(marker=str(marker), attacker=str(attacker), setup=setup, after=after)
    return run_vendored(site, code, work)


def test_a_snapshot_module_of_the_standard_library_is_rejected(tmp_path):
    out = attempt(tmp_path, "os", "evil.py")
    assert "rejected" in out["raised"] and not out["executed"]


def test_a_snapshot_module_that_only_looks_like_the_package_is_rejected(tmp_path):
    setup = "import sys; sys.path.insert(0, attacker)"
    out = attempt(tmp_path, "hubofhubs_evil", "hubofhubs_evil.py", setup)
    assert "rejected" in out["raised"] and not out["executed"]


def test_a_look_alike_module_earlier_on_sys_path_is_not_imported(tmp_path):
    # The attacker directory comes first on sys.path and holds hubofhubs/evil.py, but the package is already the vendored one.
    setup = "import sys; sys.path.insert(0, {})".format("attacker")
    out = attempt(tmp_path, "hubofhubs.evil", "unused.py", setup, after="import hubofhubs, sys; assert hubofhubs.__file__.startswith(sys.path[1])")
    assert "rejected" in out["raised"] and not out["executed"]


def test_a_module_found_outside_the_package_directory_is_rejected(tmp_path):
    # The package search path was extended to a directory that holds the module: find_spec finds it, the origin check refuses.
    out = attempt(tmp_path, "hubofhubs.evil", "unused.py", after="import hubofhubs; hubofhubs.__path__.append(attacker + '/hubofhubs')")
    assert "not inside the installed hubofhubs package" in out["raised"] and not out["executed"]


def test_a_record_filepath_that_leaves_the_package_is_rejected(tmp_path):
    chk = tmp_path / "chk"
    shutil.copytree(ROOT / "hubofhubs", chk / "hubofhubs", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "esoi", chk / "esoi")
    shutil.copy(ROOT / "esoi.toml", chk / "esoi.toml")
    rows = (chk / "esoi" / "implementations.csv").read_text().replace("hubofhubs/tiers.py", "../x.py")
    (chk / "esoi" / "implementations.csv").write_text(rows)
    marker = tmp_path / "executed"
    (tmp_path / "x.py").write_text(f"open({str(marker)!r}, 'w').write('x')\n")
    out = run_vendored(chk, ATTEMPT.format(marker=str(marker), attacker="", setup="", after=""), tmp_path)
    assert "rejected" in out["raised"] and not out["executed"]
