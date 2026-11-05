"""Rebuild cases.json for Prioritization: invented, neutral cases that each exercise one generic ordering rule of the hub's arm. A consumer's own ordering rules
(its data model, its autopilot's instructions) are not here: the consumer adds an arm that competes under this metric, with cases built on it from its own
code and tests. The expected order is written by hand from the rule, never produced by an arm.

Families (the ``kind`` of a case, reported separately):
  rank      the person's own rank: ranked first ascending (0 is highest), unranked after in the order given, and before the deadline.
  carried   fields the data carries: nearest deadline first (undated last), oldest ask first, more people waiting first, longest since a nudge first, a blocked
            item after the unblocked.
  stated    what the person said: the order of kinds, an explicit order with a deferral, feedback that implies sooner or later, a not-before time, only some kinds.

    python3 evaluation/prioritization/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOW = "2026-07-12T09:00:00Z"


def case(name, family, rule, candidates, expect, stated=None, person=""):
    args = {"person": person, "candidates": candidates, "now": NOW}
    if stated is not None:
        args["stated"] = stated
    return {"id": "prioritize-" + name, "kind": family, "origin": "rule: " + rule, "args": args, "expect": expect}


def item(ident, kind="task", **fields):
    return dict({"id": ident, "kind": kind}, **fields)


def main():
    cases = []
    cases.append(case("rank-ascending-unranked-after", "rank", "ranked items first by ascending rank, unranked after in the order given",
                      [item("u1"), item("r2", rank=2), item("r0", rank=0), item("u2")], ["r0", "r2", "u1", "u2"]))
    cases.append(case("rank-many", "rank", "ascending rank over a long list", [item(f"t{i}", rank=i) for i in range(11, -1, -1)], [f"t{i}" for i in range(12)]))
    cases.append(case("rank-before-deadline", "rank", "a ranked item comes before an unranked one that is due sooner",
                      [item("due-soon", deadline="2026-07-13T00:00:00Z"), item("ranked", rank=5, deadline="2026-08-01T00:00:00Z")], ["ranked", "due-soon"]))
    cases.append(case("deadline-nearest-first", "carried", "the nearest deadline first",
                      [item(f"d{i}", deadline=f"2026-07-{i:02d}T00:00:00Z") for i in range(20, 13, -1)], [f"d{i}" for i in range(14, 21)]))
    cases.append(case("deadline-undated-last-in-given-order", "carried", "undated items after the dated, in the order given",
                      [item("n1"), item("late", deadline="2026-07-30T00:00:00Z"), item("n2"), item("soon", deadline="2026-07-14T00:00:00Z")], ["soon", "late", "n1", "n2"]))
    cases.append(case("ask-oldest-first", "carried", "the earlier ask first",
                      [item("new", "ask", asked_at="2026-07-10T09:00:00Z"), item("old", "ask", asked_at="2026-07-01T12:00:00Z")], ["old", "new"]))
    cases.append(case("more-people-waiting-first", "carried", "the item more people wait on first",
                      [item("one", waiting=["a"]), item("three", waiting=["a", "b", "c"]), item("none")], ["three", "one", "none"]))
    cases.append(case("longest-since-nudge-first", "carried", "never nudged first, then the longest since a nudge",
                      [item("recent", last_nudged_at="2026-07-11T00:00:00Z"), item("old", last_nudged_at="2026-07-01T00:00:00Z"), item("never")], ["never", "old", "recent"]))
    cases.append(case("blocked-after-unblocked", "carried", "an item that waits for a present item comes after the unblocked",
                      [item("b", blocked_by=["a"]), item("a"), item("c")], ["a", "c", "b"]))
    cases.append(case("person-orders-kinds", "stated", "kinds come in the order the person gave",
                      [item("n1", "note"), item("t1"), item("a1", "ask")], ["a1", "n1", "t1"], stated={"kind_order": ["ask", "note"]}))
    cases.append(case("person-order-then-deferral", "stated", "the person's order first, what they deferred last",
                      [item("x"), item("y"), item("z"), item("w")], ["z", "y", "w", "x"], stated={"order": ["z"], "deferred": ["x"]}))
    cases.append(case("feedback-sooner-moves-an-item", "stated", "feedback that implies sooner moves the item up",
                      [item("a"), item("b"), item("c")], ["c", "a", "b"], stated={"feedback": [{"about": "c", "direction": "sooner"}]}))
    cases.append(case("feedback-later-moves-a-kind", "stated", "feedback that implies later moves the whole kind down",
                      [item("t1"), item("n1", "note"), item("t2")], ["n1", "t1", "t2"], stated={"feedback": [{"about": "task", "direction": "later"}]}))
    cases.append(case("not-before-holds-an-item-back", "stated", "an item the person said not before a later time is held back",
                      [item("a"), item("b")], ["a"], stated={"not_before": {"b": "2026-08-01T00:00:00Z"}}))
    cases.append(case("only-kinds-holds-the-rest-back", "stated", "only the kinds the person limited the work to are ordered",
                      [item("a1", "ask"), item("n1", "note")], ["a1"], stated={"only_kinds": ["ask"]}))
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
