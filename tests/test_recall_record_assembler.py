"""The record assembler finds a record by a name the message uses, respects scope tags, and never raises. Offline."""
from hubofhubs.recall.record_assembler import RecordContextAssembler, rank_records

RECORDS = [
    {"id": "n1", "title": "Language", "text": "Dana only teaches on Tuesday and Thursday evenings, never on Friday.", "scope_tags": ["group:a"]},
    {"id": "n2", "title": "Garden", "text": "Plant the beans after the last frost and water twice a week.", "scope_tags": ["group:b"]},
    {"id": "n3", "title": "Money", "text": "Budget cap is 2000 and the invoice is due next week.", "scope_tags": ["group:c"]},
]


def test_a_name_in_the_message_finds_the_record_that_mentions_it():
    out = RecordContextAssembler(lambda meta: RECORDS).assemble("Can you help me book Dana for Friday?")
    assert out.card_ids == ["n1"] and "Tuesday and Thursday" in out.context_view


def test_a_message_naming_nothing_in_the_records_adds_nothing():
    assert RecordContextAssembler(lambda meta: RECORDS).assemble("What is the weather?").context_view == ""


def test_a_word_in_most_records_alone_does_not_admit_one():
    same = [{"id": str(i), "text": f"week {i} plan"} for i in range(5)]
    assert rank_records("plan", same, min_score=1.0) == []


def test_a_turn_scoped_to_one_group_sees_only_that_groups_records():
    out = RecordContextAssembler(lambda meta: RECORDS).assemble("book Dana", meta={"scope_tags": ["group:b"]})
    assert out.context_view == ""


def test_the_listing_is_cached_and_a_broken_lister_returns_nothing():
    calls = []
    arm = RecordContextAssembler(lambda meta: calls.append(1) or RECORDS)
    arm.assemble("book Dana"), arm.assemble("book Dana")
    assert len(calls) == 1

    def broken(meta):
        raise RuntimeError("down")
    assert RecordContextAssembler(broken).assemble("book Dana").context_view == ""
