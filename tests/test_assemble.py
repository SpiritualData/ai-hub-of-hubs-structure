"""assemble: dependency order, provided objects, cycles, unmet needs, options, frozen result."""
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import toy  # noqa: E402
from toy import (IndexNeedsReport, IndexReport, LoopA, LoopB, MemoryStore, ReportNeedsStore, StoreIndex,
                 StoreNeedsIndex, toys)  # noqa: E402,F401
from hubofhubs import HubConfig, HubError, assemble, register  # noqa: E402
from hubofhubs.needs import needs_of  # noqa: E402


def wire():
    register("toy-store", "acme-memory", MemoryStore)
    register("toy-index", "acme-index", StoreIndex)
    register("toy-report", "acme-report", IndexReport)
    return HubConfig(seats=("toy-report",), selections={"toy-store": "acme-memory", "toy-index": "acme-index",
                                                        "toy-report": "acme-report"})


def test_needs_read_from_typed_parameters(toys):
    assert needs_of(StoreIndex) == {"store": "toy-store"}
    assert needs_of(IndexReport) == {"index": "toy-index"}
    assert needs_of(MemoryStore) == {} and needs_of(object()) == {}


def test_objects_are_built_in_dependency_order_and_the_needs_are_injected(toys):
    system = assemble(wire())
    assert system.seats() == ["toy-store", "toy-index", "toy-report"]
    system["toy-store"].put("k", "v")
    assert system["toy-report"].render() == "report:v"
    assert system["toy-index"].store is system["toy-store"]


def test_a_provided_object_wins_for_its_seat(toys):
    mine = MemoryStore()
    mine.put("k", "mine")
    system = assemble(wire(), provided={"toy-store": mine})
    assert system["toy-store"] is mine and system["toy-report"].render() == "report:mine"
    assert "layer: consumer provided" in system.reason_by_seat["toy-store"]


def test_a_provided_object_must_satisfy_the_seat(toys):
    with pytest.raises(HubError, match="does not satisfy ToyStore"):
        assemble(wire(), provided={"toy-store": object()})
    with pytest.raises(HubError, match="unknown solution"):
        assemble(wire(), provided={"no-such-seat": object()})


def test_an_unmet_need_fails_at_startup_naming_the_chain(toys):
    register("toy-index", "acme-index", StoreIndex)
    with pytest.raises(HubError) as caught:
        assemble(HubConfig(seats=("toy-index",), selections={"toy-index": "acme-index"}))
    assert "toy-index (acme-index) needs toy-store: no arm, not provided" in str(caught.value)
    assert "toy-index -> toy-store" in str(caught.value)
    with pytest.raises(HubError, match="toy-store: no arm, not provided"):
        assemble(HubConfig(seats=("toy-store",)))


def test_a_cycle_fails_at_startup_naming_the_ring(toys):
    register("toy-index", "loop-a", LoopA)
    register("toy-report", "loop-b", LoopB)
    with pytest.raises(HubError) as caught:
        assemble(HubConfig(seats=("toy-index",), selections={"toy-index": "loop-a", "toy-report": "loop-b"}))
    assert "dependency cycle: toy-index -> toy-report -> toy-index" in str(caught.value)


def test_a_longer_cycle_names_every_seat(toys):
    register("toy-report", "r2", ReportNeedsStore)
    register("toy-store", "s2", StoreNeedsIndex)
    register("toy-index", "i2", IndexNeedsReport)
    config = HubConfig(seats=("toy-report",), selections={"toy-report": "r2", "toy-store": "s2", "toy-index": "i2"})
    with pytest.raises(HubError, match="toy-report -> toy-store -> toy-index -> toy-report"):
        assemble(config)


def test_options_reach_the_constructor_and_unknown_options_fail(toys):
    config = wire()
    config = HubConfig(seats=config.seats, selections=config.selections, options={"toy-index": {"prefix": "p-"}})
    system = assemble(config)
    assert system["toy-index"].prefix == "p-"
    bad = HubConfig(seats=config.seats, selections=config.selections, options={"toy-index": {"nope": 1}})
    with pytest.raises(HubError, match="no option"):
        assemble(bad)


def test_the_reason_line_names_seat_arm_layer_version_and_hash(toys):
    system = assemble(wire())
    line = system.reason_by_seat["toy-store"]
    assert line.startswith("toy-store -> acme-memory (layer: consumer selections, package version ")
    assert "config hash " in line and len(system.reasons) == 3


def test_the_hub_default_builds_without_a_consumer():
    system = assemble(HubConfig(seats=("reason-and-answer",)))
    assert type(system["reason-and-answer"]).__name__ == "TierSelector"
    assert "layer: hub default" in system.reasons[0]


def test_the_result_is_frozen_and_threads_can_use_it(toys):
    system = assemble(wire())
    with pytest.raises(TypeError):
        system.objects["x"] = 1
    system["toy-store"].put("k", "v")
    seen = []
    threads = [threading.Thread(target=lambda: seen.append(system["toy-report"].render())) for _ in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert seen == ["report:v"] * 8
    with pytest.raises(HubError, match="was not assembled"):
        system["nothing"]
