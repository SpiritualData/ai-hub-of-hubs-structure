"""Scores a Delegated Agent Sessions arm (a harness, the provider it drives and a tier) on open-ended work of three kinds.

Each case is a small folder of plain files and a goal. A fresh temporary folder holds the files; the arm gets the goal and the folder as
its working directory and nothing else. Every case needs the run to say it met the goal and the files it was not asked to change to be
unchanged; then, by the case's ``stratum``:

* ``report``: the final report holds every expected fact (case-insensitive).
* ``code``: the case's own tests, rewritten by the harness after the run, pass in a new process with a time limit.
* ``deliverable``: the file the goal names exists and meets its rubric (words in range, every required term present as a word, nothing
  forbidden, terms in the stated order).

One number: the share of cases passed, with cost and time folded by ``[balance.agent_sessions]``. An arm is named
``<harness>@provider=<p>,tier=<t>``; the harness gets ``provider`` and ``tier`` as constructor arguments and resolves the tier's model
itself, so no model name is written here. The Claude Code arms run on a subscription: their dollars are the CLI's own estimate at
list price. The other harnesses report their provider's cost, or are priced from the hub's price table.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

MAX_TURNS = 15
AGENT_SECONDS = 300       # wall-clock limit per case for one agent session
CHECK_SECONDS = 60


def agent_config(root):
    from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
    from hubofhubs.the_world.tools.delegated_agent_sessions.launch import DeepLaunchSettings
    # No user, project or local settings and no ambient MCP servers, so a Claude Code run does not depend on this machine's configuration.
    return SubprocessConfig(working_dir=str(root), review_interval_seconds=0, timeout_seconds=AGENT_SECONDS,
                            launch=DeepLaunchSettings(setting_sources="", strict_mcp=True))


def agent_settings(implementation):
    """The worker starts from HOME and PATH, plus the credential variables of the provider the arm names, read from this process."""
    from hubofhubs.the_world.tools.delegated_agent_sessions import providers
    from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings
    provider = (getattr(implementation, "keywords", None) or {}).get("provider", "")
    names = ("HOME", "PATH") + providers.credential_names(provider)
    env = {name: os.environ[name] for name in names if name in os.environ}
    return GoalSettings(environment=lambda: dict(env))


def adapt(implementation, meter):
    """``implementation`` is the declared runner class, or a ``functools.partial`` of it holding the arm's ``provider`` and ``tier``;
    returns ``run(kind, args) -> DeepResult`` for one case folder."""

    def run(kind, args):
        runner = implementation(agent_config(args["root"]), settings=agent_settings(implementation))
        meter.model = getattr(runner, "model", None) or getattr(runner, "tier_model", None) or "default"
        result = runner.run_goal(goal=args["goal"], brief=args["goal"], max_turns=MAX_TURNS)
        meter.record()   # one agent session
        meter.cost_usd += float(getattr(result, "cost_usd", 0.0) or 0.0)
        return result
    return run


def word_in(term, text):
    """Whether ``term`` appears in ``text`` as a whole word or phrase (case-insensitive)."""
    return re.search(r"(?<![\w])" + re.escape(term.lower()) + r"(?![\w])", text.lower()) is not None


def rubric_problems(root, rubric):
    target = root / rubric["file"]
    if not target.is_file():
        return [f"{rubric['file']} was not written"]
    text = target.read_text(encoding="utf-8", errors="replace")
    words = len(text.split())
    problems = []
    if words < rubric.get("min_words", 0) or words > rubric.get("max_words", 10 ** 9):
        problems.append(f"{words} words")
    problems += [f"lacks {t!r}" for t in rubric.get("contains", []) if not word_in(t, text)]
    problems += [f"holds {t!r}" for t in rubric.get("absent", []) if t in text]
    order = rubric.get("order", [])
    found = [re.search(r"(?<![\w])" + re.escape(t) + r"(?![\w])", text.lower()) for t in order]
    if order and all(found) and [m.start() for m in found] != sorted(m.start() for m in found):
        problems.append("not in the stated order")
    return problems


def run_tests(root, tests):
    try:
        done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", *tests], cwd=root,
                              capture_output=True, text=True, timeout=CHECK_SECONDS)
    except subprocess.TimeoutExpired:
        return False, "the tests timed out"
    lines = [line for line in (done.stdout + done.stderr).strip().splitlines() if line.strip()]
    return done.returncode == 0, (lines[-1] if lines else "no output")[:100]


def write_files(root, files):
    for name, text in files.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")


def score_case(fn, case):
    root = Path(tempfile.mkdtemp(prefix="agent_session_"))
    try:
        write_files(root, case["files"])
        write_files(root, case.get("tests", {}))
        result = fn(case.get("stratum", "report"), dict(root=str(root), goal=case["goal"]))
        report = str(getattr(result, "output", "") or "")
        fixed = {n: t for n, t in case["files"].items() if n not in case.get("editable", [])}
        changed = [n for n, t in fixed.items() if not (root / n).is_file() or (root / n).read_text(encoding="utf-8") != t]
        problems = []
        if case.get("stratum") == "code":
            write_files(root, case["tests"])   # the check is the case's, not whatever the arm left behind
            ok, last = run_tests(root, sorted(case["tests"]))
            problems += [] if ok else [f"tests fail: {last}"]
        elif case.get("rubric"):
            problems += rubric_problems(root, case["rubric"])
        missing = [fact for fact in case["expect"] if fact.lower() not in report.lower()]
        problems += [f"the report lacks {missing}"] if missing else []
        problems += [f"files changed: {changed}"] if changed else []
        met = bool(getattr(result, "met", False))
        ok = met and not problems
        note = "" if ok else (getattr(result, "error", None) or "; ".join(problems) or "the run did not meet the goal")
        return dict(ok=ok, got=report[:60], note=str(note)[:160])
    finally:
        shutil.rmtree(root, ignore_errors=True)
