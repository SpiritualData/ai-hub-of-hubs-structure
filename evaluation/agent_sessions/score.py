"""Scores a Delegated Agent Sessions arm on general tasks that are not coding.

Each case is a small folder of plain files, a goal and the facts the agent's final report must hold. A fresh temporary folder holds the files; the agent
gets the goal and the folder as its working directory and nothing else. Pass = the run says it met the goal and its final report holds every expected
fact (case-insensitive) and the files are unchanged (the tasks ask to read and report, not to change). One number: the share of cases passed, with cost and time
folded by ``[balance.agent_sessions]``. The runners are the Claude Code CLI runners on the existing subscription; their dollars are the CLI's own estimate.
"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CLAUDE_MODEL = "haiku"
MAX_TURNS = 15


def adapt(implementation, meter):
    """``implementation`` is the declared runner class; returns ``run(kind, args) -> DeepResult`` for one case folder."""
    from file_edit_goals.score import agent_config, agent_settings

    def run(kind, args):
        meter.model = CLAUDE_MODEL
        runner = implementation(agent_config(args["root"]), settings=agent_settings())
        result = runner.run_goal(goal=args["goal"], brief=args["goal"], model=CLAUDE_MODEL, max_turns=MAX_TURNS)
        meter.record()
        meter.cost_usd += float(getattr(result, "cost_usd", 0.0) or 0.0)
        return result
    return run


def score_case(fn, case):
    root = Path(tempfile.mkdtemp(prefix="agent_session_"))
    try:
        for name, text in case["files"].items():
            (root / name).write_text(text, encoding="utf-8")
        result = fn("report", dict(root=str(root), goal=case["goal"]))
        report = str(getattr(result, "output", "") or "").lower()
        missing = [fact for fact in case["expect"] if fact.lower() not in report]
        changed = [name for name, text in case["files"].items() if not (root / name).is_file() or (root / name).read_text(encoding="utf-8") != text]
        ok = bool(getattr(result, "met", False)) and not missing and not changed
        note = "" if ok else (getattr(result, "error", None) or (f"the report lacks {missing}" if missing else f"files changed: {changed}" if changed else "the run did not meet the goal"))
        return dict(ok=ok, got=report[:60], note=str(note)[:120])
    finally:
        shutil.rmtree(root, ignore_errors=True)
