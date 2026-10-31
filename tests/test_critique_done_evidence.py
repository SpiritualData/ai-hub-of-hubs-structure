"""done_evidence: coverage as data, the gap, the stop or continue rule and the code-written lines. No model call."""
from hubofhubs.critique import done_evidence as de


def test_nothing_declared_is_never_a_gap():
    for raw in (None, {}, "x", {"processed": "a"}, {"processed": -1}, {"processed": True}):
        assert de.coverage_gap(raw) is None


def test_a_known_total_above_processed_is_a_gap_and_a_complete_flag_wins():
    gap = de.coverage_gap({"processed": 200, "total": 344, "unit": "entries", "next_skip": 200})
    assert (gap.remaining, gap.next_skip, gap.unit) == (144, 200, "entries")
    assert de.coverage_gap({"processed": 344, "total": 344}) is None
    assert de.coverage_gap({"processed": 200, "total": 344, "complete": True}) is None


def test_a_capped_read_of_unknown_size_is_a_gap_with_no_remaining_count():
    gap = de.coverage_gap({"processed": 200, "capped": True})
    assert gap is not None and gap.total is None and gap.remaining is None


def test_progress_is_the_difference_between_an_advancing_job_and_a_repeat():
    assert de.coverage_progress(None, {"processed": 5})
    assert de.coverage_progress({"processed": 5}, {"processed": 9})
    assert not de.coverage_progress({"processed": 9}, {"processed": 9})
    assert not de.coverage_progress({"processed": 9}, None)


def test_continue_decision_is_structural():
    gap = de.coverage_gap({"processed": 1, "total": 9})
    assert de.continue_decision(None, attempts_left=3)[0] == de.STOP_COMPLETE
    assert de.continue_decision(gap, attempts_left=3)[0] == de.CONTINUE
    assert de.continue_decision(gap, attempts_left=0)[0] == de.STOP_NO_BUDGET
    assert de.continue_decision(gap, attempts_left=3, budget_left=0)[0] == de.STOP_NO_BUDGET
    assert de.continue_decision(gap, attempts_left=3, progressed=False)[0] == de.STOP_NO_PROGRESS


def test_the_coverage_lines_state_the_numbers_and_how_to_continue():
    part = {"processed": 1200, "total": 5200, "unit": "entries", "next_skip": 1200}
    assert de.render_coverage_line(part) == "Coverage: 1,200 of 5,200 entries processed (4,000 not yet covered)."
    assert "continue from entries 1,201" in de.render_continue_plan(part)
    full = {"processed": 344, "total": 344, "unit": "entries"}
    assert de.render_coverage_line(full) == "Coverage: 344 of 344 entries processed."
    assert de.render_continue_plan(full) == "" and de.render_coverage_line(None) == ""


def test_requirements_are_bounded_and_interim_data_has_the_agreed_shape():
    items = de.clean_requirements(["  a  b ", "", 3, "x" * 500, "c", "d", "e"])
    assert len(items) == 4 and items[0] == "a b" and len(items[1]) == de.MAX_REQUIREMENT_CHARS
    assert de.render_requirements(["one", "two"]) == "  R1. one\n  R2. two"
    data = de.interim_data({"processed": 2, "total": 4}, attempt=1)
    assert data["final"] is False and data["coverage"]["total"] == 4 and data["attempt"] == 1
    assert de.interim_data(None) == {"final": False, "coverage": None}
