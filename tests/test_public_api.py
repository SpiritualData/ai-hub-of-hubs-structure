"""The front door: a consumer reaches every interface through `hubofhubs.api` and `hubofhubs.run`, never an internal module path."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from support import ROOT  # noqa: E402

import hubofhubs  # noqa: E402
from esoi import selection  # noqa: E402
from hubofhubs import api  # noqa: E402

INTERNAL_IMPORT = re.compile(r"^\s*(?:>>> |\.\.\. )?(?:from|import) hubofhubs\.(?!api\b)[A-Za-z_]", re.M)


def test_every_public_name_resolves():
    missing = []
    for name in api.__all__:
        try:
            getattr(api, name)
        except Exception as error:  # a moved module whose entry in LOCATIONS was not updated
            missing.append((name, repr(error)[:80]))
    assert missing == []


def test_every_interface_of_the_records_is_exported():
    hubofhubs.HUB.prepare()
    unexported = []
    for key, entry in selection.REGISTRY.items():
        if entry.interface is None or key[0] != "hubofhubs":
            continue
        name = entry.interface.__name__
        if getattr(api, name, None) is not entry.interface:
            unexported.append(f"{key[1]}: {name}")
    assert unexported == []


def test_the_front_door_is_the_same_object_as_the_package_entry():
    assert api.run is hubofhubs.run and api.assemble is hubofhubs.assemble and api.Binding is hubofhubs.Binding


def test_a_typed_handle_comes_from_the_public_name():
    from hubofhubs.api import CardStore
    assert hubofhubs.run(CardStore) is not None


def test_consumer_facing_docs_import_no_internal_path():
    docs = [ROOT / "README.md", ROOT / "CONTRIBUTING.md"]
    for folder in ("tutorials", "how-to"):
        docs += sorted((ROOT / "docs" / folder).glob("*.md"))
    docs += [ROOT / "docs" / "explanation" / "science-search.md"]
    offenders = [f"{path.relative_to(ROOT)}: {line.strip()}" for path in docs for line in path.read_text().splitlines()
                 if INTERNAL_IMPORT.match(line)]
    assert offenders == [], "import from hubofhubs.api, not an internal path"


def test_a_submodule_is_listed_by_its_module_path_not_as_an_attribute_of_its_package():
    """``package:module`` fails when nothing has imported the submodule yet; a module is listed as ``package.module``."""
    from hubofhubs import api
    root = Path(api.__file__).resolve().parents[1]
    wrong = [name for name, target in api.LOCATIONS.items() if ":" in target
             and any((root.joinpath(*target.partition(":")[0].split("."), target.partition(":")[2] + suffix)).exists()
                     for suffix in (".py", "/__init__.py"))]
    assert not wrong, wrong
