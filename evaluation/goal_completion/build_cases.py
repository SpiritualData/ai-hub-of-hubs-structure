"""Rebuild cases.json for Goal Completion from the coverage cases the repository's own done-evidence tests assert (hubofhubs/the_intelligence/critical_thinking/goal_completion/tests/test_critique_done_evidence.py:
a known total above processed is a gap, an explicit complete flag wins, a capped read of unknown size is a gap, and anything undeclared or malformed
never blocks) and from the other ways an outcome can fail a done-standard: empty, refused, or missing a requirement the standard names.

    python3 evaluation/goal_completion/build_cases.py

A case of kind ``outcome`` is a goal, its done-standard and an outcome; ``expect`` is whether the goal is met. A case of kind ``stop`` is an iteration history
(``hubofhubs/the_intelligence/critical_thinking/goal_completion/stop_rule.py`` documents its fields) and ``expect`` is the right decision: ``continue``,
``stop_met``, ``stop_good_enough``, ``stop_not_worth_it`` or ``ask``. Each stop case is a neutral scripted scenario of one situation and carries a ``note`` that says
why that decision is right, written from the ESOI and Consciousness principles (iterate while the gain toward the next milestone is worth its cost; what the
person stated outranks the default; policy and authority bound it; what only a person can supply is asked, never iterated). Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOAL = "process every entry"
STANDARD = "every entry was processed"
TEXT = "Processed the entries."


def case(name, outcome, met, standard=STANDARD):
    return {"id": "goal-" + name, "kind": "outcome", "args": {"goal": GOAL, "done_standard": standard, "outcome": outcome}, "expect": met}


CEILING = {"spend_usd": 20.0, "seconds": 14400.0, "soft_fraction": 0.8}
UP = {"better": "higher", "target": 1.0}
DOWN = {"better": "lower", "target": 0.0}
GAP = {"processed": 200, "total": 344, "unit": "entries"}


def step(metric=None, verdict=False, changed=1, missing=None, spend=1.0, seconds=60.0, claimed=None, outcome=None):
    return {"verdict": verdict, "claimed_met": claimed, "outcome": outcome, "changed": changed, "metric": metric,
            "missing": list(missing) if missing is not None else [], "spend_usd": spend, "seconds": seconds}


def stop(name, expect, why, iterations, metric=UP, ceiling=CEILING, **rest):
    history = {"goal": GOAL, "done_standard": STANDARD, "iterations": iterations, "metric": metric, "ceiling": ceiling}
    history.update(rest)
    return {"id": "stop-" + name, "kind": "stop", "args": {"history": history}, "expect": expect, "note": why}


def track(values, **each):
    return [step(metric=v, **each) for v in values]


def stop_cases():
    c = "continue"
    return [
        # met early
        stop("met-first-iteration", "stop_met", "the check says met after one cheap iteration: nothing more to gain", [step(0.9, verdict=True)]),
        stop("met-after-progress", "stop_met", "progress each round and the last check says met", track([0.3, 0.6]) + [step(0.95, verdict=True)]),
        stop("met-below-metric-target", "stop_met", "the done-standard is met even though the metric is short of its ceiling value: the standard decides", track([0.4]) + [step(0.8, verdict=True)]),
        # real progress each round
        stop("progress-rising", c, "each round closed about a third of the rest for a small share of the budget", track([0.3, 0.55, 0.75])),
        stop("progress-falling-errors", c, "errors fall 12, 8, 4 for a small spend: worth another round", track([12, 8, 4]), metric={"better": "lower", "target": 0}),
        stop("progress-missing-shrinks", c, "what the check finds missing shrinks 4, 3, 2 and the work changes things", [step(missing=["a"] * n) for n in (4, 3, 2)], metric=None),
        # plateau
        stop("plateau-flat-metric", "stop_not_worth_it", "the last round moved the metric by 0.01 of a 0.4 gap: a plateau", track([0.6, 0.61, 0.61])),
        stop("plateau-nothing-changed", "stop_not_worth_it", "the first round changed nothing, so another will not", [step(verdict=False, changed=0)], metric=None),
        stop("plateau-missing-unchanged", "stop_not_worth_it", "the same three things are missing after three rounds", [step(missing=["a", "b", "c"]) for _ in range(3)], metric=None),
        # oscillation
        stop("oscillation-higher", "stop_not_worth_it", "0.5, 0.7, 0.5, 0.7: the last round only repeats the cycle", track([0.5, 0.7, 0.5, 0.7])),
        stop("oscillation-lower", "stop_not_worth_it", "errors 6, 4, 6, 4: no new best, going round", track([6, 4, 6, 4]), metric={"better": "lower", "target": 0}),
        # regress
        stop("regress-higher", "stop_not_worth_it", "the last round made it worse: keep the best and stop", track([0.5, 0.7, 0.4])),
        stop("regress-lower", "stop_not_worth_it", "errors went 5, 3, 6: worse", track([5, 3, 6]), metric={"better": "lower", "target": 0}),
        # near the ceiling
        stop("near-spend-ceiling", "stop_good_enough", "17 of 20 dollars used and not met: a natural, safe stopping point, say what is left", track([0.4, 0.6], spend=8.5, missing=["the last two tests"])),
        stop("near-time-ceiling", "stop_good_enough", "12000 of 14400 seconds used: wrap up", track([0.4, 0.6], seconds=6000.0)),
        stop("below-soft-but-dear-round", "stop_not_worth_it", "70 percent of the money used and the last round cost over half of what remained for under half of the gap", track([0.3, 0.6], spend=7.0)),
        # one pass
        stop("one-pass-done-unmet", "stop_good_enough", "the person asked for one pass: it is done, report what is left", [step(0.5, missing=["the summary"])], stated={"one_pass": True}),
        stop("one-pass-done-met", "stop_met", "one pass asked and it met the goal", [step(0.95, verdict=True)], stated={"one_pass": True}),
        stop("three-passes-asked", "stop_good_enough", "the person asked for three passes and made three, with progress still being made", track([0.2, 0.4, 0.6]), stated={"max_iterations": 3}),
        stop("person-says-stop", "stop_good_enough", "the person asked to stop", track([0.3, 0.6]), stated={"stop": True}),
        # keep going
        stop("keep-going-through-plateau", c, "the person said keep going until X: a plateau does not outrank that", track([0.6, 0.6, 0.6]), stated={"keep_going_until": "every test passes", "until_reached": False}),
        stop("keep-going-through-regress", c, "keep going was asked and X is not reached", track([0.5, 0.4]), stated={"keep_going_until": "every test passes", "until_reached": False}),
        stop("keep-going-reached", "stop_met", "what the person asked to keep going until is reached", track([0.6, 0.9]), stated={"keep_going_until": "every test passes", "until_reached": True}),
        stop("keep-going-at-ceiling", "ask", "keep going was asked but the ceiling is reached: raising it is the person's to say", track([0.5, 0.6], spend=9.0), stated={"keep_going_until": "every test passes", "until_reached": False}),
        stop("keep-going-met-standard-not-theirs", c, "the done-standard is met but the person's own stop condition is not", [step(0.8, verdict=True)], stated={"keep_going_until": "the report is in two languages", "until_reached": False}),
        # human-only blocker
        stop("human-blocker-with-progress", "ask", "what is missing is a signature only a person can give: iterating cannot supply it", track([0.5, 0.7], missing=["a signature"]), needs_human="a signature"),
        stop("human-blocker-plateau", "ask", "a login only a person holds: ask, do not iterate", track([0.4, 0.4]), needs_human="a login"),
        stop("human-blocker-already-met", "stop_met", "met, so there is nothing to ask", [step(0.95, verdict=True)], needs_human="a signature"),
        stop("human-blocker-one-pass", "stop_good_enough", "the person asked for one pass: stop and report what only they can supply", [step(0.5)], needs_human="a payment", stated={"one_pass": True}),
        # policy bound
        stop("policy-forbids", "stop_good_enough", "policy does not allow unasked iteration here", [step(0.5)], policy={"forbids_iteration": True}),
        stop("policy-iteration-cap", "stop_good_enough", "policy allows two iterations and both are used", track([0.3, 0.5]), policy={"max_iterations": 2}),
        stop("policy-authority-used", "ask", "the Representative's authority is used up: the person can extend it", track([0.3, 0.5]), policy={"authority_exhausted": True}),
        stop("policy-outranks-keep-going", "stop_good_enough", "policy bounds what the person's wish can ask of the hub", track([0.3, 0.5]), policy={"forbids_iteration": True}, stated={"keep_going_until": "all done", "until_reached": False}),
        # milestone already reached
        stop("milestone-reached-unmet-standard", "stop_met", "the next milestone is already reached: more iteration aims beyond it", track([0.5, 0.7]), milestone={"text": "the first version", "reached": True}),
        stop("milestone-reached-progressing", "stop_met", "the next milestone is reached even with progress still being made", track([0.2, 0.5, 0.8]), milestone={"text": "the draft", "reached": True}),
        # tiny gain at high cost
        stop("tiny-gain-high-cost", "stop_not_worth_it", "0.06 of an 0.8 gap for 9 dollars of the 19 that remained", [step(0.2), step(0.26, spend=9.0)]),
        stop("tiny-gain-high-time", "stop_not_worth_it", "a few percent of the gap for much of the time left", [step(0.2), step(0.25, seconds=7000.0)]),
        # large gain at small cost
        stop("large-gain-small-cost", c, "0.2 to 0.7 for 50 cents", [step(0.2), step(0.7, spend=0.5)]),
        stop("good-gain-small-cost", c, "0.2 to 0.5 for 2 dollars of 20: a share of the gap well above the share of the budget", [step(0.2), step(0.5, spend=2.0)]),
        # misleading self-claims
        stop("claim-met-check-not", c, "the worker says it is met, the check says not, and the metric is moving", [step(0.3, claimed=True), step(0.6, claimed=True)]),
        stop("claim-met-unchecked-gap", c, "a claim of done with no check, and the outcome shows 200 of 344 covered", [step(None, verdict=None, claimed=True, outcome={"text": "Processed the entries.", "coverage": GAP})], metric=None),
        stop("claim-met-plateau", "stop_not_worth_it", "the worker keeps saying it is done while the metric does not move", [step(0.5, claimed=True), step(0.5, claimed=True), step(0.5, claimed=True)]),
        stop("shallow-check-passed-gap", c, "a check that only asks for text said met, but the outcome declares 200 of 344 covered", [step(0.5, verdict=True, outcome={"text": "Processed the entries.", "coverage": GAP})]),
        stop("shallow-check-passed-refused", c, "a check that only asks for text said met, but the outcome says a step was refused", [step(0.5, verdict=True, outcome={"text": "Done.", "refused": "authority"})]),
        stop("shallow-check-passed-truly-met", "stop_met", "the outcome really is complete, so the second reading agrees", [step(0.9, verdict=True, outcome={"text": "Processed the entries.", "coverage": {"processed": 344, "total": 344}})]),
        # good enough, cap, firsts
        stop("good-enough-level", "stop_good_enough", "the metric is at the level the person accepts and what is left is small", track([0.5, 0.8, 0.92]), metric={"better": "higher", "target": 1.0, "good_enough": 0.9}, ),
        stop("good-enough-errors", "stop_good_enough", "errors are down to the accepted two", track([9, 5, 2]), metric={"better": "lower", "target": 0, "good_enough": 2}),
        stop("iteration-cap-unasked", "stop_good_enough", "five unasked iterations are the bound even while still gaining", track([0.1, 0.25, 0.4, 0.55, 0.7])),
        stop("first-iteration-progress", c, "the first round changed things and cost little", [step(None, changed=3)], metric=None),
        stop("first-iteration-dear-and-flat", "stop_not_worth_it", "the first round cost 11 of 20 dollars and shows nothing that justifies a second", [step(None, changed=1, spend=11.0)], metric=None),
        stop("nothing-tried-yet", c, "no iteration yet: nothing to judge", [], metric=None),
    ]


def main():
    cases = [
        case("gap-known-total", {"text": TEXT, "coverage": {"processed": 200, "total": 344, "unit": "entries", "next_skip": 200}}, False),
        case("covered-total", {"text": TEXT, "coverage": {"processed": 344, "total": 344}}, True),
        case("complete-flag-wins", {"text": TEXT, "coverage": {"processed": 200, "total": 344, "complete": True}}, True),
        case("capped-unknown-size", {"text": TEXT, "coverage": {"processed": 200, "capped": True}}, False),
        case("nothing-declared", {"text": TEXT}, True),
        case("malformed-string-count", {"text": TEXT, "coverage": {"processed": "a"}}, True),
        case("malformed-negative-count", {"text": TEXT, "coverage": {"processed": -1}}, True),
        case("malformed-bool-count", {"text": TEXT, "coverage": {"processed": True}}, True),
        case("malformed-not-a-mapping", {"text": TEXT, "coverage": "x"}, True),
        case("empty-outcome", {"text": ""}, False),
        case("refused", {"text": "", "refused": "authority"}, False),
        case("plain-text-outcome", TEXT, True),
        case("requirement-held", {"text": "Updated notes.md and ran the tests."}, True, "the work is finished; the outcome must contain: notes.md; the tests"),
        case("requirement-missing", {"text": "Updated notes.md."}, False, "the work is finished; the outcome must contain: notes.md; the tests"),
    ]
    cases += stop_cases()
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
