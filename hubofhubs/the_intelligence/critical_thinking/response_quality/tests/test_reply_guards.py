"""The reply guards of Response Quality: em dash, figures held to the evidence, day counts, machine paths. Offline; no model."""
from datetime import date, timedelta

import hubofhubs
from hubofhubs.api import (clean_value, day_count_errors, evidence_of, event_offset_errors, relativize, remove_em_dashes, strip_unsupported)
from hubofhubs.the_consciousness.representatives.quality import Criterion, QualityProfile
from hubofhubs.the_intelligence.critical_thinking.response_quality.date_arithmetic import DateArithmetic
from hubofhubs.the_intelligence.critical_thinking.response_quality.em_dash_free import EmDashFree
from hubofhubs.the_intelligence.critical_thinking.response_quality.figure_grounding import GroundedFigures

D = "—"


def test_a_single_dash_between_clauses_becomes_a_comma():
    assert remove_em_dashes(f"Saved the note {D} easy cycling from Monday.") == "Saved the note, easy cycling from Monday."
    assert remove_em_dashes(f"It is done{D}really.") == "It is done, really."


def test_a_pair_of_dashes_wraps_an_aside_in_parentheses():
    assert remove_em_dashes(f"The plan {D} which you wrote {D} works.") == "The plan (which you wrote) works."


def test_a_bullet_label_gets_a_colon_and_a_number_range_reads_as_a_range():
    assert remove_em_dashes(f"- Goal {D} run 5k") == "- Goal: run 5k"
    assert remove_em_dashes(f"Budget is 10{D}20 dollars") == "Budget is 10 to 20 dollars"


def test_a_dash_at_the_edge_of_a_line_is_dropped_and_no_hyphen_is_ever_produced():
    assert remove_em_dashes(f"Wait {D}") == "Wait"
    assert remove_em_dashes(f"{D} first") == "first"
    for text in (f"Yes {D} it can help {D} start with a goal.", f"A {D} b {D} c {D} d", f"Done. {D} Next."):
        out = remove_em_dashes(text)
        assert D not in out and "-" not in out


def test_text_without_a_dash_is_returned_untouched():
    for text in ("Plain sentence, with a comma.", "A well-known range 10-20.", "", "Line one\n\nLine two"):
        assert remove_em_dashes(text) == text
    assert remove_em_dashes(None) is None


def test_values_are_cleaned_through_lists_and_dicts_but_ids_are_left_alone():
    assert clean_value({"text": f"a {D} b", "tags": [f"x {D} y"], "item_id": f"q{D}1", "n": 3}) == {"text": "a, b", "tags": ["x, y"], "item_id": f"q{D}1", "n": 3}


def test_a_sentence_stating_a_figure_the_evidence_lacks_is_taken_out_and_the_rest_stays():
    reads = [{"locator": "tool:list", "text": "595 matching items in all"}]
    evidence = evidence_of(reads, "", "how many items are there?")
    reply = "There are **595 items**, open and done combined. That is newer than the earlier counts of 573 and 542, so go by 595. I did not get the split."
    text, dropped = strip_unsupported(reply, evidence)
    assert text == "There are **595 items**, open and done combined. I did not get the split." and dropped == ["573", "542"]
    assert strip_unsupported("It is 573.", evidence) == ("It is 573.", [])                                  # never an empty reply
    assert strip_unsupported("1. First step\n2. Second step", evidence)[0] == "1. First step\n2. Second step"       # list numbering is not a figure


def test_the_machine_folder_a_worker_wrote_in_is_shown_relative_and_a_shallow_root_is_never_hidden():
    root = "/srv/app/run-7"
    assert relativize(f"I read {root}/data/club.json and {root}/notes.md.", [root]) == "I read data/club.json and notes.md."
    assert relativize(f"saved in {root}", [root]) == "saved in the working folder"
    assert relativize("see /tmp/x/y", ["/tmp", "/"]) == "see /tmp/x/y"


def test_a_wrong_days_from_today_count_is_reported_and_the_right_one_is_not():
    evidence = "Current date: 2026-11-01 (Sunday). The guests arrive 20 Nov."
    wrong = "If they arrive a week early, on 13 Nov, that leaves you 10 days from today instead of 19."
    assert day_count_errors(wrong, evidence) == ["12 days from today to 13 Nov, not 10"]
    assert day_count_errors("On 13 Nov, that leaves you 12 days from today.", evidence) == []
    assert day_count_errors("Finish 3 days before they arrive on 20 Nov.", evidence) == []      # counts from another date: not judged
    assert day_count_errors(wrong, "- Date: Sunday, November 1, 2026") == ["12 days from today to 13 Nov, not 10"]
    due = date.today() + timedelta(days=12)           # no date in the evidence: the server's date counts, with one day of slack
    if due.year == date.today().year:
        stated = f"{due.day} {due:%b}"
        assert day_count_errors(f"On {stated} that is 13 days from today.", "no date here") == []
        assert day_count_errors(f"On {stated} that is 9 days from today.", "no date here") == [f"12 days from today to {stated}, not 9"]


def test_a_day_offset_from_an_event_date_the_paragraph_states_is_checked():
    wrong = "If they arrive early they would come on 13 Nov, and your own target is already 3 days before arrival (17 Nov). That squeezes the work."
    errors = event_offset_errors(wrong)
    assert len(errors) == 1 and "10 Nov" in errors[0] and "17 Nov" in errors[0]
    assert event_offset_errors("They would come on 13 Nov, so your target is 3 days before arrival (10 Nov).") == []
    assert event_offset_errors("The race is 2 days after arrival (22 Nov).") == []     # no earlier date to count from


def test_each_arm_judges_its_own_criterion_and_repairs_by_its_fixed_rule():
    assert GroundedFigures().judge("We sold 30 jars. Then 45 more.", "12 jars sold") == ["figure not in the evidence: 30", "figure not in the evidence: 45"]
    assert GroundedFigures().judge("It is 9.", "") == ["figure not in the evidence: 9"]                  # reported even when the repair would leave nothing
    assert GroundedFigures().repair("We sold 12 jars. Then 45 more.", "12 jars sold") == "We sold 12 jars."
    assert EmDashFree().judge(f"a {D} b", "") == ["em dash in the response: 1"] and EmDashFree().judge("a, b", "") == []
    assert EmDashFree().repair(f"a {D} b") == "a, b"
    assert DateArithmetic().judge("On 13 Nov that is 10 days from today.", "Current date: 2026-11-01") == ["12 days from today to 13 Nov, not 10"]
    assert DateArithmetic().repair("keep as given") == "keep as given"


def test_a_profile_without_the_criterion_leaves_the_arm_nothing_to_judge():
    without = QualityProfile("brief", (Criterion("concision", "short"),))
    for arm, text in ((GroundedFigures(), "It is 9."), (EmDashFree(), f"a {D} b"), (DateArithmetic(), "On 13 Nov that is 10 days from today.")):
        assert arm.judge(text, "Current date: 2026-11-01", without) == []


def test_the_arms_are_declared_on_the_response_quality_seat_and_the_entry_still_judges_links():
    assert hubofhubs.run("response-quality", {"response": "See https://x.example/a", "evidence": "https://y.example/b"}) == ["link not in the evidence: https://x.example/a"]
