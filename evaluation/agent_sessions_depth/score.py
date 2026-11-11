"""Scores a Delegated Agent Sessions arm on depth work: cases that need parts read separately, records in the folder, a consumer's skills
or an earlier finding, plus one small case where depth is waste. Every check is code; no model judge.

Ability first: the run says it met the goal, the facts or files are right (per part where the case has parts), the folder's tests pass where
the case has them, and no file that should stay the same changed (the skills folder included). Cost, wall time and calls are recorded by the
harness for every case; this scorer adds ``subagent_calls`` and ``turns`` to the row when the run's result exposes them (an attribute of that
name), and notes a sub-agent used on the small case without failing it: the cost is the penalty.

The skills folder and the earlier finding are case data. ``adapt`` hands them only to an arm whose constructor names ``skills_dir`` or
``recall`` as a parameter (read from its signature, never by the arm's name); an arm that cannot take them gets the goal and the folder alone.
Arms, credentials and cost basis are those of ``agent_sessions_hard`` (whose settings and time-limit mechanism this reuses).
"""
import dataclasses
import inspect
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_sessions import score as base   # noqa: E402
from agent_sessions_hard import score as hard   # noqa: E402

HERE = Path(__file__).resolve().parent
AGENT_SECONDS = 600
MAX_TURNS = 60
SKILLS_PARAMETER = "skills_dir"
RECALL_PARAMETER = "recall"


def accepts(implementation, name):
    """Whether the arm's constructor names ``name`` as a parameter (a catch-all ``**kwargs`` does not count)."""
    try:
        parameter = inspect.signature(implementation).parameters.get(name)
    except (TypeError, ValueError):
        return False
    return parameter is not None and parameter.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)


def extras_for(implementation, args):
    """The constructor arguments this case may add for this arm: the skills folder and the known text, each only if the arm takes it."""
    extras = {}
    if args.get("skills_dir") and accepts(implementation, SKILLS_PARAMETER):
        extras[SKILLS_PARAMETER] = args["skills_dir"]
    if args.get("known") and accepts(implementation, RECALL_PARAMETER):
        known = args["known"]
        extras[RECALL_PARAMETER] = lambda goal: known   # a consumer's recall: the goal in, the text it already knows out
    return extras


def adapt(implementation, meter):
    """``run(kind, args) -> DeepResult``: as the hard stage's, plus the case's skills folder and known text for an arm that takes them."""
    base.AGENT_SECONDS = AGENT_SECONDS
    settings = dataclasses.replace(base.agent_settings(implementation), instruction_pack=hard.pack_text)

    def run(kind, args):
        runner = implementation(base.agent_config(args["root"]), settings=settings, **extras_for(implementation, args))
        meter.model = getattr(runner, "model", None) or getattr(runner, "tier_model", None) or "default"
        result = runner.run_goal(goal=args["goal"], brief=args["goal"], max_turns=MAX_TURNS)
        meter.record()
        meter.cost_usd += float(getattr(result, "cost_usd", 0.0) or 0.0)
        return result
    return run


def load_cases():
    return json.loads((HERE / "cases.json").read_text(encoding="utf-8"))


def snapshot(folder):
    return {str(p.relative_to(folder)): p.read_bytes() for p in sorted(Path(folder).rglob("*")) if p.is_file() and "__pycache__" not in p.parts}


def report_problems(case, report):
    """Per part: the part names that lack any of their facts."""
    return [f"part {part['part']} lacks {[f for f in part['facts'] if not base.word_in(f, report)]}"
            for part in case.get("expect_report", []) if not all(base.word_in(f, report) for f in part["facts"])]


def json_problems(root, expect):
    target = Path(root, expect["file"])
    if not target.is_file():
        return [f"{expect['file']} was not written"]
    try:
        got = json.loads(target.read_text(encoding="utf-8"))
    except ValueError:
        return [f"{expect['file']} is not JSON"]
    problems = []
    for key, want in expect["values"].items():
        value = got.get(key) if isinstance(got, dict) else None
        if isinstance(want, list):
            same = isinstance(value, list) and sorted(map(str, value)) == sorted(map(str, want))
        elif isinstance(want, float):
            same = isinstance(value, (int, float)) and not isinstance(value, bool) and abs(value - want) < 0.005
        else:
            same = value == want
        if not same:
            problems.append(f"{key} is {value!r}, not the right value")
    return problems


def test_problems(root, case):
    """Every folder test file runs on its own, so the note names the milestone that fails."""
    if not case.get("hidden_tests"):
        return []
    base.write_files(root, case["tests"])
    base.write_files(root, case["hidden_tests"])
    failed = []
    for name in sorted(list(case["tests"]) + list(case["hidden_tests"])):
        ok, last = base.run_tests(root, [name])
        if not ok:
            failed.append(f"{name}: {last}")
    return [f"tests fail: {failed}"] if failed else []


def score_case(fn, case):
    root = Path(tempfile.mkdtemp(prefix="agent_session_depth_"))
    skills_root = Path(tempfile.mkdtemp(prefix="agent_session_depth_skills_"))
    try:
        base.write_files(root, case["files"])
        base.write_files(root, case.get("tests", {}))
        base.write_files(skills_root, case.get("skills", {}))
        skills_before = snapshot(skills_root)
        args = dict(root=str(root), goal=case["goal"])
        if case.get("skills"):
            args["skills_dir"] = str(skills_root)
        if case.get("known"):
            args["known"] = case["known"]
        result = fn(case["stratum"], args)
        report = str(getattr(result, "output", "") or "")
        fixed = {n: t for n, t in case["files"].items() if n not in case.get("editable", [])}
        changed = [n for n, t in fixed.items() if not (root / n).is_file() or (root / n).read_text(encoding="utf-8") != t]
        problems = [f"files changed: {changed}"] if changed else []
        problems += ["the skills folder changed"] if snapshot(skills_root) != skills_before else []
        problems += report_problems(case, report)
        problems += json_problems(root, case["expect_json"]) if case.get("expect_json") else []
        problems += test_problems(root, case)
        met = bool(getattr(result, "met", False))
        ok = met and not problems
        note = "" if ok else (getattr(result, "error", None) or "; ".join(problems) or "the run did not meet the goal")
        row = dict(ok=ok, got=report[:60], note=str(note)[:300])
        for key in ("subagent_calls", "turns"):
            value = getattr(result, key, None)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                row[key] = int(value)
        if case["stratum"] == "small" and row.get("subagent_calls"):
            row["note"] = (row["note"] + "; " if row["note"] else "") + f"{row['subagent_calls']} sub-agent call(s) on a one-file task"
        return row
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(skills_root, ignore_errors=True)
