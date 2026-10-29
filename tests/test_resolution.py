"""register, names, the cascade and isolation between two consumers in one process."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import toy  # noqa: E402
from toy import MemoryStore, StoreIndex, toys  # noqa: E402,F401
from hubofhubs import HubConfig, HubError, assemble, choice, names, register, resolve  # noqa: E402
from hubofhubs.resolution import check_name  # noqa: E402

SEAT = "reason-and-answer"


def test_a_consumer_registers_a_name_it_owns_and_selects_it_on_its_own_config(toys):
    register("toy-store", "acme-memory", MemoryStore)
    assert names("toy-store") == ["acme-memory"]
    assert resolve("toy-store", "acme-memory") is MemoryStore
    assert choice("toy-store", config=HubConfig(selections={"toy-store": "acme-memory"})).layer == "consumer selections"


def test_replacing_or_shadowing_a_hub_declared_name_raises():
    class Mine:
        pass
    for replace in (False, True):
        with pytest.raises(HubError, match="declared by the hub"):
            register(SEAT, "tier_selector", Mine, replace=replace)
    assert resolve(SEAT).__name__ == "TierSelector"


def test_a_consumer_may_replace_its_own_name(toys):
    register("toy-store", "acme-memory", MemoryStore)
    register("toy-store", "acme-memory", StoreIndex, replace=True)
    assert resolve("toy-store", "acme-memory") is StoreIndex


def test_register_validates_the_solution_and_the_name(toys):
    for sid, name in (("no-such-seat", "ok"), ("toy-store", "has.dot"), ("toy-store", "os:system"), ("toy-store", "Upper")):
        with pytest.raises(HubError):
            register(sid, name, MemoryStore)


def test_name_pattern():
    for good in ("a", "tier_selector", "x-1", "0abc"):
        assert check_name(good) == good
    for bad in ("", "-a", "_a", "a.b", "a:b", "A", "a b", "a\n", "../x", None, 3):
        with pytest.raises(HubError):
            check_name(bad)


def test_a_name_that_is_not_listed_is_an_error_naming_the_choices(toys):
    register("toy-store", "acme-memory", MemoryStore)
    with pytest.raises(HubError) as caught:
        resolve("toy-store", "other")
    message = str(caught.value)
    assert "toy-store" in message and "hubofhubs" in message and "explicit name" in message and "acme-memory" in message
    with pytest.raises(HubError, match="consumer selections"):
        choice("toy-store", config=HubConfig(selections={"toy-store": "other"}))


def test_the_cascade_is_explicit_then_selections_then_hub_default(toys):
    register(SEAT, "acme-selector", type("Selector", (), {}))
    assert choice(SEAT).layer == "hub default"
    assert choice(SEAT, config=HubConfig(selections={SEAT: "acme-selector"})).name == "acme-selector"
    both = HubConfig(selections={SEAT: "acme-selector"}, names={SEAT: "tier_selector"})
    assert (choice(SEAT, config=both).name, choice(SEAT, config=both).layer) == ("tier_selector", "explicit name")
    assert choice(SEAT, "tier_selector", HubConfig(selections={SEAT: "acme-selector"})).layer == "explicit name"


def test_two_consumers_with_different_selections_do_not_affect_each_other(toys):
    register(SEAT, "first-selector", type("First", (), {}))
    register(SEAT, "second-selector", type("Second", (), {}))
    one = assemble(HubConfig(seats=(SEAT,), selections={SEAT: "first-selector"}))
    two = assemble(HubConfig(seats=(SEAT,), selections={SEAT: "second-selector"}))
    default = assemble(HubConfig(seats=(SEAT,)))
    assert (type(one[SEAT]).__name__, type(two[SEAT]).__name__, type(default[SEAT]).__name__) == ("First", "Second", "TierSelector")
    assert one.choice(SEAT).name == "first-selector" and two.choice(SEAT).name == "second-selector"
