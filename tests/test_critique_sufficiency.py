"""The structural sufficiency gate, unit pieces: an abridged context item declares how to fetch the whole source, and the
check compares that declaration with the reads that actually ran."""
from typing import Any, Dict

from hubofhubs.critique.sufficiency import (
    AbridgedTurnState,
    collect_abridged_items,
    render_abridged_notice,
    spec_covers,
    unfetched_abridged,
)

SUMMARY = "Notes on the remaining gaps"
FETCH_SPEC: Dict[str, Any] = {"query": {"kind": "document", "id": "d1", "include_notes": True}}


def abridged_card() -> Dict[str, Any]:
    """One card whose single content item is a summary that declares how to fetch the real source."""
    return {
        "id": "card_gaps",
        "title": "Remaining gaps",
        "items": [{
            "id": "item_1",
            "type": "note",
            "why": "the gap list",
            "text": SUMMARY,
            "locator": {"text": SUMMARY, "full_ref": FETCH_SPEC},
            "pointer_eligible": False,
        }],
    }


def test_collects_only_items_that_declare_a_usable_fetch():
    plain = {"id": "c2", "items": [{"id": "i", "type": "note", "locator": {"text": "just a fact"}}]}
    junk = {"id": "c3", "items": [{"id": "i", "type": "note",
                                   "locator": {"text": "x", "full_ref": {"nonsense": 1}}}]}
    items = collect_abridged_items([abridged_card(), plain, junk])
    assert len(items) == 1
    assert items[0].fetch == FETCH_SPEC
    assert items[0].chars == len(SUMMARY)
    assert items[0].card_id == "card_gaps"


def test_same_source_on_two_cards_forces_one_read():
    a, b = abridged_card(), abridged_card()
    b["id"] = "card_other"
    assert len(collect_abridged_items([a, b])) == 1


def test_notice_names_the_fetch_and_forbids_asking_permission():
    notice = render_abridged_notice(collect_abridged_items([abridged_card()]))
    assert "document" in notice
    assert "SUMMARY" in notice
    assert "do NOT ask the user" in notice
    assert render_abridged_notice([]) == ""


def test_spec_coverage_matches_the_nested_and_flat_shapes():
    flat = {"kind": "document", "id": "d1", "include_notes": True}
    assert spec_covers(flat, FETCH_SPEC)                      # adapters see the flattened shape
    assert spec_covers({**flat, "limit": 20}, FETCH_SPEC)     # extra filters still cover it
    assert not spec_covers({"kind": "document", "id": "OTHER"}, FETCH_SPEC)
    assert not spec_covers({"rel_path": "README.md"}, FETCH_SPEC)


def test_unfetched_is_computed_from_reads_that_actually_ran():
    items = collect_abridged_items([abridged_card()])
    assert unfetched_abridged(items, []) == items
    assert unfetched_abridged(items, [FETCH_SPEC]) == []
    state = AbridgedTurnState(items=items)
    assert state.should_force_read() == items
    state.record_reads([FETCH_SPEC])
    assert state.should_force_read() == []
