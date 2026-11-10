"""Scores an Agent Action Format arm: scripted replies in each format over a temporary folder; the share whose intended actions were all executed with the
effect the case states (files and their text, how many actions ran, how many were refused, nothing written outside the folder). One number: the share of
cases passed, reported per format. No model call. An arm passes only the formats it reads; a reader of one family fails the others, so the number rewards a
harness that can take what the model it drives emits.

What it cannot see: what a real model emits (the replies are written from real failure shapes, not sampled), a tool that takes a long time, and the native
loop of a provider's own agent (it executes its own tool calls and cannot be scripted offline: its share is a paid measure, the tasks of Delegated Agent
Sessions)."""
import shutil
import tempfile
from pathlib import Path


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        base = Path(tempfile.mkdtemp(prefix="action_format_"))
        root = base / "work"
        root.mkdir()
        try:
            for name, text in args["files"].items():
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text(text)
            outcomes = arm.execute(args["reply"], str(root))
            files = {str(p.relative_to(root)): p.read_text(errors="replace") for p in root.rglob("*") if p.is_file()}
            return dict(outcomes=outcomes, files=files, escaped=sorted(str(p.name) for p in base.iterdir() if p.name != "work"))
        finally:
            shutil.rmtree(base, ignore_errors=True)
    return run


def score_case(fn, case):
    got = fn(case["format"], case["args"])
    want, problems = case["expect"], []
    for name, text in want.get("has", {}).items():
        if text.strip() not in got["files"].get(name, "").strip():
            problems.append(f"{name} lacks the text")
    for name in want.get("absent", []):
        if name.lstrip("./") in got["files"] or got["escaped"]:
            problems.append(f"{name} was written")
    if "ran" in want and len(got["outcomes"]) != want["ran"]:
        problems.append(f"{len(got['outcomes'])} actions ran, expected {want['ran']}")
    if "failed" in want and sum(not o["ok"] for o in got["outcomes"]) != want["failed"]:
        problems.append("refusals differ")
    if "failed" not in want and any(not o["ok"] for o in got["outcomes"]):
        problems.append("an action failed")
    return dict(ok=not problems, kind=case["format"], got=f"{len(got['outcomes'])} actions", note="; ".join(problems))


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}"
            for k in ("protocol", "function-markup", "json-tool-call", "native-tool-calls")}
