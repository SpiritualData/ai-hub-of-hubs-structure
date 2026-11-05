"""Rebuild cases.json for Objectives from rules a standing view of a person's intents and goals states, with invented neutral objectives (a garden, a house move, a
study plan, a trip) and no consumer data. Every case has ``origin: rule`` (written to exercise a rule, none is a recording of real use) and says which rule:

  rollup    a goal rolls up to its parent: progress is the share of units met, units being the objective's own criteria and its children (each counting its own
            progress); met only when every unit is; an objective with no criteria and no children is met only when it says so; an unknown parent makes a root, and members of a cycle are listed once, from the first.
  place     a request goes under the live objective whose own words it shares most, the deeper one on a tie; a met objective is no longer live; with no shared
            word no objective is named; the answer carries the path from the top.

    python3 evaluation/live_objectives/build_cases.py

``expect`` for a rollup case is the list of ``[id, depth, state, progress]``; for a place case it is ``[objective, path]``. Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def obj(ident, title, parent="", done_when=(), met=None):
    out = {"id": ident, "title": title, "parent": parent, "done_when": [{"text": t, "met": m} for t, m in done_when]}
    if met is not None:
        out["met"] = met
    return out


GARDEN = [obj("garden", "Grow vegetables for the summer", done_when=[("a harvest of tomatoes is eaten", False)]),
          obj("beds", "Build the raised beds", "garden", [("four beds are filled with soil", True), ("a watering line reaches the beds", False)]),
          obj("seeds", "Order the seeds", "garden", [("tomato and basil seeds arrive", True)])]
MOVE = [obj("move", "Move to the new house", done_when=[("the old flat is handed back", False)]),
        obj("pack", "Pack the books and the kitchen", "move", [("all boxes are labelled", True), ("the van is booked", True)]),
        obj("utilities", "Transfer the electricity and internet", "move", [("the electricity contract is moved", False), ("the internet is connected", False)]),
        obj("broadband", "Choose an internet provider", "utilities", met=True)]
STUDY = [obj("exam", "Pass the chemistry exam", done_when=[("a practice paper scores above 70 percent", False)]),
         obj("organic", "Revise organic reactions", "exam", [("every reaction card is reviewed", False)]),
         obj("lab", "Finish the lab report", met=True)]
TRIP = [obj("trip", "Walk the coastal path in May"),
        obj("gear", "Buy walking boots", "trip", [("boots are bought", False), ("boots are worn in", False)])]


def rolled(*rows):
    return [list(r) for r in rows]


def rollup(name, objectives, expect):
    return {"id": "objectives-rollup-" + name, "kind": "rollup", "origin": "rule", "args": {"objectives": objectives}, "expect": expect}


def place(name, request, objectives, expect_id, expect_path):
    return {"id": "objectives-place-" + name, "kind": "place", "origin": "rule", "args": {"request": request, "objectives": objectives}, "expect": [expect_id, expect_path]}


def main():
    cases = [
        rollup("goal-rolls-up-to-parent", GARDEN, rolled(("garden", 0, "in progress", 0.5), ("beds", 1, "in progress", 0.5), ("seeds", 1, "met", 1.0))),
        rollup("met-needs-every-unit", MOVE, rolled(("move", 0, "in progress", 0.4444), ("pack", 1, "met", 1.0), ("utilities", 1, "in progress", 0.3333), ("broadband", 2, "met", 1.0))),
        rollup("no-criteria-no-children-says-so", STUDY, rolled(("exam", 0, "not started", 0.0), ("organic", 1, "not started", 0.0), ("lab", 0, "met", 1.0))),
        rollup("empty-objective-is-not-started", TRIP, rolled(("trip", 0, "not started", 0.0), ("gear", 1, "not started", 0.0))),
        rollup("children-listed-before-parent", [GARDEN[1], GARDEN[0]], rolled(("garden", 0, "in progress", 0.25), ("beds", 1, "in progress", 0.5))),
        rollup("unknown-parent-becomes-a-root", [obj("orphan", "Learn to bake bread", "gone", [("a loaf is baked", True)])], rolled(("orphan", 0, "met", 1.0))),
        rollup("no-objectives", [], []),
        rollup("parent-with-only-met-children-is-met", [obj("a", "Declutter the garage", ""), obj("b", "Sort the tools", "a", met=True)], rolled(("a", 0, "met", 1.0), ("b", 1, "met", 1.0))),
        rollup("a-cycle-is-listed-once-from-its-first-member", [obj("x", "First", "y", [("one", True)]), obj("y", "Second", "x", [("two", False)])], rolled(("x", 0, "in progress", 0.5), ("y", 1, "not started", 0.0))),
        place("a-met-child-is-not-live-so-its-parent-takes-it", "Where should I buy the tomato seeds this week?", GARDEN, "garden", ["garden"]),
        place("deeper-wins-a-tie", "Plan the watering line for the beds", GARDEN, "beds", ["garden", "beds"]),
        place("path-runs-from-the-top", "Is the electricity contract transferred yet?", MOVE, "utilities", ["move", "utilities"]),
        place("met-objective-is-not-live", "Choose an internet provider", [MOVE[0], MOVE[3]], "", []),
        place("no-shared-word", "What is the capital of Peru?", GARDEN, "", []),
        place("stop-words-do-not-count", "What should I do about the", GARDEN, "", []),
        place("plural-matches-singular", "Review every reaction for organic chemistry", STUDY, "organic", ["exam", "organic"]),
        place("most-shared-words-wins", "Revise organic reactions before the exam", STUDY, "organic", ["exam", "organic"]),
        place("top-level-by-its-criteria", "Book a practice paper for next week", STUDY, "exam", ["exam"]),
        place("boots", "How do I wear in new walking boots?", TRIP, "gear", ["trip", "gear"]),
        place("no-objectives", "Anything at all about gardens", [], "", []),
    ]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1, sort_keys=True) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
