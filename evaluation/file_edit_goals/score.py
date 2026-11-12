"""Scores an file-editing or delegated-agent-sessions arm that changes files: the goal is to make a test file pass, and the check is that test file, run afresh.

Each case is one HumanEval problem (MIT). A fresh temporary folder holds ``solution.py`` (the signature and docstring with a ``pass``
body) and ``test_solution.py`` (the benchmark's own tests). The arm gets the goal and the folder as its writable root and nothing else.
Afterwards the test file is rewritten from the case (an arm cannot pass by editing the check) and pytest runs in a new process with a time
limit. Pass = pytest exits 0. The folder is removed after each case.

Arm: ``fast_edit`` (one model call through the Claude CLI provider on the operator's subscription login; ``impls/fast_edit.py``). The model of
``fast_edit`` is never named here: it is the model the tier chooser names for the tier (``FILE_EDIT_TIER``, default ``fast``; ``fast_edit@tier=balanced`` and ``fast_edit@tier=quality`` record the other tiers), resolved on the day of the run.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

TIER_VARIABLE = "FILE_EDIT_TIER"   # the tier the fast_edit arm runs on when the arm name does not say; fast, balanced or quality
TIERS = ("fast", "balanced", "quality")
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
        from hubofhubs.the_world.tools.deep import WriteResult
        target = self.resolve(rel_path)
        if target is None:
            return WriteResult(ok=False, rel_path=rel_path, error="outside the writable root")
        created = not target.exists()
        target.write_text(content, encoding="utf-8")
        return WriteResult(ok=True, rel_path=rel_path, bytes_written=len(content.encode("utf-8")), created=created)


class DayChooser:
    """The model tier chooser's answer for the day of the run, in the shape ``TierRegistry`` reads (``choose()``)."""

    def choose(self):
        import datetime
        from hubofhubs.the_world.model_plumbing.model_tier_chooser import tiers
        return tiers.choose(today=datetime.date.today().isoformat())


def tier_of(param=None, environ=None):
    """The tier of a ``fast_edit`` run: the arm name's ``tier`` parameter, else ``FILE_EDIT_TIER``, else ``fast``. A run on a tier other than fast must say so in
    the arm name (``fast_edit@tier=balanced``), because the arm name is what the results row and the role tier table match on."""
    from esoi import RunError
    environ = os.environ if environ is None else environ
    given = (environ.get(TIER_VARIABLE) or "").strip().lower()
    tier = param or given or "fast"
    if tier not in TIERS or (param == "fast"):
        raise RunError(f"the tier is one of {', '.join(TIERS)} ({TIER_VARIABLE}), and fast is the arm fast_edit with no parameter; got {tier!r} from {'the arm name' if param else TIER_VARIABLE}")
    if not param and tier != "fast":
        raise RunError(f"{TIER_VARIABLE}={tier} must also be in the arm name, so the record carries it: --impl fast_edit@tier={tier}")
    return tier


def claude_provider(meter, tier):
    """The Claude CLI provider (subscription login, no key) and the model the tier chooser names for ``tier`` today; ``meter.model`` is that model."""
    from esoi import RunError
    from hubofhubs.the_world.model_plumbing.model_tier_chooser.tier_registry import TierRegistry
    from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
    chosen = (DayChooser().choose().get(tier) or {}).get("arm")
    if not chosen or chosen[0] != "anthropic":
        raise RunError(f"the {tier} tier names {chosen!r} today, not an Anthropic model, so the Claude CLI cannot run it")
    model = TierRegistry(DayChooser()).resolve_tier(tier)
    meter.model = model
    provider = ClaudeCliProvider(claude_path="claude", timeout_seconds=300, environment={k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"})
    return meter.wrap(provider, ("answer",)), model


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
