"""Scores a Route a Request arm: for a request (and the view the Mind already has), does the arm say the route the case expects (information, act, draft or clarify)?

One number: the share of requests routed correctly, with the share per route beside it. The model-free arms make no call: ``majority_floor`` and ``plan_derived`` over the hub's rule
Planner. The single classifier (a paid arm) is built with the cheapest Gemini model and runs only when asked with ``--max-calls``."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402
from priced import first_env, price_of, priced  # noqa: E402,F401


MODEL = "gemini-2.5-flash-lite"


class Plumbing:
    """Model Plumbing for this component: one question to the cheapest Gemini model, counted by the meter and priced from the registry."""

    def __init__(self, meter):
        from hubofhubs.the_world.model_plumbing.vendor_model_caller.gemini import GeminiProvider
        self.provider = meter.wrap(priced(GeminiProvider, price_of("gemini", MODEL))(api_key=first_env("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY")),
                                   ("answer",))
        meter.model = MODEL

    def ask(self, prompt, tier=""):
        return self.provider.answer([{"role": "user", "content": prompt}], model=MODEL)


def adapt(implementation, meter):
    import inspect
    from hubofhubs.the_intelligence.mind.planner.planning import CueRouter
    parameters = inspect.signature(implementation).parameters
    arm = implementation(plumbing=Plumbing(meter)) if "plumbing" in parameters else implementation(planner=CueRouter()) if "planner" in parameters else implementation()
    return lambda kind, args: arm.route(args["request"], args.get("context") or None)["route"]


def score_case(fn, case):
    return dict(judge(fn(case["kind"], case["args"]), case), kind=case["kind"])


def aggregate(rows):
    out = {}
    for kind in sorted({r.get("kind") for r in rows} - {None}):
        mine = [r for r in rows if r.get("kind") == kind]
        out[f"{kind}_passed"] = f"{sum(bool(r['ok']) for r in mine)}/{len(mine)}"
    return out
