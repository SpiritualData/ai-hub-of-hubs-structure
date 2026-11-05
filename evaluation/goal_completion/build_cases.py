"""Rebuild cases.json for Goal Completion from the coverage cases the repository's own done-evidence tests assert (tests/test_critique_done_evidence.py:
a known total above processed is a gap, an explicit complete flag wins, a capped read of unknown size is a gap, and anything undeclared or malformed
never blocks) and from the other ways an outcome can fail a done-standard: empty, refused, or missing a requirement the standard names.

    python3 evaluation/goal_completion/build_cases.py

A case is a goal, its done-standard and an outcome; ``expect`` is whether the goal is met. Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
GOAL = "process every entry"
STANDARD = "every entry was processed"
TEXT = "Processed the entries."


def case(name, outcome, met, standard=STANDARD):
    return {"id": "goal-" + name, "kind": "outcome", "args": {"goal": GOAL, "done_standard": standard, "outcome": outcome}, "expect": met}


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
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
