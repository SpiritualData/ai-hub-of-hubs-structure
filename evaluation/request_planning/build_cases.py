"""Rebuild cases.json for the Planner from the case sets other seats already measure on, so each request has the worker its own seat's metric uses:
a question from the web-search set goes to web search, a literature question from the Science set to Science, a coding goal from the file-editing
set to file editing, and a request that needs no context from the retrieval set to no worker. The first twenty of each, in file order. A fifth source, ``datasets/written.json``, is 24 requests written for this evaluation with none of the cue words of the
rule arm (an imperative lookup, a gather-what-is-known request, an edit in plain words, a request that needs no worker), so the rule arm and the model arm are compared on wording the rules were not
written from.

    python3 evaluation/request_planning/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE.parent
PER_KIND = 20


def main():
    search = json.loads((EVAL / "search_backend" / "cases.json").read_text())[:PER_KIND]
    science = json.loads((EVAL / "know_the_world" / "cases.json").read_text())[:PER_KIND]
    edits = json.loads((EVAL / "file_edit_goals" / "cases.json").read_text())[:PER_KIND]
    none = json.loads((EVAL / "context_retrieval" / "datasets" / "no_context.json").read_text())[:PER_KIND]
    written = json.loads((HERE / "datasets" / "written.json").read_text())
    cases = ([{"id": "plan-search-" + c["id"], "kind": "search", "args": {"request": c["question"]}, "expect": "web-search"} for c in search]
             + [{"id": "plan-science-" + c["id"], "kind": "science", "args": {"request": c["question"]}, "expect": "the-science"} for c in science]
             + [{"id": "plan-edit-" + c["id"], "kind": "edit", "args": {"request": f"Implement the function {c['entry_point']} so that its docstring holds."}, "expect": "file-editing"} for c in edits]
             + [{"id": "plan-none-" + c["id"], "kind": "none", "args": {"request": c["task"]}, "expect": ""} for c in none]
             + [{"id": "plan-steps-01", "kind": "steps", "args": {"request": "1. Find the latest Rust release.\n2. Implement the function parse_version so that its docstring holds."},
                 "expect": ["web-search", "file-editing"]}]
             + [{"id": "plan-" + c["id"], "kind": c["kind"], "args": {"request": c["request"]}, "expect": c["expect"]} for c in written])
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
