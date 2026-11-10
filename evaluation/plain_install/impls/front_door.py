"""The front door on a plain install: ``hubofhubs.run("the-self", ...)`` with an empty environment mapping that holds only a PATH with the Claude CLI on it (a stand-in
program that answers the way the real one's JSON envelope does), run from a folder that holds the case's files. Nothing else is faked: no vendor key, no search service,
the hub's own selection and its stand-in of arms that cannot run here."""
import os
import tempfile
from pathlib import Path

import hubofhubs

from evaluation.plain_install import fake_claude


def steps_of(rows):
    for row in rows or ():
        yield row
        yield from steps_of(row.get("steps"))


def build(meter):
    def run(kind, args):
        with tempfile.TemporaryDirectory() as scratch:
            base = Path(scratch)
            bindir = fake_claude.install(base / "bin")
            work = base / "work"
            work.mkdir()
            for name, text in (args.get("files") or {}).items():
                (work / name).write_text(text)
            before = Path.cwd(), os.environ.get("PATH")
            os.chdir(work)
            os.environ["PATH"] = str(bindir)      # the process the stand-in program is started from; the hub reads it through the mapping below
            try:
                result = hubofhubs.run("the-self", {"request": args["request"], "person": ""}, environ={"PATH": str(bindir)})
            finally:
                os.chdir(before[0])
                os.environ["PATH"] = before[1] or ""
        steps = list(steps_of(result.steps))
        return {"answer": result.answer, "note": result.note, "steps": steps, "stood_in": list(result.stood_in),
                "broken": [s for s in steps if s.get("status") == "unavailable" and s.get("depends") != "supporting"]}
    return run
