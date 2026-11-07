"""Rebuild cases.json for the pursue step of Critical Thinking: scripted pursuits of an unmet goal with a stub check and a stub attempt, so no model is called.

    python3 evaluation/goal_pursuit/build_cases.py

A case holds the goal's draft, the verdict of each outcome the stub check will see (``verdicts``: outcome text to met), the read and write ``means`` with
their estimated seconds, the ``budget``, and the ``attempts`` the stub returns in order (``outcome``, ``means_used``, ``writes``). ``expect`` is the summary
the scorer reports: status, met, replans, tried, how many interim lines were announced, how many attempts ran, how many write means were offered to an
attempt, whether a plain message came back, the outcome to send and the ignored writes. Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEARCH = {"name": "search", "kind": "read", "cost_seconds": 5}
LOOKUP = {"name": "lookup", "kind": "read", "cost_seconds": 5}
POST = {"name": "post", "kind": "write", "cost_seconds": 5}
DRAFT = "I do not have it, could you paste it?"
QUESTION = "Which quest or topic do you want to talk about?"      # a reply that is the one question a cut-off or ambiguous message needs
GOOD = "Here is the next step, from the transcript."
PARTIAL = "Found part of it."
BUDGET = {"max_replans": 2, "wall_seconds": 120, "inline_seconds": 30, "background": False}


def case(name, kind, verdicts, means, attempts, budget=None, expect=None, attempt_given=True, elapsed_start=0, draft=DRAFT):
    args = {"goal": "an actionable next step, grounded in the transcript", "done_standard": "a next step that cites the transcript", "draft": draft, "verdicts": verdicts,
            "means": means, "attempts": attempts, "budget": dict(BUDGET, **(budget or {})), "attempt_given": attempt_given, "elapsed_start": elapsed_start}
    summary = {"status": "", "met": False, "replans": 0, "tried": [], "interims": 0, "attempts": 0, "writes_offered": 0, "message": False, "outcome": draft, "ignored_writes": 0}
    return {"id": "pursuit-" + name, "kind": kind, "args": args, "expect": dict(summary, **expect)}


def main():
    unmet = {DRAFT: False}
    cases = [
        case("met-first-pass", "first_pass", {DRAFT: True}, [SEARCH], [], expect={"status": "met", "met": True}),
        case("met-after-one-replan", "replan", dict(unmet, **{GOOD: True}), [SEARCH], [{"outcome": GOOD, "means_used": ["search"]}],
             expect={"status": "met_after_replan", "met": True, "replans": 1, "tried": ["search"], "attempts": 1, "outcome": GOOD}),
        case("met-after-two-replans", "replan", dict(unmet, **{PARTIAL: False, GOOD: True}), [SEARCH, LOOKUP],
             [{"outcome": PARTIAL, "means_used": ["search"]}, {"outcome": GOOD, "means_used": ["lookup"]}],
             expect={"status": "met_after_replan", "met": True, "replans": 2, "tried": ["search", "lookup"], "attempts": 2, "outcome": GOOD}),
        case("unrecoverable-no-means", "unrecoverable", unmet, [], [], expect={"status": "unmet_reported", "message": True}),
        case("unrecoverable-after-trying", "unrecoverable", dict(unmet, **{PARTIAL: False}), [SEARCH], [{"outcome": PARTIAL, "means_used": ["search"]}],
             expect={"status": "unmet_reported", "replans": 1, "tried": ["search"], "attempts": 1, "message": True, "outcome": PARTIAL}),
        case("no-attempt-to-run", "unrecoverable", unmet, [SEARCH], [], attempt_given=False, expect={"status": "unmet_reported", "message": True}),
        case("empty-outcome-keeps-the-draft", "unrecoverable", unmet, [SEARCH], [{"outcome": "", "means_used": ["search"]}],
             expect={"status": "unmet_reported", "replans": 1, "tried": ["search"], "attempts": 1, "message": True}),
        case("write-never-offered", "write", dict(unmet, **{GOOD: True}), [SEARCH, POST], [{"outcome": GOOD, "means_used": ["search"]}],
             expect={"status": "met_after_replan", "met": True, "replans": 1, "tried": ["search"], "attempts": 1, "outcome": GOOD}),
        case("write-reported-is-discarded", "write", dict(unmet, **{GOOD: True}), [SEARCH], [{"outcome": GOOD, "means_used": ["search"], "writes": ["post"]}],
             expect={"status": "unmet_reported", "replans": 1, "attempts": 1, "message": True, "ignored_writes": 1}),
        case("replan-cap-respected", "cap", dict(unmet, **{PARTIAL: False}), [SEARCH, LOOKUP], [{"outcome": PARTIAL, "means_used": ["search"]}, {"outcome": PARTIAL, "means_used": ["lookup"]}],
             budget={"max_replans": 1}, expect={"status": "unmet_reported", "replans": 1, "tried": ["search"], "attempts": 1, "message": True, "outcome": PARTIAL}),
        case("wall-cap-respected", "cap", dict(unmet, **{GOOD: True}), [SEARCH], [{"outcome": GOOD, "means_used": ["search"]}],
             budget={"wall_seconds": 100}, elapsed_start=98, expect={"status": "unmet_reported", "message": True}),
        case("long-work-announces-once-and-runs", "interim", dict(unmet, **{GOOD: True}), [dict(SEARCH, cost_seconds=40)], [{"outcome": GOOD, "means_used": ["search"]}],
             expect={"status": "met_after_replan", "met": True, "replans": 1, "tried": ["search"], "interims": 1, "attempts": 1, "outcome": GOOD}),
        case("long-work-hands-on-to-the-background", "interim", unmet, [dict(SEARCH, cost_seconds=40)], [], budget={"background": True},
             expect={"status": "continuing", "interims": 1, "message": True}),
        case("two-long-rounds-announce-once", "interim", dict(unmet, **{PARTIAL: False, GOOD: True}), [dict(SEARCH, cost_seconds=40), dict(LOOKUP, cost_seconds=40)],
             [{"outcome": PARTIAL, "means_used": ["search"]}, {"outcome": GOOD, "means_used": ["lookup"]}], budget={"wall_seconds": 400},
             expect={"status": "met_after_replan", "met": True, "replans": 2, "tried": ["search", "lookup"], "interims": 1, "attempts": 2, "outcome": GOOD}),
        case("cut-off-message-question-is-terminal", "awaiting_person", {QUESTION: "awaiting"}, [dict(SEARCH, cost_seconds=40)], [], budget={"background": True},
             draft=QUESTION, expect={"status": "awaiting_person", "met": True, "outcome": QUESTION}),
        case("ambiguous-request-one-question-is-terminal", "awaiting_person", {QUESTION: "awaiting"}, [SEARCH], [{"outcome": GOOD, "means_used": ["search"]}],
             draft=QUESTION, expect={"status": "awaiting_person", "met": True, "outcome": QUESTION}),
        case("real-unmet-goal-still-pursues", "awaiting_person", dict(unmet, **{GOOD: True}), [SEARCH], [{"outcome": GOOD, "means_used": ["search"]}],
             expect={"status": "met_after_replan", "met": True, "replans": 1, "tried": ["search"], "attempts": 1, "outcome": GOOD}),
        case("short-work-does-not-announce", "interim", dict(unmet, **{GOOD: True}), [SEARCH], [{"outcome": GOOD, "means_used": ["search"]}],
             expect={"status": "met_after_replan", "met": True, "replans": 1, "tried": ["search"], "attempts": 1, "outcome": GOOD}),
    ]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
