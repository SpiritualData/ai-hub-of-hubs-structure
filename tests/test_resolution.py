"""The hub's binding of esoi.assemble: its default arm, its name for the default layer, its refusal to be shadowed.
The generic behaviour (names, cascade, build order, cycles, safe loading) is tested in the esoi library."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs import HubConfig, HubError, assemble, choice, names, register, resolve  # noqa: E402

SEAT = "reason-and-answer"


def test_replacing_or_shadowing_a_hub_declared_name_raises():
    class Mine:
        pass
    for replace in (False, True):
        with pytest.raises(HubError, match="declared by the hub"):
            register(SEAT, "tier_selector", Mine, replace=replace)
    assert resolve(SEAT).__name__ == "TierSelector"


def test_a_consumer_selection_beats_the_hub_default_and_two_consumers_do_not_see_each_other():
    register(SEAT, "first-selector", type("First", (), {}))
    register(SEAT, "second-selector", type("Second", (), {}))
    assert choice(SEAT).layer == "hub default" and names(SEAT) == ["first-selector", "second-selector", "tier_selector"]
    built = [assemble(HubConfig(seats=(SEAT,), selections=sel))[SEAT] for sel in
             ({SEAT: "first-selector"}, {SEAT: "second-selector"}, {})]
    assert [type(obj).__name__ for obj in built] == ["First", "Second", "TierSelector"]


def test_the_hub_default_builds_without_a_consumer():
    system = assemble(HubConfig(seats=(SEAT,)))
    assert type(system[SEAT]).__name__ == "TierSelector" and "layer: hub default" in system.reasons[0]
