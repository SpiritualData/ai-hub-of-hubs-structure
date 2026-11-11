"""Structure Watch: the scripted cases of the metric, the default timing and the route of each item through Judgment Calls."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation"))
sys.path.insert(0, str(ROOT / "evaluation" / "structure_watch"))
import score  # noqa: E402
from hubofhubs.api import structure_watch_due  # noqa: E402
from hubofhubs.the_consciousness.judgment_calls.judgment import SeverityPolicy  # noqa: E402
from hubofhubs.the_intelligence.nervous_system.structure_watch.watch import BestTierCall, FindingsOnly, OUTPUT_TOKENS  # noqa: E402

CASES = json.loads((ROOT / "evaluation" / "structure_watch" / "cases.json").read_text(encoding="utf-8"))


def test_every_scripted_case_passes_for_the_call():
    run = score.adapt(BestTierCall, None)
    failed = [c["id"] for c in CASES if not score.score_case(run, c)["ok"]]
    assert failed == []


def test_the_findings_only_baseline_never_calls_a_model():
    calls = []
    arm = FindingsOnly(ask=lambda *a: calls.append(a))
    got = arm.watch({"intent": "x", "tables": {"solutions": [{"solution_id": "s", "name": "s", "purpose": "p", "authoritative_metric_id": "", "metric_ids": ""}], "implementations": []}, "now": "2026-11-10T09:00:00Z"})
    assert calls == [] and got["called"] is False and got["items"][0]["subject"] == "solutions:s"


def test_judgment_calls_asks_for_a_persons_structure_and_proceeds_for_the_ais():
    judge = SeverityPolicy().decide
    assert judge({"severity": "low", "reason": "r"}, "", {"needs_person": True})["decision"] == "ask"
    assert judge({"severity": "high", "reason": "r"}, "", {"ai_owned": True})["decision"] == "proceed"


def test_default_timing_end_of_run_and_session_start():
    now = "2026-11-10T09:00:00Z"
    assert structure_watch_due("end_of_run", now, "2026-11-10T08:00:00Z", now)["due"] is True
    assert structure_watch_due("end_of_run", now, "2026-11-10T08:00:00Z", "")["due"] is False          # nothing changed
    assert structure_watch_due("session_start", now, "2026-11-10T08:00:00Z", now)["due"] is False       # last watch under a day old
    assert structure_watch_due("session_start", now, "2026-11-08T08:00:00Z", now)["due"] is True
    assert structure_watch_due("end_of_run", now, "", now, off=True)["due"] is False


def test_the_output_cap_is_a_few_hundred_tokens():
    assert OUTPUT_TOKENS <= 500


def _large_structure(plant: bool):
    """A structure of many solutions with a recent run; with ``plant`` one solution the run touched has a metric whose last result is older than the run, and one has three implementations and no metric."""
    solutions = [{"solution_id": f"s{n}", "name": f"s{n}", "purpose": f"serve the job number {n} alone", "authoritative_metric_id": "m", "metric_ids": "m", "selected": "a"} for n in range(150)]
    impls = [{"implementation_id": f"s{n}:a", "solution_id": solutions[n]["solution_id"], "filepath": f"code/s{n}.py"} for n in range(150)]
    results = [{"date": "2026-10-01", "component": f"s{n}"} for n in range(150)]
    if plant:
        solutions[7].update(authoritative_metric_id="", metric_ids="", selected="")
        impls += [{"implementation_id": f"s7:{k}", "solution_id": "s7", "filepath": "code/s7.py"} for k in range(3)]
        results = [r for r in results if r["component"] != "s7"]
    runs = [{"at": "2026-11-09T10:00:00Z", "summary": "reworked s42 and s7", "solutions": ["s42", "s7"]}]
    return {"intent": "example", "tables": {"solutions": solutions, "implementations": impls, "metrics": [], "experiments": [], "investigations": [], "milestones": []},
            "results": results, "runs": runs, "now": "2026-11-10T09:00:00Z"}


def test_a_planted_problem_in_a_large_structure_is_in_the_digest_and_comes_back_as_an_item():
    """A scripted model that only reads the digest: it raises the first finding line it is shown. The planted problems (a solution with no metric that recent work touches, and a touched solution whose
    metric last ran before the work) must be in the digest, within the input cap, and so come back."""
    seen = []

    def reads_the_digest(prompt, tier, cap):
        seen.append(prompt)
        lines = prompt.split("FINDINGS BY RULE (subject | severity | step | detail):")[1].strip().splitlines()
        subject, _, rest = lines[0].lstrip(" -").partition(" | ")
        severity, _, rest = rest.partition(" | ")
        step = rest.partition(" | ")[0]
        return json.dumps({"items": [{"subject": subject, "what": "needs attention", "why_now": "recent work", "risk": "more is built on it", "severity": severity, "step": step, "step_text": step}]})
    got = BestTierCall(ask=reads_the_digest).watch(_large_structure(True), "2026-11-10T09:00:00Z")
    assert got["called"] and [i["subject"] for i in got["items"]] == ["solutions:s7"] and got["items"][0]["step"] == "add-metric"
    assert len(seen[0]) <= 3000 * 4 and "RECORDS: 150 solutions" in seen[0] and "reworked s42 and s7" in seen[0]
    clean = BestTierCall(ask=lambda p, t, c: json.dumps({"items": []})).watch(_large_structure(False), "2026-11-10T09:00:00Z")
    assert clean["called"] and clean["items"] == []


def test_recent_work_after_the_last_result_is_a_finding_and_recently_touched_ranks_first():
    s = _large_structure(False)
    s["results"] = [r for r in s["results"] if r["component"] != "s42"] + [{"date": "2026-10-01", "component": "s42"}]
    s["runs"] = [{"at": "2026-11-09T10:00:00Z", "summary": "reworked s42", "solutions": ["s42"]}]
    kinds = {(f["kind"], f["subject"]) for f in __import__("hubofhubs.the_intelligence.nervous_system.structure_watch.digest", fromlist=["x"]).findings_of(s, [])}
    assert ("result_older_than_recent_work", "solutions:s42") in kinds


def test_a_result_belongs_to_the_solution_whose_metric_runs_its_component():
    from hubofhubs.the_intelligence.nervous_system.structure_watch.digest import last_results
    s = {"tables": {"metrics": [{"metric_id": "m", "command": "esoi run agent_sessions --impl none", "solution_ids": "delegated-agent-sessions"}]}, "results": [{"date": "2026-11-10", "component": "agent_sessions"}]}
    assert last_results(s) == {"delegated-agent-sessions": "2026-11-10", "agent-sessions": "2026-11-10"}


def test_the_stored_review_mark_decides_applied_with_undo_or_proposal():
    """A record marked ``ai`` (its ``reviewed_by`` column) that no person reviewed is changed by the AI and recorded with an undo; a person-marked or unmarked record stays a proposal."""
    def solution(sid, mark):
        return {"solution_id": sid, "name": sid, "purpose": "p", "authoritative_metric_id": "", "metric_ids": "", "selected": "", "reviewed_by": mark}
    structure = {"intent": "x", "tables": {"solutions": [solution("a", "ai"), solution("b", "person"), solution("c", "")], "implementations": [], "metrics": []}, "now": "2026-11-10T09:00:00Z"}
    edit = lambda sid: {"kind": "spec_edit", "target": sid, "field": "purpose", "value": "new text"}
    reply = json.dumps({"items": [{"subject": f"solutions:{sid}", "what": "no metric", "why_now": "work", "risk": "r", "severity": "high", "step": "add-metric", "step_text": "t", "edit": edit(sid)} for sid in "abc"]})
    applied = []

    def applier(change):
        applied.append(change["edit"]["target"])
        return {"applied": True, "before": "p", "after": "new text"}
    got = BestTierCall(ask=lambda *a: reply, judge=SeverityPolicy().decide, applier=applier).watch(structure, "2026-11-10T09:00:00Z")
    routes = {i["subject"]: i["route"] for i in got["items"]}
    assert routes == {"solutions:a": "applied", "solutions:b": "proposal", "solutions:c": "proposal"} and applied == ["a"]
    change = next(i for i in got["items"] if i["subject"] == "solutions:a")["change"]
    assert change["before"] == "p" and change["after"] == "new text" and change["undo"]["value"] == "p"
