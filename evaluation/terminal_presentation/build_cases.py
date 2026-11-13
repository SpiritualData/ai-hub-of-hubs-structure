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
    "agents_depth1": ("a run with a helper and a finished sibling: the helper listed with its state, entered, messaged, stopped alone, left, and the finished one read (revision 4, X34 to X38)", ["X34", "X35", "X36", "X38"]),
    "agents_depth2": ("the same walk with a helper that started a helper", ["X34", "X35", "X36", "X38"]),
    "agents_depth4": ("the same walk four levels deep: each level entered, a message at the bottom, one key up a level at a time", ["X34", "X35", "X36", "X38"]),
    "agents_depth_compare": ("the screen inside a helper at depth 4 against depth 1: content width, header and footer rows, key hints and the time to enter, within the stated tolerance", ["X37"]),
    "real_agents": ("a real fast-tier run over made-up garden notes (one helper that read two files, recorded 2026-11-12): the helper listed, entered while it worked and after it ended, its result once", ["X34", "X38"]),
    "feed_noise": ("a run with the agent's task-list tools, reads of files that are not there, commands that did not work (one repeated) and a helper with a long name: no bookkeeping line, one short muted line per failed kind, a clean footer at 56, 80 and 120 columns (revision 5, X39 X40 X42 X43)", ["X39", "X40", "X42", "X43"]),
    "ceiling_stop": ("a run stopped at its spend ceiling while a helper works: said once, with what is kept, how to continue and how to raise the limit (revision 5, X41 X42)", ["X41", "X42"]),
}
# The protocol ceiling column (the structure on request, spend against ceilings, who the AI acts for, a correction shown as taken up, stopping one helper: X24, X26, X32, X6, X8) is read
# inside the watch, steer and target cases and reported in the details, not scored.
CASES = [{"id": f"presentation-{name}", "kind": "presentation", "origin": "rule: " + why + " (docs/explanation/working-with-the-ai-while-it-works.md)",
          "args": {"scenario": name}, "requirements": ids, "expect": {"failed": []}} for name, (why, ids) in SCENARIOS.items()]

if __name__ == "__main__":
    (HERE / "cases.json").write_text(json.dumps(CASES, indent=1) + "\n")
    print(len(CASES), "cases")
