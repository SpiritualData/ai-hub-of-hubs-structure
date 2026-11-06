"""Rebuild cases.json for Integrated Efficiency: written whole-hub tasks, each a request the assembled whole is asked as one assistant and the words a completed answer
contains. Six tasks that need no private data: two about the hub itself, two small calculations and two general questions with a settled answer.

    python3 evaluation/integrated_efficiency/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
TASKS = (("hub-judgment-calls", "Explain in one sentence what Judgment Calls decides for a person.", ("ask", "proceed")),
         ("hub-seats", "Name the five containers the hub is organised in.", ("Self", "Body", "Intelligence", "World", "Consciousness")),
         ("sum", "What is 17 plus 25?", ("42",)),
         ("product", "What is 12 times 12?", ("144",)),
         ("capital", "What is the capital of France?", ("Paris",)),
         ("water", "What is the chemical formula of water?", ("H2O",)))


def main():
    cases = [{"id": "whole-" + name, "kind": "task", "args": {"request": request, "person": ""}, "expect": {"contains": list(words)}} for name, request, words in TASKS]
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
