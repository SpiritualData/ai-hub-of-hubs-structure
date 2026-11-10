"""Choosing an approach: distinct views, deduplication, the unlabelled picking call and its fallbacks, with a stub decide (no model call)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))
from hubofhubs.api import DEFAULT_VIEWS, choose_approach  # noqa: E402

DIRECT = {"name": "Direct draft", "how": "Write it straight away. Check it once.", "disadvantage": "Misses edge cases."}
REUSE = {"name": "Reuse the template", "how": "Start from the existing template. Adapt it.", "disadvantage": "Inherits its limits."}
SPECIALIST = {"name": "Specialist review", "how": "Draft, then review against a checklist.", "disadvantage": "Slower."}


def stub(proposals, pick):
    asked = []

    def decide(prompt):
        asked.append(prompt)
        if "Which one would best meet" in prompt:
            return json.dumps(pick)
        for view, proposal in zip(DEFAULT_VIEWS, proposals):
            if view in prompt:
                return json.dumps(proposal)
        return "{}"
    decide.asked = asked
    return decide


def test_the_picked_index_names_the_chosen_approach_and_the_rest_are_alternatives():
    probe = stub([DIRECT, REUSE, SPECIALIST], {"index": 1})
    first = choose_approach("make a script", ["short"], probe)
    listing = [p for p in probe.asked if "Which one would best meet" in p][0]
    shown = [line.split(". ", 1)[1].split(":")[0] for line in listing.splitlines() if line[:2] in ("1.", "2.", "3.")]
    assert first["chosen"]["name"] == shown[0] and first["calls"] == 4 and len(first["alternatives"]) == 2
    assert "Direct draft" not in listing.split("Which one")[0].split("The approaches")[0]      # no view label is shown


def test_the_order_shown_is_deterministic_for_a_frame():
    one, two = stub([DIRECT, REUSE, SPECIALIST], {"index": 1}), stub([DIRECT, REUSE, SPECIALIST], {"index": 1})
    assert choose_approach("frame", [], one)["chosen"] == choose_approach("frame", [], two)["chosen"]


def test_an_invalid_index_falls_back_to_the_first_valid_approach():
    out = choose_approach("make a script", ["short"], stub([DIRECT, REUSE, SPECIALIST], {"index": 9}))
    assert out["chosen"] == DIRECT and len(out["alternatives"]) == 2 and out["reason"] == ""


def test_the_same_name_is_one_approach_and_fewer_than_two_skips_the_picking_call():
    probe = stub([DIRECT, dict(REUSE, name="  direct DRAFT "), {"name": "", "how": "x"}], {"index": 1})
    out = choose_approach("make a script", [], probe)
    assert out["chosen"] == DIRECT and out["alternatives"] == [] and out["calls"] == 3
    assert not any("Which one would best meet" in p for p in probe.asked)


def test_no_valid_view_gives_no_choice():
    assert choose_approach("x", [], lambda prompt: "nothing")["chosen"] is None
