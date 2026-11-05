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


def case(name, family, rule, candidates, expect, stated=None, person="", subject="", batch_limit=0):
    args = {"person": person, "candidates": candidates, "now": NOW}
    if subject:
        args["subject"] = subject
    if batch_limit:
        args["batch_limit"] = batch_limit
    if stated is not None:
        args["stated"] = stated
    return {"id": "prioritize-" + name, "kind": family, "origin": "rule: " + rule, "args": args, "expect": expect}


def item(ident, kind="task", **fields):
    return dict({"id": ident, "kind": kind}, **fields)


def ask(ident, **fields):
    return item(ident, "ask", **fields)


def milestone(ident, solution, intent="i-1", **fields):
    return item(ident, "milestone", solution=solution, intent=intent, **fields)


def asks_cases():
    out = []
    def add(name, rule, candidates, expect, **kw):
        out.append(case("asks-" + name, "asks", rule, candidates, expect, subject="asks", **kw))
    add("unblocks-most-first", "the ask whose answer frees the most waiting items first, whatever order they arrived in",
        [ask("a", asked_at="2026-07-01T00:00:00Z"), ask("b", unblocks=["t1"]), ask("c", unblocks=["t1", "t2", "t3"])], ["c", "b", "a"])
    add("unblocks-counts-dependents", "items that list the ask in blocked_by count as freed by it",
        [ask("a"), ask("b"), item("t1", blocked_by=["b"]), item("t2", blocked_by=["b"])], ["b", "a", "t1", "t2"])
    add("deadline-breaks-an-unblock-tie", "with the same number freed, the earlier deadline first",
        [ask("late", unblocks=["t1"], deadline="2026-07-30T00:00:00Z"), ask("soon", unblocks=["t2"], deadline="2026-07-13T00:00:00Z")], ["soon", "late"])
    add("unblock-before-deadline", "what an ask frees counts before its deadline",
        [ask("due", deadline="2026-07-13T00:00:00Z"), ask("frees", unblocks=["t1", "t2"], deadline="2026-09-01T00:00:00Z")], ["frees", "due"])
    add("shorter-effort-first", "with the same freed and deadline, the ask that takes less to answer first",
        [ask("long", unblocks=["t1"], effort=30), ask("quick", unblocks=["t2"], effort=2)], ["quick", "long"])
    add("recently-asked-later", "an ask the person was asked about recently comes after one they were not",
        [ask("recent", last_nudged_at="2026-07-12T08:00:00Z"), ask("never"), ask("week", last_nudged_at="2026-07-05T00:00:00Z")], ["never", "week", "recent"])
    add("person-order-beats-unblocks", "what the person ordered comes before what another ask frees",
        [ask("frees", unblocks=["t1", "t2"]), ask("pinned")], ["pinned", "frees"], stated={"order": ["pinned"]})
    add("person-deferral-last", "an ask the person deferred comes last whatever it frees",
        [ask("frees", unblocks=["t1", "t2"]), ask("plain")], ["plain", "frees"], stated={"deferred": ["frees"]})
    add("batch-limit-keeps-the-first", "with a batch limit only that many are put in front of the person, the first of the order",
        [ask("a"), ask("b", unblocks=["t1"]), ask("c", unblocks=["t1", "t2"]), ask("d", unblocks=["t1", "t2", "t3"])], ["d", "c"], batch_limit=2)
    add("batch-limit-above-the-count", "a limit above the number of asks holds nothing back",
        [ask("a", unblocks=["t1"]), ask("b")], ["a", "b"], batch_limit=5)
    return out


def goals_cases():
    out = []
    def add(name, rule, candidates, expect, **kw):
        out.append(case("goals-" + name, "goals", rule, candidates, expect, subject="goals", **kw))
    add("unblocks-first", "the milestone another milestone depends on comes before the one that waits",
        [milestone("ship", "s-a", blocked_by=["build"]), milestone("build", "s-a")], ["build", "ship"])
    add("frees-more-first", "the milestone that unblocks more comes first",
        [milestone("one", "s-a", unblocks=["x"]), milestone("three", "s-b", unblocks=["x", "y", "z"])], ["three", "one"])
    add("target-time-first", "the earlier target time first",
        [milestone("late", "s-a", deadline="2026-09-01T00:00:00Z"), milestone("soon", "s-b", deadline="2026-07-20T00:00:00Z")], ["soon", "late"])
    add("met-held-back", "a met milestone is no longer a priority and is held back",
        [milestone("met", "s-a", met="2026-06-01T00:00:00Z"), milestone("open", "s-a")], ["open"])
    add("ended-held-back", "a milestone whose end condition has passed is held back",
        [milestone("ended", "s-a", ends_at="2026-07-01T00:00:00Z"), milestone("open", "s-b")], ["open"])
    add("no-metric-ordered-the-same", "a milestone with no metric value is ordered by the same fields as one with a metric",
        [milestone("measured", "s-a", metric=0.8, deadline="2026-08-15T00:00:00Z"), milestone("unmeasured", "s-b", deadline="2026-07-20T00:00:00Z")], ["unmeasured", "measured"])
    add("person-orders-a-solution", "what the person ordered about a solution puts its milestones first",
        [milestone("a1", "s-a", deadline="2026-07-15T00:00:00Z"), milestone("b1", "s-b")], ["b1", "a1"], stated={"order": ["s-b"]})
    add("feedback-later-on-an-intent", "feedback that implies later about an intent moves its milestones down",
        [milestone("a1", "s-a", "i-1"), milestone("b1", "s-b", "i-2"), milestone("a2", "s-c", "i-1")], ["b1", "a1", "a2"], stated={"feedback": [{"about": "i-1", "direction": "later"}]})
    add("person-rank", "the person's own rank of a milestone comes before its target time",
        [milestone("due", "s-a", deadline="2026-07-13T00:00:00Z"), milestone("ranked", "s-b", rank=0, deadline="2026-12-01T00:00:00Z")], ["ranked", "due"])
    return out


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
    cases += asks_cases() + goals_cases()
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
