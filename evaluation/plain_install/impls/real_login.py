"""The front door on a plain install with the real Claude CLI: the same run as ``front_door`` with the program on the PATH of the person's own environment, no vendor key in the mapping,
so every model call and web search is a real one on the subscription login. It spends the login's allowance (a few calls per case), so a person authorizes the run."""
import os
import tempfile
from pathlib import Path

import hubofhubs

from evaluation.plain_install.impls.front_door import steps_of

PAID = True


def build(meter):
    def run(kind, args):
        with tempfile.TemporaryDirectory() as scratch:
            work = Path(scratch)
            for name, text in (args.get("files") or {}).items():
                (work / name).write_text(text)
            before = Path.cwd()
            os.chdir(work)
            try:
                result = hubofhubs.run("the-self", {"request": args["request"], "person": ""}, environ={"PATH": os.environ.get("PATH", "")})
            finally:
                os.chdir(before)
        steps = list(steps_of(result.steps))
        return {"answer": result.answer, "note": result.note, "steps": steps, "stood_in": list(result.stood_in),
                "broken": [s for s in steps if s.get("status") == "unavailable" and s.get("depends") != "supporting"]}
    return run
