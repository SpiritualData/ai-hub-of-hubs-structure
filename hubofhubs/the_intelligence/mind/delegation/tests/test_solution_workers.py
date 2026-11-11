"""Solution workers: the tree follows the solution hierarchy, children report up first, each brief holds only its own frame, and the limits report what they cut."""
import threading
import time

from hubofhubs.the_intelligence.mind.delegation.solution_workers import SolutionReport, delegates_of, records_frame, work_solution

TREE = {"root": ["a", "b"], "a": ["a1"], "b": [], "a1": []}


def frame(sid):
    return {"name": sid.upper(), "approach": f"approach of {sid}", "milestone": f"milestone of {sid}"}


def kids(sid, task):
    return TREE.get(sid, [])


def met(sid, milestone, output):
    return {"met": True, "missing": ""}


def make_work(log=None, lock=threading.Lock()):
    def work(brief):
        with lock:
            (log if log is not None else []).append(brief)
        return f"out of {brief['solution_id']}"
    return work


def run(**kw):
    args = dict(frame=frame, children=kids, work=make_work(), check=met, task="the task")
    args.update(kw)
    return work_solution("root", **args)


def shape(report):
    return {report.solution: [shape(c) for c in report.children]}


def test_the_tree_shape_equals_the_solution_hierarchy():
    report = run(budget={"depth": 3})
    assert shape(report) == {"root": [{"a": [{"a1": []}]}, {"b": []}]}
    assert report.status == "met" and report.total_calls() == 4
    assert report.tree_text().splitlines()[0].startswith("- ROOT (root): met") and "    - A1 (a1): met" in report.tree_text()


def test_children_run_before_the_parent_and_the_parent_brief_holds_their_compact_reports():
    order, briefs = [], []

    def work(brief):
        order.append(brief["solution_id"])
        briefs.append(brief)
        return f"out of {brief['solution_id']}"
    report = run(work=work)
    assert order[-1] == "root" and order.index("a1") < order.index("a") and set(order) == {"a", "a1", "b", "root"}
    root = briefs[-1]
    assert [r.splitlines()[0] for r in root["reports"]] == ["A (a): met", "B (b): met"]
    assert root["reports"][0] == report.children[0].compact() and "Output: out of a" in root["reports"][0]
    assert root["milestone"] == "milestone of root" and root["task"] == "the task"


def test_a_child_brief_holds_neither_the_parent_frame_nor_a_sibling_output():
    briefs = {}

    def work(brief):
        briefs[brief["solution_id"]] = brief
        return f"SECRET-{brief['solution_id']}"
    run(work=work)
    for sid in ("a", "b"):
        text = repr(briefs[sid])
        assert "approach of root" not in text and "milestone of root" in briefs[sid]["handed"]      # only the one line the parent hands down
        assert briefs[sid]["reports"] == [] or sid == "a"
    assert "SECRET-b" not in repr(briefs["a"]) and "SECRET-a" not in repr(briefs["b"])
    assert briefs["a"]["handed"] == "ROOT needs from A, for: the task, toward: milestone of root"
    assert "approach of a" in briefs["a"]["frame"] and set(briefs["b"]) == {"solution_id", "name", "frame", "milestone", "task", "handed", "reports"}


def test_an_unmet_part_is_worked_again_once_with_what_is_missing_then_met():
    briefs = []

    def check(sid, milestone, output):
        return {"met": len(briefs) >= 2, "missing": "a source"}
    report = run(children=lambda s, t: [], work=make_work(briefs), check=check)
    assert report.status == "met" and report.calls == 2
    assert "missing" not in briefs[0] and briefs[1]["missing"] == "a source" and briefs[1]["round"] == 2


def test_the_rework_stops_at_rounds_and_a_lower_score_is_not_kept():
    scores = iter([0.6, 0.2])
    outputs = iter(["better", "worse"])
    report = run(children=lambda s, t: [], work=lambda b: next(outputs), check=lambda s, m, o: {"met": False, "missing": "x", "score": next(scores)})
    assert report.status == "unmet" and report.output == "better" and report.calls == 2 and report.missing == "x"


def test_calls_running_out_reports_not_started_with_the_reason():
    report = run(budget={"calls": 2, "depth": 3, "width": 1})
    states = {c.solution: c.status for c in report.children}
    assert report.total_calls() == 2 and report.status == "not_started" and "call budget" in report.missing
    assert "not_started" in states.values() and all(c.met is None for c in report.children if c.status == "not_started")
    assert "call budget" in report.tree_text()


def test_the_depth_limit_reports_the_levels_below_it_as_not_started():
    report = run(budget={"depth": 1})
    a = report.children[0]
    assert a.status == "met" and a.children[0].status == "not_started" and "depth limit" in a.children[0].missing


def test_a_cycle_does_not_recurse_forever():
    graph = {"x": ["y"], "y": ["x"]}
    report = work_solution("x", frame=frame, children=lambda s, t: graph[s], work=make_work(), check=met, budget={"depth": 9})
    assert report.children[0].children[0].status == "not_started" and "cycle" in report.children[0].children[0].missing
    assert report.total_calls() == 2


def test_a_child_already_met_spends_no_call():
    briefs = []
    report = run(work=make_work(briefs), already_met=lambda cid: cid == "b")
    b = report.children[1]
    assert b.status == "already_met" and b.met is True and b.calls == 0 and "b" not in [x["solution_id"] for x in briefs]
    assert "B (b): already_met" in briefs[-1]["reports"][1]


def test_an_exception_in_one_child_does_not_stop_the_others_or_the_parent():
    def work(brief):
        if brief["solution_id"] == "a":
            raise RuntimeError("boom")
        return "ok"
    report = run(work=work)
    a, b = report.children
    assert a.status == "unmet" and "RuntimeError: boom" in a.missing and b.status == "met" and report.status == "met"
    broken = run(check=lambda s, m, o: (_ for _ in ()).throw(ValueError("bad check")) if s == "b" else {"met": True})
    assert broken.children[1].status == "unmet" and "bad check" in broken.children[1].missing and broken.status == "met"


def test_children_run_in_parallel_up_to_width():
    barrier = threading.Barrier(3, timeout=5)

    def work(brief):
        if brief["solution_id"] != "root":
            barrier.wait()      # all three children must be running at once
        return "ok"
    report = run(children=lambda s, t: ["a", "b", "b2"] if s == "root" else [], work=work, budget={"width": 3})
    assert [c.status for c in report.children] == ["met"] * 3 and report.status == "met"


def test_cancel_stops_new_work_and_says_so():
    report = run(cancel=lambda: True)
    assert report.status == "cancelled" and report.met is None and report.total_calls() == 0


def test_compact_clips_the_output():
    r = SolutionReport(solution="s", name="S", milestone="m", status="unmet", output="word " * 500, missing="more")
    text = r.compact(chars=50)
    assert "Output: " in text and text.count("word") <= 11 and text.endswith("Missing: more") and "..." in text


def test_records_frame_and_delegates_of_read_the_hub_records():
    from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import SolutionNetwork
    net = SolutionNetwork.from_rows({"solutions": [
        {"solution_id": "p", "name": "P", "approach": "Do p.", "milestones": "1. one [met]\n2. two", "delegates_to": "q;none;ghost"},
        {"solution_id": "q", "name": "Q", "purpose": "Does q.", "milestones": "1. only [met]"}]})
    assert delegates_of(net)("p", "t") == ["q"]
    assert records_frame(net)("p") == {"name": "P", "approach": "Do p.", "milestone": "two"}
    assert records_frame(net)("q")["milestone"] == "" and records_frame(net)("q")["approach"] == "Does q."


def test_a_workers_frame_holds_the_next_milestone_the_records_frame_names():
    briefs = []
    run(work=make_work(briefs))
    assert all(f"Next unmet milestone: milestone of {b['solution_id']}" in b["frame"] for b in briefs)
