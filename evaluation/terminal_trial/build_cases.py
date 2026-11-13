"""Rebuild cases.json for the human trial stage of the presentation metric: one case per aspect the ledger human_verdicts.csv names (what a person who used the arms on a real terminal said).
The expected result is not written here: a case's result for an arm is what the ledger says, never something the arm produces.

    python3 evaluation/terminal_trial/build_cases.py

Run it after appending a verdict that names a new aspect, then re-record the arms (`esoi run terminal_trial --impl ARM --record`). Standard library only."""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build():
    with (HERE / "human_verdicts.csv").open(newline="") as handle:
        aspects = sorted({row["aspect"] for row in csv.DictReader(handle)})
    return [{"id": f"trial-{aspect}", "kind": "aspect", "origin": "human evidence: what a person who used the arms on a real terminal said about this aspect (human_verdicts.csv)",
             "args": {"aspect": aspect}, "requirements": [], "expect": {}} for aspect in aspects]


if __name__ == "__main__":
    cases = build()
    (HERE / "cases.json").write_text(json.dumps(cases, indent=1) + "\n")
    print(len(cases), "cases")
