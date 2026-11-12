"""Structure in conversation: the arms, the reading of a metric value, the terms and the advisory parser. No model is called."""
from hubofhubs.api import MOVES, NoStructure, StructureMove, TERMS, vocabulary_note
from hubofhubs.the_intelligence.critical_thinking.structure_in_conversation import advisory
from hubofhubs.the_intelligence.critical_thinking.structure_in_conversation.moves import reading_of

RECORDS = {"problems": {"p": {"name": "A problem"}}, "ideals": {"i": {"name": "An ideal"}},
           "solutions": {"s": {"name": "A solution", "problem_ids": "p", "ideal_ids": "i", "milestones": "1. First target"}},
           "implementations": {"a": {"solution_id": "s", "name": "Held option"}},
           "metrics": {"m": {"name": "A measure", "solution_ids": "s", "record": "Current value: 3 (as of 2026-01-02, from the person's report)"}}}
DRAFT = {"solution_name": "A solution", "alternatives": [{"name": "Held option"}, {"name": "New option", "description": "d"}], "metric": {"name": "Other", "record": "r"}}


def test_none_arm_is_plain():
    assert NoStructure().decide({"move": "frame", "records": RECORDS, "draft": DRAFT}) == {"move": "none", "block": None, "offer": None}


def test_a_plain_or_unknown_move_stays_plain():
    for move in ("none", "banter", ""):
        assert StructureMove().decide({"move": move, "records": RECORDS})["block"] is None


def test_frame_reuses_held_records_and_offers_only_the_missing_alternative():
    result = StructureMove().decide({"move": "frame", "records": RECORDS, "relevant_solution_ids": ["s"], "draft": DRAFT})
    assert result["block"]["metric"]["existing"] and result["block"]["metric"]["reading"]["value"] == "3"
    assert [edit["table"] for edit in result["offer"]["edits"]] == ["implementations"]
    assert result["offer"]["edits"][0]["fields"]["solution_id"] == "s"


def test_a_declined_offer_is_not_made_again():
    first = StructureMove().decide({"move": "frame", "records": RECORDS, "relevant_solution_ids": ["s"], "draft": DRAFT})
    again = StructureMove().decide({"move": "frame", "records": RECORDS, "relevant_solution_ids": ["s"], "draft": DRAFT, "declined": [first["offer"]["key"]]})
    assert again["offer"] is None and again["block"]


def test_review_shows_only_a_value_the_records_hold():
    held = {key: dict(value) for key, value in RECORDS.items()}
    held["metrics"] = {"m": {"name": "A measure", "solution_ids": "s", "record": "No value yet."}}
    block = StructureMove().decide({"move": "review", "records": held, "relevant_solution_ids": ["s"], "draft": DRAFT})["block"]
    assert block["metric"]["reading"] is None and "alternatives" not in block


def test_reading_of_needs_the_leading_line():
    assert reading_of("Current value: 4 of 5 (as of 2026-02-03, from a log)\nmore") == {"value": "4 of 5", "as_of": "2026-02-03", "source": "a log"}
    assert reading_of("It was Current value: 9") is None


def test_terms_have_one_meaning_each_and_no_em_dash():
    assert len({term for term, meaning in TERMS}) == 6 and chr(0x2014) not in vocabulary_note() and set(MOVES) >= {"none", "frame"}


def test_advisory_parse_defaults_to_false():
    assert advisory.parse("no json", ("a", "b")) == {"a": False, "b": False}
    assert advisory.parse('x {"a": true, "b": "yes"} y', ("a", "b")) == {"a": True, "b": False}
