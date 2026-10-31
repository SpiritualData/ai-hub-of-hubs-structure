"""Staged plans: nesting is normalized, capped and split into stages, and ``run_when`` reads the step before."""
from typing import Any, Dict, Optional

from hubofhubs.orchestrate.staged_plan import (
    count_tasks, is_staged, normalize_staged_subtasks, sequence_stages, split_plan, step_allows, tasks_flat, tasks_in,
)
from hubofhubs.ports.deep import DeepResult


def task(name: str, run_when: Optional[str] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {"goal": name, "brief": f"do {name}"}
    if run_when:
        out["run_when"] = run_when
    return out


def normalize(raw, **caps):
    return normalize_staged_subtasks(raw, **{"max_items": 4, "max_stages": 4, "max_tasks": 8, **caps})


def test_a_flat_list_is_cleaned_and_every_task_runs_always():
    got = normalize([task("A"), task("B"), {"goal": "", "brief": ""}, "junk"])
    assert [(t["goal"], t["brief"], t["run_when"]) for t in got] == [("A", "do A", "always"), ("B", "do B", "always")]


def test_a_flat_list_keeps_its_cap():
    assert len(normalize([task(f"T{i}") for i in range(7)])) == 4


def test_a_nested_list_is_a_sequence_and_keeps_its_condition():
    got = normalize([[task("A"), task("B", "prev_not_met")]])
    assert len(got) == 1 and [t["goal"] for t in got[0]] == ["A", "B"]
    assert got[0][1]["run_when"] == "prev_not_met"


def test_an_unknown_run_when_is_always_and_steps_of_tasks_are_kept():
    got = normalize([[task("A"), [task("B1", "sometimes"), task("B2")], task("C")]])
    assert [[t["run_when"] for t in step] if isinstance(step, list) else step["run_when"] for step in got[0]] == [
        "always", ["always", "always"], "always"]


def test_the_caps_on_steps_and_on_tasks_hold():
    assert len(normalize([[task(f"S{i}") for i in range(9)]])[0]) == 4
    many = [[task(f"a{i}") for i in range(4)], [task(f"b{i}") for i in range(4)], task("c"), task("d")]
    assert count_tasks(normalize(many)) == 8


def test_a_single_step_sequence_is_just_the_task():
    assert normalize([[task("A")]]) == [{"goal": "A", "brief": "do A", "run_when": "always"}]


def test_a_sequence_becomes_ordered_stages_and_flat_tasks_stand_alone():
    subtasks = normalize([task("X"), [task("A"), [task("B1"), task("B2", "prev_met")], task("C", "prev_not_met")]])
    flat, plans = split_plan(subtasks)
    assert [t["goal"] for t in flat] == ["X"]
    assert [[t["goal"] for t in stage] for stage in plans[0]] == [["A"], ["B1", "B2"], ["C"]]
    assert is_staged(subtasks)
    assert not is_staged([task("A"), task("B")])
    assert is_staged([task("A", "prev_met")])


def test_independent_sequences_are_separate_plans_and_never_share_a_stage():
    subtasks = normalize([[task("A1"), task("A2", "prev_met")], [task("B1"), task("B2", "prev_not_met"), task("B3")]])
    flat, plans = split_plan(subtasks)
    assert flat == []
    assert [[[t["goal"] for t in stage] for stage in plan] for plan in plans] == [[["A1"], ["A2"]], [["B1"], ["B2"], ["B3"]]]


def test_nothing_comes_before_the_first_step_or_a_top_level_task_so_their_run_when_is_always():
    got = normalize([task("X", "prev_met"), [task("A", "prev_not_met"), task("B", "prev_met")]])
    assert got[0]["run_when"] == "always" and got[1][0]["run_when"] == "always" and got[1][1]["run_when"] == "prev_met"


def test_tasks_flat_reaches_every_task_of_a_nested_plan():
    subtasks = normalize([task("X"), [task("A"), [task("B1"), task("B2")]]])
    assert [t["goal"] for t in tasks_flat(subtasks)] == ["X", "A", "B1", "B2"]
    assert tasks_in("not a plan") == [] and sequence_stages([]) == []


def test_step_allows_reads_the_step_before():
    met, unmet = [DeepResult(met=True)], [DeepResult(met=False)]
    assert step_allows("prev_met", met) and not step_allows("prev_met", unmet)
    assert step_allows("prev_not_met", unmet) and not step_allows("prev_not_met", met)
    assert step_allows("always", unmet) and step_allows("prev_met", None) and step_allows(None, met)
    assert not step_allows("prev_met", [])
