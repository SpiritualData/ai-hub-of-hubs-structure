"""Install honesty: every dependency of the distribution is pinned to a tag, a commit or a version range; none is a bare name that
would take whatever is newest."""
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BARE = re.compile(r"^[A-Za-z0-9_.-]+(\[[^\]]*\])?$")
PINNED = re.compile(r"(@\s*git\+https://\S+@v?\d|==|~=|>=|<=|<|>)")


def declared():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    found = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        found += extra
    return found


def test_no_dependency_is_a_bare_unpinned_name():
    bare = [d for d in declared() if BARE.match(d.strip()) or not PINNED.search(d)]
    assert not bare, f"every dependency, core or optional, names a tag, a commit or a version bound: {bare}"


def test_esoi_is_installed_from_its_git_tag():
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    esoi = [d for d in deps if d.startswith("esoi")]
    assert esoi == ["esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git@v0.3.0#subdirectory=implementations/python"]


def test_the_version_is_bumped_with_the_pin():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.2.0"
