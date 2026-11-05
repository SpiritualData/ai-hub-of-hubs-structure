"""Rebuild cases.json for the Response Writer from the web-search seat's public set (SimpleQA questions with their gold answer and gold source
links) and from the ways a delegated piece can fail to deliver.

    python3 evaluation/response_writing/build_cases.py

A case hands the writer the results of delegated pieces: for a question, one result holding the gold answer and its gold links as items; for a failure, a
piece that was refused (authority, budget or cancelled) or that failed. A response passes when it says the answer, names no link the results
do not hold and names at least one that they do; a failure case passes when the response says the piece was not done and does not say any answer.
Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE.parent
FAILURES = (("authority", "Delete the old backup folder."), ("budget", "Search the web for every release note since 2019."),
            ("cancelled", "Summarize the quarterly report."), ("error", "Edit notes.md to add a line."))


def main():
    search = json.loads((EVAL / "search_backend" / "cases.json").read_text())
    cases = []
    for c in search:
        answer = c["answer"].strip()
        urls = [u for raw in c["gold_urls"] for u in raw.split() if u.startswith("http")]      # a gold entry may hold several links or none
        items = [{"title": "Source " + str(i + 1), "url": u, "snippet": answer} for i, u in enumerate(urls)]
        cases.append({"id": "write-" + c["id"], "kind": "answer", "args": {"results": [{"piece": c["question"], "text": answer, "items": items, "met": True}]},
                      "expect": {"answer": answer, "links": urls}})
    for reason, piece in FAILURES:
        result = {"piece": piece, "text": "", "items": [], "met": None}
        result["error" if reason == "error" else "refused"] = "the editor was unreachable" if reason == "error" else reason
        cases.append({"id": "write-fail-" + reason, "kind": "failure", "args": {"results": [result]}, "expect": {"piece": piece}})
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")


if __name__ == "__main__":
    main()
