"""Scores an act-in-the-world arm that changes files: the goal is to make a test file pass, and the check is that test file, run afresh.

Each case is one HumanEval problem (MIT). A fresh temporary folder holds ``solution.py`` (the signature and docstring with a ``pass``
body) and ``test_solution.py`` (the benchmark's own tests). The arm gets the goal and the folder as its writable root and nothing else.
Afterwards the test file is rewritten from the case (an arm cannot pass by editing the check) and pytest runs in a new process with a time
limit. Pass = pytest exits 0. The folder is removed after each case.

Arms: ``fast_edit`` (one model call on the cheapest Gemini text model) and the Claude Code CLI runners (the cheapest Claude model,
``haiku``, on the existing subscription). The two groups use different models: a circumstance, stated in README.md.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from priced import first_env, price_of, priced  # noqa: E402

GEMINI_MODEL = "gemini-2.5-flash-lite"
CLAUDE_MODEL = "haiku"
MAX_TURNS = 15            # agent turn limit per goal
AGENT_SECONDS = 240       # wall-clock limit per goal for an agent run
CHECK_SECONDS = 30

GOAL = ("Implement the function `{entry}` in solution.py so that every test in test_solution.py passes. "
        "Edit only solution.py; do not change test_solution.py. Done when `python3 -m pytest -q test_solution.py` passes.")


class SandboxWriter:
    """A FileWriter confined to one folder. Plain files only; the case's own folder is the whole world."""

    def __init__(self, root):
        self.root = Path(root).resolve()

    def resolve(self, rel_path):
        target = (self.root / rel_path).resolve()
        return target if target == self.root or self.root in target.parents else None

    def read_file(self, rel_path):
        target = self.resolve(rel_path)
        try:
            return target.read_text(encoding="utf-8") if target is not None and target.is_file() else None
        except OSError:
            return None

    def write_file(self, rel_path, content):
        from hubofhubs.ports.deep import WriteResult
        target = self.resolve(rel_path)
        if target is None:
            return WriteResult(ok=False, rel_path=rel_path, error="outside the writable root")
        created = not target.exists()
        target.write_text(content, encoding="utf-8")
        return WriteResult(ok=True, rel_path=rel_path, bytes_written=len(content.encode("utf-8")), created=created)


class TierIsModel:
    """The tier registry of the fast edit arm: this evaluation pins the model, so a tier is the model id."""

    def resolve_tier(self, tier):
        return GEMINI_MODEL


def gemini_provider(meter):
    from hubofhubs.models.gemini import GeminiProvider
    provider = priced(GeminiProvider, price_of("gemini", GEMINI_MODEL))(api_key=first_env("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY"))
    meter.model = GEMINI_MODEL
    return meter.wrap(provider, ("answer",))


def agent_config(root):
    from hubofhubs.deep.contract import SubprocessConfig
    from hubofhubs.deep.launch import DeepLaunchSettings
    # No user, project or local settings and no ambient MCP servers, so the run does not depend on this machine's configuration.
    return SubprocessConfig(working_dir=str(root), review_interval_seconds=0, timeout_seconds=AGENT_SECONDS,
                            launch=DeepLaunchSettings(setting_sources="", strict_mcp=True))


def agent_settings():
    """The worker starts from HOME and PATH only (its login lives under HOME); nothing else of this machine's environment reaches it."""
    from hubofhubs.deep.settings import GoalSettings
    env = {name: os.environ[name] for name in ("HOME", "PATH") if name in os.environ}
    return GoalSettings(environment=lambda: dict(env))


def adapt(implementation, meter):
    """``implementation`` is the declared runner class; returns ``run(kind, args) -> DeepResult`` for one case folder."""
    name = implementation.__name__

    def run(kind, args):
        root, goal = args["root"], args["goal"]
        if name == "FastEditRunner":
            runner = implementation(provider=gemini_provider(meter), writer=SandboxWriter(root), registry=TierIsModel())
            return runner.run_goal(goal=goal, brief=goal, model=GEMINI_MODEL)
        meter.model = CLAUDE_MODEL
        runner = implementation(agent_config(root), settings=agent_settings())
        result = runner.run_goal(goal=goal, brief=goal, model=CLAUDE_MODEL, max_turns=MAX_TURNS)
        meter.record()   # one agent session; the CLI does not report its turn count to the runner
        meter.cost_usd += float(getattr(result, "cost_usd", 0.0) or 0.0)   # the CLI's own estimate; the subscription is not charged per call
        return result
    return run


def write_case(root, case):
    (root / "solution.py").write_text(case["stub"], encoding="utf-8")
    write_tests(root, case)


def write_tests(root, case):
    (root / "test_solution.py").write_text(
        "from solution import *  # noqa: F401,F403\n\n" + case["test"] + f"\n\ndef test_solution():\n    check({case['entry_point']})\n",
        encoding="utf-8")


def check(root):
    """pytest in a new process; returns (passed, last output line)."""
    try:
        done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "test_solution.py"], cwd=root,
                              capture_output=True, text=True, timeout=CHECK_SECONDS)
    except subprocess.TimeoutExpired:
        return False, "check timed out"
    lines = [line for line in (done.stdout + done.stderr).strip().splitlines() if line.strip()]
    return done.returncode == 0, (lines[-1] if lines else "no output")[:100]


def score_case(fn, case):
    root = Path(tempfile.mkdtemp(prefix="file_edit_goal_"))
    try:
        write_case(root, case)
        before = (root / "solution.py").read_text(encoding="utf-8")
        result = fn("edit", dict(root=str(root), goal=GOAL.format(entry=case["entry_point"]), case=case))
        write_tests(root, case)   # the check is the case's, not whatever the arm left behind
        ok, last = check(root)
        changed = (root / "solution.py").read_text(encoding="utf-8") != before
        note = "" if ok else (getattr(result, "error", None) or last)
        return dict(ok=ok, got=f"{'edited' if changed else 'unchanged'}; {last}"[:60], note=str(note)[:120])
    finally:
        shutil.rmtree(root, ignore_errors=True)
