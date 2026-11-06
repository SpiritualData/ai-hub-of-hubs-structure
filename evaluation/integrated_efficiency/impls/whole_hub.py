"""The assembled whole run on a request as one assistant: ``hubofhubs.run("the-self", ...)`` with the environment the run is given. A run needs the keys the seats
it uses declare (``hubofhubs.needs``); without them a request comes back as a stated failure, which the score counts as not completed and honest."""
import os

import hubofhubs


def build(meter):
    def run(kind, args):
        environ = dict(os.environ) if os.environ.get("HUB_WHOLE_LIVE") else {}
        result = hubofhubs.run("the-self", {"request": args["request"], "person": args.get("person", "")}, environ=environ)
        steps = [dict(s) for s in (result.steps or ())]
        return {"answer": result.answer, "note": result.note, "steps": steps, "calls": int((result.tokens or {}).get("calls", 0))}
    return run
