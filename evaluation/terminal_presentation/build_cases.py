"""Rebuild cases.json for the presentation metric (layer 1) of Terminal Experience: one case per scripted scenario, each drawn at 80x24 and 120x40 and read back from the
emulated screen. The expected result is written here, never produced by an arm: no check of the case may fail.

    python3 evaluation/terminal_presentation/build_cases.py

Standard library only."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

SCENARIOS = {
    "watch": ("a run with a read, an edit, a helper and a command, then its report", ["X1", "X2", "X10", "X13", "X18"]),
    "steer": ("a correction typed while the run works", ["X6", "X23"]),
    "stop_resume": ("Escape then resume, finished work kept", ["X4", "X5", "X21", "X33"]),
    "approve": ("a risky step waits with its preview, then is approved", ["X9", "X19"]),
    "refuse": ("a risky step waits with its preview, then is refused", ["X9", "X19", "X20"]),
    "target": ("stopping one helper, or being told the harness cannot", ["X8"]),
    "plain": ("the same run written to something that is not a terminal", ["X13"]),
    "pasted_run": ("the run the owner pasted on 2026-11-11 at a narrow width: header, goal, steps, answer once, markdown, figures, closing and the resume command (revision 2)", ["X1", "X2", "X3", "X10", "X13", "X16", "X18", "X33"]),
    "real_run": ("a real native run's recorded events (the interim note is the answer cut with three dots, three figure updates before the finish): the answer is on the screen once (revision 3)", ["X1", "X10", "X13", "X18"]),
}
# The protocol ceiling column (the structure on request, spend against ceilings, who the AI acts for, a correction shown as taken up, stopping one helper: X24, X26, X32, X6, X8) is read
# inside the watch, steer and target cases and reported in the details, not scored.
CASES = [{"id": f"presentation-{name}", "kind": "presentation", "origin": "rule: " + why + " (docs/explanation/working-with-the-ai-while-it-works.md)",
          "args": {"scenario": name}, "requirements": ids, "expect": {"failed": []}} for name, (why, ids) in SCENARIOS.items()]

if __name__ == "__main__":
    (HERE / "cases.json").write_text(json.dumps(CASES, indent=1) + "\n")
    print(len(CASES), "cases")
