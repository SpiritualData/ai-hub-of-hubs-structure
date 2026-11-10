"""Rebuild cases.json for Plain Install: ordinary inputs a person types on a machine with only a logged-in Claude CLI and no vendor key. Each case says the words a
good outcome holds (``contains``, any one of them when ``any``; none for an open question, where any real answer holds) and which files exist in the folder the work runs in. A case passes only when the front door ends with a
real answer or an honest, actionable message, no raw error text, and **zero warnings** (the result's ``note`` is empty and no step of the answer is reported broken):
a message that would appear for most people on a plain install is a defect to fix, or not worth saying.

    python3 evaluation/plain_install/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = {"notes.txt": "Project Aurora\nStatus: green\nBudget: 12000 dollars\n", "calc.py": "def add(a, b):\n    return a - b\n"}
CASES = (
    ("about-the-hub", "What can you do?", (), ["hub of hubs"], False),
    ("factual-needing-the-web", "What is the latest stable version of Python?", (), ["3.15"], False),
    ("general-question", "Explain how photosynthesis works", (), [], False),
    ("local-file", "What does notes.txt say about the budget?", ("notes.txt",), ["12000"], False),
    ("small-file-edit", "Fix the bug in calc.py so add returns the sum", ("calc.py",), ["ahohs work"], False),
    ("multi-step", "Compare the population of France and Germany, then tell me which has more people; then give me the ratio", (), [], False),
    ("a-decision-for-a-person", "Should I pay the 12000 dollar invoice today?", (), ["your decision"], False),
    ("empty", "", (), ["type a question"], False),
    ("very-long", "Explain the history of the printing press in Europe and its effect on literacy. " * 400, (), [], False),
    ("missing-file", "What does missing_report.txt say?", (), ["could not find"], False),
)


def main():
    cases = [{"id": "plain-" + name, "kind": "ask", "args": {"request": request, "files": {f: FILES[f] for f in files}},
              "expect": {"contains": words, "any": any_word}} for name, request, files, words, any_word in CASES]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
