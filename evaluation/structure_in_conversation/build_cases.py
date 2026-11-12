"""Rebuild cases.json for Structure in Conversation: thirty written turns over neutral records (a person keeping a daily practice), each with the move the
turn calls for, the records held, the caller's draft of the missing pieces and what was declined or held, and the projected result an arm must give.

Kinds: stay_out (six turns that must stay plain), frame_bare (four, nothing held but a problem and an ideal), frame_existing (three, the solution, an alternative,
a metric with a value and a milestone are held), reuse_complete (two, nothing is missing), compare (three), review (five, values come only from the records),
focus (three), declined (two, an offer declined before is not made again) and held (two, a held solution gets no milestone). Weights are fixed here, before any
arm is scored: every case counts once.

    python3 evaluation/structure_in_conversation/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOLUTION = "Build a steady practice"
ALTERNATIVES = [{"name": "Morning session", "description": "Practice before the day starts."}, {"name": "Evening session", "description": "Practice after dinner."},
                {"name": "Weekend block", "description": "One long session each weekend."}]
DRAFT = {"solution_name": SOLUTION, "alternatives": ALTERNATIVES, "metric": {"name": "Sessions completed per week", "record": "Counted each week."},
         "milestone": "Ten sessions logged"}
BARE = {"problems": {"p-1": {"name": "Practice is irregular"}}, "ideals": {"i-1": {"name": "A practice that holds without effort"}}}


def records(metric_record="Current value: 4 (as of 2026-11-03, from the person's own report)\nSessions per week.", milestones="1. Ten sessions logged", solution_extra=None,
            with_metric=True, with_alternative=True):
    held = {"solutions": {"s-1": dict({"name": SOLUTION, "problem_ids": "p-1", "ideal_ids": "i-1", "milestones": milestones}, **(solution_extra or {}))},
            "implementations": {"a-1": {"solution_id": "s-1", "name": "Morning session"}} if with_alternative else {}}
    if with_metric:
        held["metrics"] = {"m-1": {"name": "Sessions completed per week", "solution_ids": "s-1", "record": metric_record}}
    return dict(json.loads(json.dumps(BARE)), **held)


def turn(move, held, relevant=(), draft=None, declined=(), held_ids=()):
    return {"move": move, "records": held, "relevant_solution_ids": list(relevant), "draft": DRAFT if draft is None else draft, "declined": list(declined),
            "held": list(held_ids)}


def expect(move, parts=(), solution=None, alternatives=(0, 0), metric=None, reading=None, milestone=None, offer=None, edits=0):
    return {"move": move, "parts": sorted(parts), "solution": solution, "alternatives": list(alternatives), "metric": metric, "reading": reading, "milestone": milestone,
            "offer": offer, "edits": edits}


ALL = ("problem", "ideal", "solution", "alternatives", "metric", "milestone")
PLAIN = expect("none")
cases = []


def add(kind, name, built_turn, wanted):
    cases.append({"id": f"{kind}-{name}", "kind": kind, "args": {"turn": built_turn}, "expect": wanted})


for name, held in (("bare", BARE), ("full", records()), ("empty", {}), ("with-relevant", records())):
    add("stay_out", name, turn("none", held, relevant=["s-1"] if name == "with-relevant" else ()), PLAIN)
add("stay_out", "unknown-move", turn("banter", records(), relevant=["s-1"]), PLAIN)
add("stay_out", "none-with-draft", turn("none", BARE, draft=DRAFT), PLAIN)

add("frame_bare", "three-alternatives", turn("frame", BARE),
    expect("frame", ALL, "proposed", (0, 3), "proposed", None, "proposed", ["solution", "alternatives", "metric", "milestone"], 6))
add("frame_bare", "two-alternatives", turn("frame", BARE, draft=dict(DRAFT, alternatives=ALTERNATIVES[:2])),
    expect("frame", ALL, "proposed", (0, 2), "proposed", None, "proposed", ["solution", "alternatives", "metric", "milestone"], 5))
many = [{"name": f"Option {n}", "description": ""} for n in range(7)]
add("frame_bare", "capped-at-five", turn("frame", BARE, draft=dict(DRAFT, alternatives=many)),
    expect("frame", ALL, "proposed", (0, 5), "proposed", None, "proposed", ["solution", "alternatives", "metric", "milestone"], 8))
add("frame_bare", "no-metric-no-milestone-drafted", turn("frame", BARE, draft={"solution_name": SOLUTION, "alternatives": ALTERNATIVES}),
    expect("frame", ("problem", "ideal", "solution", "alternatives"), "proposed", (0, 3), None, None, None, ["solution", "alternatives"], 4))

add("frame_existing", "one-held-two-new", turn("frame", records(), ["s-1"]),
    expect("frame", ALL, "existing", (1, 2), "existing", "4", "existing", ["alternatives"], 2))
add("frame_existing", "all-new", turn("frame", records(), ["s-1"], draft=dict(DRAFT, alternatives=ALTERNATIVES[1:])),
    expect("frame", ALL, "existing", (1, 2), "existing", "4", "existing", ["alternatives"], 2))
add("frame_existing", "same-name-other-spacing", turn("frame", records(), ["s-1"], draft=dict(DRAFT, alternatives=[{"name": "  morning   SESSION", "description": ""}, ALTERNATIVES[1]])),
    expect("frame", ALL, "existing", (1, 1), "existing", "4", "existing", ["alternatives"], 1))

add("reuse_complete", "only-held-named", turn("frame", records(), ["s-1"], draft=dict(DRAFT, alternatives=[ALTERNATIVES[0]])),
    expect("frame", ALL, "existing", (1, 0), "existing", "4", "existing"))
add("reuse_complete", "no-alternatives-drafted", turn("frame", records(), ["s-1"], draft={}),
    expect("frame", ALL, "existing", (1, 0), "existing", "4", "existing"))

add("compare", "solution-no-metric", turn("compare", records(with_metric=False), ["s-1"], draft=dict(DRAFT, alternatives=ALTERNATIVES[1:])),
    expect("compare", ("solution", "alternatives", "metric"), "existing", (1, 2), "proposed", None, None, ["alternatives", "metric"], 3))
add("compare", "full-records", turn("compare", records(), ["s-1"]),
    expect("compare", ("solution", "alternatives", "metric"), "existing", (1, 2), "existing", "4", None, ["alternatives"], 2))
add("compare", "no-solution-yet", turn("compare", BARE),
    expect("compare", ("solution", "alternatives", "metric"), "proposed", (0, 3), "proposed", None, None, ["solution", "alternatives", "metric"], 5))

add("review", "value-held", turn("review", records(), ["s-1"]),
    expect("review", ("solution", "metric", "milestone"), "existing", (0, 0), "existing", "4", "existing"))
add("review", "no-value-logged", turn("review", records(metric_record="Sessions per week."), ["s-1"]),
    expect("review", ("solution", "metric", "milestone"), "existing", (0, 0), "existing", None, "existing"))
add("review", "no-metric-held", turn("review", records(with_metric=False), ["s-1"], draft={}),
    expect("review", ("solution", "milestone"), "existing", (0, 0), None, None, "existing"))
two = records()
two["metrics"]["m-2"] = {"name": "Minutes per session", "solution_ids": "s-1", "record": "Current value: 7 (as of 2026-11-05, from the person's own report)"}
two["solutions"]["s-1"]["authoritative_metric_id"] = "m-2"
add("review", "authoritative-metric-wins", turn("review", two, ["s-1"]),
    expect("review", ("solution", "metric", "milestone"), "existing", (0, 0), "existing", "7", "existing"))
add("review", "no-matching-solution", turn("review", records(), []), expect("review"))

add("focus", "problem-and-next-milestone", turn("focus", records(), ["s-1"]),
    expect("focus", ("problem", "milestone"), None, (0, 0), None, None, "existing"))
add("focus", "no-solution-held", turn("focus", BARE), expect("focus", ("problem",)))
done = records(solution_extra={"milestone_entries": [{"sentence": "Ten sessions logged", "met": True}]})
add("focus", "every-milestone-met", turn("focus", done, ["s-1"]), expect("focus", ("problem",)))

add("declined", "whole-offer-declined", turn("frame", BARE, declined=["structure:build a steady practice:solution,alternatives,metric,milestone"]),
    expect("frame", ALL, "proposed", (0, 3), "proposed", None, "proposed"))
add("declined", "alternatives-offer-declined", turn("frame", records(), ["s-1"], declined=["structure:s-1:alternatives"]),
    expect("frame", ALL, "existing", (1, 2), "existing", "4", "existing"))

add("held", "no-milestone-for-held-solution", turn("frame", records(milestones=""), ["s-1"], held_ids=["s-1"]),
    expect("frame", ALL, "existing", (1, 2), "existing", "4", "proposed", ["alternatives"], 2))
add("held", "nothing-else-missing", turn("frame", records(milestones=""), ["s-1"], draft=dict(DRAFT, alternatives=[ALTERNATIVES[0]]), held_ids=["s-1"]),
    expect("frame", ALL, "existing", (1, 0), "existing", "4", "proposed"))

def many():
    """A quest that holds several solutions, each with its own problem, ideal and metric (one with a value logged), as a person who has built structure over time."""
    return {"problems": {"p-1": {"name": "Practice is irregular"}, "p-2": {"name": "Progress is hard to see"}, "p-3": {"name": "Energy runs low"}},
            "ideals": {"i-1": {"name": "A practice that holds without effort"}, "i-2": {"name": "Visible, steady improvement"}},
            "solutions": {"s-1": {"name": "Keep a routine", "problem_ids": ["p-1"], "ideal_ids": ["i-1"], "milestones": "1. Ten sessions logged", "authoritative_metric_id": "m-1"},
                          "s-2": {"name": "Build a skill", "problem_ids": ["p-2"], "ideal_ids": ["i-2"], "milestones": "1. Pass the first checkpoint", "authoritative_metric_id": "m-2"},
                          "s-3": {"name": "Rest well", "problem_ids": ["p-3"], "ideal_ids": ["i-1"]}},
            "implementations": {"a-2": {"solution_id": "s-2", "name": "Daily drill"}},
            "metrics": {"m-1": {"name": "Sessions per week", "solution_ids": ["s-1"], "record": "Current value: 4 (as of 2026-11-03, from the person's own report)"},
                        "m-2": {"name": "Checkpoint score", "solution_ids": ["s-2"], "record": "Current value: 7 (as of 2026-11-05, from the person's own report)"}}}


MANY_ALL = ("problem", "ideal", "solution", "alternatives", "metric", "milestone")
add("several", "frame-matched-keeps-its-own-metric", turn("frame", many(), ["s-2"]),
    expect("frame", MANY_ALL, "existing", (1, 3), "existing", "7", "existing", ["alternatives"], 3))
add("several", "compare-matched", turn("compare", many(), ["s-2"]),
    expect("compare", ("solution", "alternatives", "metric"), "existing", (1, 3), "existing", "7", None, ["alternatives"], 3))
add("several", "review-matched-reads-its-value", turn("review", many(), ["s-2"]),
    expect("review", ("solution", "metric", "milestone"), "existing", (0, 0), "existing", "7", "existing"))
add("several", "review-other-solution-other-value", turn("review", many(), ["s-1"]),
    expect("review", ("solution", "metric", "milestone"), "existing", (0, 0), "existing", "4", "existing"))
add("several", "focus-matched", turn("focus", many(), ["s-2"]), expect("focus", ("problem", "milestone"), None, (0, 0), None, None, "existing"))
add("several", "none-fits-proposes-a-new-solution", turn("frame", many(), []),
    expect("frame", ("solution", "alternatives", "metric", "milestone"), "proposed", (0, 3), "proposed", None, "proposed", ["solution", "alternatives", "metric", "milestone"], 6))

(HERE / "cases.json").write_text(json.dumps(cases, indent=1, sort_keys=True) + "\n")
print(f"{len(cases)} cases")
