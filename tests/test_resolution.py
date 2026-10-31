"""The hub's binding of esoi.assemble: its default arm, its name for the default layer, its refusal to be shadowed.
The generic behaviour (names, cascade, build order, cycles, safe loading) is tested in the esoi library."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs import AssemblyConfig, AssemblyError, assemble, choice, names, register, resolve  # noqa: E402

SEAT = "reason-and-answer"


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
    system = assemble()
    assert system.solutions() == ["card-store", "reason-and-answer"]
    assert all(line.startswith(seat + ":") for seat, line in system.pending.items())
    assert "no selected arm; pass arms=" in system.pending["search-backend"]
    assert "pass provided=" in system.pending["model-call"]


def test_assemble_overrides_name_only_what_differs():
    register("card-store", "other-store", type("OtherStore", (), {"__init__": lambda self, repository: None}))
    system = assemble(arms={"card-store": "other-store"}, options={"card-store": {"repository": 1}})
    assert type(system["card-store"]).__name__ == "OtherStore" and "card-store" not in system.pending
    assert "card-store" in assemble(arms={"card-store": "other-store"}).pending
    mine = object.__new__(type("Mine", (), {"add": 0, "get": 0, "search": 0, "delete": 0, "count": 0}))
    assert assemble(provided={"card-store": mine})["card-store"] is mine
    with pytest.raises(TypeError):
        assemble(AssemblyConfig(), arms={"card-store": "x"})
