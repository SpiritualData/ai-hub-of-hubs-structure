"""Rebuild cases.json for Structure Watch: scripted structures with a planted problem, clean structures where it must stay silent, and the rules around the call (an unchanged digest
makes no call, a repeated item is not raised again unless worse, the caps hold, the route of each item). No model call, no network: the model's reply is a fixed text in the case.

    python3 evaluation/structure_watch/build_cases.py

A case has ``steps``: structures watched in order against one store, each with its ``model`` reply; ``review`` marks records the AI made (``ai``); ``expect`` is what the last step must show:
``ran`` (the watch made its decision rather than skipping), ``subjects`` (raised, sorted), ``routes`` (subject to proposal or applied), ``caps`` (at most three items, tokens within the caps), and
for an applied item its ``before`` and ``after``. Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOW = "2026-11-10T09:00:00Z"


def sol(sid, name="", purpose="", metric="metric-" + "ok", selected="a", milestones="", delegates=""):
    return {"solution_id": sid, "name": name or sid, "purpose": purpose or f"serve the {sid} job alone", "authoritative_metric_id": metric, "metric_ids": metric, "selected": selected, "milestones": milestones, "delegates_to": delegates}


def impl(sid, n=1):
    return [{"implementation_id": f"{sid}:i{k}", "solution_id": sid, "filepath": f"code/{sid}_{k}.py"} for k in range(n)]


def structure(solutions, impls=(), **more):
    base = {"intent": "example", "tables": {"solutions": solutions, "implementations": list(impls), "experiments": [], "investigations": [], "metrics": []}, "results": [], "runs": [], "now": NOW}
    base.update(more)
    return base


def with_tables(s, **tables):
    s["tables"].update(tables)
    return s


def item(subject, step, severity="high", edit=None):
    out = {"subject": subject, "what": "needs attention", "why_now": "work is going on", "risk": "more is built on it", "severity": severity, "step": step, "step_text": step}
    if edit:
        out["edit"] = edit
    return out


def reply(*items):
    return json.dumps({"items": list(items)})


def case(name, steps, expect, review=None, records=None, ceilings=None, off=False):
    return {"id": "watch-" + name, "kind": "planted" if expect.get("subjects") else "rule", "origin": "rule: the structure watch", "args": {"steps": steps, "review": review or {}, "records": records, "ceilings": ceilings, "off": off}, "expect": expect}


def cases():
    base = [sol("s1"), sol("s2")]
    out = []
    exp = {"experiment_id": "e1", "status": "running", "reevaluate_time": "2026-11-01", "held_fixed": "s1 = a", "links": "solution:s1"}
    out.append(case("experiment-past-reevaluation-with-work-piling-on", [{"structure": with_tables(structure(base, impl("s1") + impl("s2"), runs=[{"at": NOW, "summary": "edited s1", "solutions": ["s1"]}]), experiments=[exp]),
                    "model": reply(item("experiments:e1", "reevaluate"))}], {"ran": True, "subjects": ["experiments:e1"], "routes": {"experiments:e1": "proposal"}, "caps": True}))
    out.append(case("three-implementations-no-metric", [{"structure": structure([sol("s1"), sol("s3", metric="", selected="")], impl("s1") + impl("s3", 3)), "model": reply(item("solutions:s3", "add-metric"))}],
                    {"ran": True, "subjects": ["solutions:s3"], "routes": {"solutions:s3": "proposal"}, "caps": True}))
    first = structure([sol("s1", "Weekly summary writer", "write a weekly summary of the team's work for the people who read it")], impl("s1"))
    second = structure([sol("s1", "Weekly summary writer", "write a weekly summary of the team's work for the people who read it"),
                        sol("s9", "Weekly summary writer two", "write a weekly summary of the team's work for the people who read it")], impl("s1") + impl("s9"))
    out.append(case("duplicate-solution-added-by-recent-work", [{"structure": first, "model": reply()}, {"structure": second, "model": reply(item("solutions:s9", "merge"))}],
                    {"ran": True, "subjects": ["solutions:s9"], "routes": {"solutions:s9": "proposal"}, "caps": True}))
    ms = [{"id": "m1", "solution": "s1", "text": "Ship the first version", "met": False, "target": "2026-10-01", "blocked_by": ""}, {"id": "m2", "solution": "s2", "text": "Build on the first version", "met": False, "target": "2026-12-01", "blocked_by": "m1"}]
    out.append(case("milestone-past-its-date-that-planned-work-depends-on", [{"structure": with_tables(structure(base, impl("s1") + impl("s2")), milestones=ms), "model": reply(item("milestones:m1", "restrategize"))}],
                    {"ran": True, "subjects": ["milestones:m1"], "routes": {"milestones:m1": "proposal"}, "caps": True}))
    inv = {"investigation_id": "i1", "status": "open", "refresh_on": "2026-10-30", "links": "solution:s2", "question": "which store"}
    ms2 = [{"id": "m3", "solution": "s2", "text": "Pick the store", "met": False, "target": "", "blocked_by": ""}]
    out.append(case("investigation-past-refresh-that-planned-work-relies-on", [{"structure": with_tables(structure(base, impl("s1") + impl("s2")), investigations=[inv], milestones=ms2), "model": reply(item("investigations:i1", "investigate", "medium"))}],
                    {"ran": True, "subjects": ["investigations:i1"], "routes": {"investigations:i1": "proposal"}, "caps": True}))
    clean = structure(base, impl("s1") + impl("s2"))
    out.append(case("clean-structure-first-watch", [{"structure": clean, "model": reply()}], {"ran": True, "subjects": [], "routes": {}, "caps": True}))
    out.append(case("clean-structure-after-small-edit", [{"structure": clean, "model": reply()}, {"structure": structure([sol("s1", purpose="serve the s1 job alone, now stated better"), sol("s2")], impl("s1") + impl("s2"),
                    runs=[{"at": NOW, "summary": "reworded s1", "solutions": ["s1"]}]), "model": reply()}], {"ran": True, "subjects": [], "routes": {}, "caps": True}))
    out.append(case("clean-structure-with-a-running-experiment-not-due", [{"structure": with_tables(structure(base, impl("s1") + impl("s2")), experiments=[dict(exp, reevaluate_time="2026-12-15")]), "model": reply()}],
                    {"ran": True, "subjects": [], "routes": {}, "caps": True}))
    out.append(case("unchanged-digest-makes-no-call", [{"structure": clean, "model": reply()}, {"structure": clean, "model": reply(item("solutions:s1", "other"))}], {"ran": False, "subjects": [], "routes": {}, "caps": True}))
    nometric = structure([sol("s1"), sol("s3", metric="", selected="")], impl("s1") + impl("s3", 3))
    nometric_edit = structure([sol("s1"), sol("s3", metric="", selected=""), sol("s2")], impl("s1") + impl("s3", 3) + impl("s2"))
    out.append(case("repeated-item-is-not-raised-again", [{"structure": nometric, "model": reply(item("solutions:s3", "add-metric"))}, {"structure": nometric_edit, "model": reply(item("solutions:s3", "add-metric"))}],
                    {"ran": True, "subjects": [], "routes": {}, "caps": True}))
    out.append(case("repeated-item-that-got-worse-is-raised-again", [{"structure": nometric, "model": reply(item("solutions:s3", "add-metric", "medium"))}, {"structure": nometric_edit, "model": reply(item("solutions:s3", "add-metric", "high"))}],
                    {"ran": True, "subjects": ["solutions:s3"], "routes": {"solutions:s3": "proposal"}, "caps": True}))
    many = structure([sol(f"x{n}", metric="", selected="") for n in range(300)], [r for n in range(300) for r in impl(f"x{n}", 3)])
    long = "word " * 900
    five = reply(*[dict(item(f"solutions:x{n}", "add-metric"), what=long, why_now=long, risk=long, step_text=long) for n in range(5)])
    out.append(case("caps-hold-and-a-reply-over-the-cap-falls-back-to-the-code-findings", [{"structure": many, "model": five}], {"ran": True, "subjects": ["solutions:x0", "solutions:x1", "solutions:x10"], "routes": {f"solutions:x{n}": "proposal" for n in (0, 1, 10)}, "caps": True}))
    edit = {"kind": "spec_edit", "target": "s3", "field": "authoritative_metric_id", "value": "metric-s3-first"}
    records = {"solutions": {"s3": {"authoritative_metric_id": ""}}}
    out.append(case("ai-made-unreviewed-structure-is-applied-and-recorded", [{"structure": nometric, "model": reply(item("solutions:s3", "add-metric", edit=edit))}],
                    {"ran": True, "subjects": ["solutions:s3"], "routes": {"solutions:s3": "applied"}, "caps": True, "before": "", "after": "metric-s3-first"}, review={"solutions:s3": "ai"}, records=records))
    out.append(case("person-reviewed-structure-goes-to-the-person-unchanged", [{"structure": nometric, "model": reply(item("solutions:s3", "add-metric", edit=edit))}],
                    {"ran": True, "subjects": ["solutions:s3"], "routes": {"solutions:s3": "proposal"}, "caps": True, "records_unchanged": True}, review={"solutions:s3": "person"}, records=records))
    held = with_tables(structure([sol("s1"), sol("s3", metric="", selected="")], impl("s1") + impl("s3", 3)), experiments=[dict(exp, reevaluate_time="2026-12-15", links="solution:s3", held_fixed="s3 = a")])
    out.append(case("what-a-running-experiment-holds-fixed-goes-to-the-person", [{"structure": held, "model": reply(item("solutions:s3", "add-metric", edit=edit))}],
                    {"ran": True, "subjects": ["solutions:s3"], "routes": {"solutions:s3": "proposal"}, "caps": True, "records_unchanged": True}, review={"solutions:s3": "ai"}, records=records))
    out.append(case("irreversible-step-goes-to-the-person-even-when-ai-made", [{"structure": second, "model": reply(item("solutions:s9", "merge"))}], {"ran": True, "subjects": ["solutions:s9"], "routes": {"solutions:s9": "proposal"}, "caps": True}, review={"solutions:s9": "ai"}))
    out.append(case("run-at-its-ceiling-makes-no-call", [{"structure": nometric, "model": reply(item("solutions:s3", "add-metric"))}], {"ran": False, "subjects": [], "routes": {}, "caps": True}, ceilings={"spent_usd": 9.0, "ceiling_usd": 10.0}))
    out.append(case("setting-off-makes-no-call", [{"structure": nometric, "model": reply(item("solutions:s3", "add-metric"))}], {"ran": False, "subjects": [], "routes": {}, "caps": True}, off=True))
    return out


if __name__ == "__main__":
    (HERE / "cases.json").write_text(json.dumps(cases(), indent=1, sort_keys=True), encoding="utf-8")
    print(len(cases()), "cases")
