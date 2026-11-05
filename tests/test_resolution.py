"""The hub's binding of esoi.runtime.assemble_by_name.assemble: its default arm, its name for the default layer, its refusal to be shadowed.
The generic behaviour (names, cascade, build order, cycles, safe loading) is tested in the esoi library."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs import AssemblyConfig, AssemblyError, assemble, choice, names, register, resolve  # noqa: E402

SEAT = "model-tier-chooser"


def test_replacing_or_shadowing_a_hub_declared_name_raises():
    class Mine:
        pass
    for replace in (False, True):
        with pytest.raises(AssemblyError, match="declared by the hubofhubs"):
            register(SEAT, "tier_selector", Mine, replace=replace)
    assert resolve(SEAT).__name__ == "TierSelector"


def test_a_consumer_selection_beats_the_hub_default_and_two_consumers_do_not_see_each_other():
    register(SEAT, "first-selector", type("First", (), {}))
    register(SEAT, "second-selector", type("Second", (), {}))
    assert choice(SEAT).layer == "hubofhubs default" and names(SEAT) == ["first-selector", "second-selector", "tier_selector"]
    built = [assemble(AssemblyConfig(solutions=(SEAT,), selections=sel))[SEAT] for sel in
             ({SEAT: "first-selector"}, {SEAT: "second-selector"}, {})]
    assert [type(obj).__name__ for obj in built] == ["First", "Second", "TierSelector"]


def test_the_hub_default_builds_without_a_consumer():
    system = assemble(AssemblyConfig(solutions=(SEAT,)))
    assert type(system[SEAT]).__name__ == "TierSelector" and "layer: hubofhubs default" in system.reasons[0]


def test_assemble_with_no_arguments_builds_the_selected_arms_and_reports_the_rest():
    system = assemble(environ={})
    built = set(system.solutions())
    assert {"card-store", "cards-from-files", "model-tier-chooser", "research-freshness-reader", "the-mind", "the-subconscious", "critical-thinking"} <= built
    assert built.isdisjoint(system.pending)
    assert all(line.startswith(seat + ":") or line.startswith(seat + " (") for seat, line in system.pending.items())
    assert "GEMINI_API_KEY" in system.pending["web-search"] and "HUBOFHUBS_WRITE_ROOT" in system.pending["file-editing"]
    assert "vendor-model-caller (multi_provider)" in system.pending["vendor-model-caller"] and "model-plumbing" in system.pending      # the selected router waits for the consumer's providers
    assert "vendor-model-caller" in assemble(arms={"vendor-model-caller": "claude_cli"}, environ={}).solutions()      # the keyless arm runs claude -p on the subscription when a consumer picks it


def test_assemble_overrides_name_only_what_differs():
    register("card-store", "other-store", type("OtherStore", (), {"__init__": lambda self, repository: None}))
    system = assemble(arms={"card-store": "other-store"}, options={"card-store": {"repository": 1}})
    assert type(system["card-store"]).__name__ == "OtherStore" and "card-store" not in system.pending
    assert "card-store" in assemble(arms={"card-store": "other-store"}).pending
    mine = object.__new__(type("Mine", (), {"add": 0, "get": 0, "search": 0, "delete": 0, "count": 0}))
    assert assemble(provided={"card-store": mine})["card-store"] is mine
    with pytest.raises(TypeError):
        assemble(AssemblyConfig(), arms={"card-store": "x"})


def test_a_child_assembler_builds_on_the_hub_and_the_hub_is_unchanged_by_it(tmp_path):
    from esoi import Assembler
    from hubofhubs import assembler
    child = Assembler("childpkg", tmp_path, parent=assembler())
    assert child.choice("card-store").layer == "hubofhubs default" and assembler().choice("card-store").name == "local_card_store"
    child.register("card-store", "child-store", type("ChildStore", (), {}))
    system = child.assemble(AssemblyConfig(solutions=("card-store",), selections={"card-store": "child-store"},
                                           reasons={"card-store": ["unconfirmed: a test."]}))
    assert type(system["card-store"]).__name__ == "ChildStore" and "child-store" not in names("card-store")
    assert child.overrides(AssemblyConfig(selections={"card-store": "child-store"}))[0].parent_default == "local_card_store"
    assert assemble(AssemblyConfig(solutions=("card-store",)))["card-store"] is not None
