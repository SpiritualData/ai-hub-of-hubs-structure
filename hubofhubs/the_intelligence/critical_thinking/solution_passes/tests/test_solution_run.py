"""The solution run helpers: which requirements each unit fails, keep-the-better for a rewritten unit, and the labelled solution frame."""
from hubofhubs.the_intelligence.critical_thinking.solution_passes.solution_run import keep_better, solution_frame, unmet_by_unit

REQS = ["names a source", "has a hook", "ends with a call"]


def meets(requirement, unit):
    return requirement in unit


def test_unmet_by_unit_lists_the_failed_requirements_per_unit_in_rubric_order():
    calls = []

    def seen(requirement, unit):
        calls.append((requirement, unit))
        return requirement in unit
    units = ["names a source has a hook", "ends with a call", "everything: " + " ".join(REQS)]
    got = unmet_by_unit(units, REQS, seen)
    assert got == [["ends with a call"], ["names a source", "has a hook"], []]
    assert len(calls) == 9 and len(set(calls)) == 9       # each (requirement, unit) is asked once


def test_unmet_by_unit_with_no_requirements_is_an_empty_list_per_unit():
    assert unmet_by_unit(["a", "b"], [], meets) == [[], []]


def test_keep_better_keeps_the_new_unit_only_when_it_meets_strictly_more():
    have = lambda r, u: r in u     # noqa: E731
    old = "names a source"
    assert keep_better(old, "names a source has a hook", REQS, have) == ("names a source has a hook", True)
    assert keep_better(old, "names a source", REQS, have) == (old, False)            # equal: the old one stays
    assert keep_better(old, "has a hook", REQS, have) == (old, False)                # equal count, different requirement
    assert keep_better("names a source has a hook", "ends with a call", REQS, have) == ("names a source has a hook", False)    # worse


def test_keep_better_without_requirements_keeps_the_old_unit():
    assert keep_better("old", "new", [], lambda r, u: True) == ("old", False)


def test_solution_frame_labels_only_what_is_present():
    got = solution_frame({"approach": "Write one script per video.", "next_milestone": "100 subscribers", "metric_disadvantages": "",
                          "implementation_disadvantages": None, "last_value": "3 of 10", "unmet": ["Part 2: has a hook", "Part 3: ends with a call"]})
    assert got.splitlines() == ["Approach: Write one script per video.", "Next unmet milestone: 100 subscribers", "Last measured value: 3 of 10",
                                "Unmet from the last measure: Part 2: has a hook; Part 3: ends with a call"]


def test_solution_frame_is_empty_when_nothing_is_present_and_is_capped():
    assert solution_frame({}) == "" and solution_frame({"approach": "  ", "unmet": []}) == ""
    long = solution_frame({"approach": "x " * 400, "next_milestone": "next"}, chars=300)
    assert len(long) <= 300 and long.startswith("Approach: ")
