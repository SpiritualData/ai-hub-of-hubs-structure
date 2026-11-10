"""Scores a Command Execution arm: do commands that must run run, does the floor refuse what it must, does confinement contain writes outside the folder, and
does a scratch folder last the session? One number: the share of cases whose conditions all hold (see ``build_cases.py``). The case's commands run in a new
temporary folder with a sibling folder the run must not touch. No model call.

What it cannot see: network confinement, reads of files outside the folder (the sandbox leaves the disk readable), resource limits (memory, processes) and
escapes a determined program could find; the cases are written, not taken from a real run."""
import shutil
import tempfile
import time
from pathlib import Path


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        base = Path(tempfile.mkdtemp(prefix="command_execution_"))
        root, outside, scratch = base / "work", base / "outside", base / "scratch"
        for folder in (root, outside, scratch):
            folder.mkdir()
        try:
            marks = {"root": str(root), "outside": str(outside), "scratch": str(scratch)}
            done, started = None, time.monotonic()
            for step in args["steps"]:
                command = step
                for name, value in marks.items():
                    command = command.replace("{" + name + "}", value)
                done = arm.run(command, str(root), timeout=float(args.get("timeout", 20)), scratch=str(scratch), limit=4000)
            return dict(output=done.output, code=done.code, refused=bool(done.refused), timed_out=bool(done.timed_out), seconds=time.monotonic() - started,
                        present=sorted(str(p) for p in base.rglob("*") if p.is_file()))
        finally:
            shutil.rmtree(base, ignore_errors=True)
            Path("/tmp/session_note.txt").unlink(missing_ok=True)
    return run


def score_case(fn, case):
    # the case's own timeout is a parameter of the run, so it travels in the args
    args = dict(case["args"], **({"timeout": case["expect"]["timeout"]} if "timeout" in case["expect"] else {}))
    got = fn(case["kind"], args)
    want = case["expect"]
    problems = []
    present = got["present"]
    if "output_has" in want and want["output_has"] not in got["output"]:
        problems.append("output lacks " + want["output_has"])
    if "output_under" in want and len(got["output"]) > want["output_under"]:
        problems.append("output not bounded")
    if "code" in want and got["code"] != want["code"]:
        problems.append(f"exit {got['code']}")
    if "refused" in want and got["refused"] != want["refused"]:
        problems.append("refusal differs")
    if "timed_out" in want and got["timed_out"] != want["timed_out"]:
        problems.append("timeout differs")
    if "seconds_under" in want and got["seconds"] > want["seconds_under"]:
        problems.append("too slow")
    for name in want.get("files_present", []):
        if not any(p.endswith(name.split("}", 1)[-1]) and "/work/" in p for p in present):
            problems.append("missing " + name)
    for name in want.get("files_absent", []):
        if any(p.endswith(name.split("}", 1)[-1]) and "/outside/" in p for p in present):
            problems.append("written outside: " + name)
    return dict(ok=not problems, kind=case["kind"], got=got["output"][:40].replace("\n", " "), note="; ".join(problems))


def aggregate(rows):
    return {f"{k}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == k)}/{sum(r.get('kind') == k for r in rows)}"
            for k in ("runs", "bounded", "refused", "contained", "scratch")}
