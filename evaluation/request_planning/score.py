"""Scores a Planner arm: for a request taken from another seat's own case set, does the first piece name the worker that seat uses (or none)?

One component, one number: the share of requests routed to the right worker. The kinds are web-search questions, literature questions, coding goals, requests that
need no context and one two-step request whose pieces must each get the right worker. The rule arms make no model call; the model planner (a paid arm) is
built with the cheapest Gemini model and runs only when asked with ``--max-calls``."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402
from priced import first_env, price_of, priced  # noqa: E402,F401


MODEL = "gemini-2.5-flash-lite"


class Plumbing:
    """Model Plumbing for this component: one question to the cheapest Gemini model, counted by the meter and priced from the registry."""

    def __init__(self, meter):
        from priced import first_env, price_of, priced
        from hubofhubs.the_world.model_plumbing.vendor_model_caller.gemini import GeminiProvider
        self.provider = meter.wrap(priced(GeminiProvider, price_of("gemini", MODEL))(api_key=first_env("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY")),
                                   ("answer",))
        meter.model = MODEL

    def ask(self, prompt, tier=""):
        return self.provider.answer([{"role": "user", "content": prompt}], model=MODEL)


def adapt(implementation, meter):
    import inspect
    arm = implementation(plumbing=Plumbing(meter)) if "plumbing" in inspect.signature(implementation).parameters else implementation()

    def run(kind, args):
        pieces = arm.plan(args["request"])
        tools = [str(p.get("tool", "")) for p in pieces]
        return tools if kind == "steps" else (tools[0] if tools else None)
    return run


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    out = {}
    for kind in sorted({r.get("kind") for r in rows} - {None}):
        mine = [r for r in rows if r.get("kind") == kind]
        out[f"{kind}_passed"] = f"{sum(bool(r['ok']) for r in mine)}/{len(mine)}"
    return out
