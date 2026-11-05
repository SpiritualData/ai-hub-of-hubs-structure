"""Install honesty: every dependency of the distribution is pinned to a tag, a commit, a branch ref or a version range; none is a
bare name that would take whatever is newest.

Our own repositories are installed from `@main` by every consumer with one identical direct-URL string, because pip refuses two
different direct URLs for one package (the 2026-10-19 production image build failure). Tags and a version range arrive together
in the coordinated release window, in every consumer at once."""
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BARE = re.compile(r"^[A-Za-z0-9_.-]+(\[[^\]]*\])?$")
PINNED = re.compile(r"(@\s*git\+https://\S+@(v?\d|main\b)|==|~=|>=|<=|<|>)")
CONSUMER_ESOI = "esoi @ git+https://github.com/JoshuaMathias/evolvable-structure.git@main#subdirectory=implementations/python"


def declared():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    found = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        found += extra
    return found


def test_no_dependency_is_a_bare_unpinned_name():
    bare = [d for d in declared() if BARE.match(d.strip()) or not PINNED.search(d)]
    assert not bare, f"every dependency, core or optional, names a tag, a commit or a version bound: {bare}"


def test_esoi_uses_the_exact_direct_url_string_the_consumers_use():
    deps = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    esoi = [d for d in deps if d.startswith("esoi")]
    assert esoi == [CONSUMER_ESOI]


def test_the_version_is_bumped_with_the_pin():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["version"] == "0.3.0"
