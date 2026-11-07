"""Scores a Resolve a Reference arm: for a phrase and its candidates, does the arm name the candidate the case expects, or abstain where the case expects no match?

One number: the share of cases settled correctly. Beside it, ``wrong_match`` counts the cases where the arm named a candidate that was not the right one (including any match where
abstaining was right): the harm this seat exists to prevent, an owner or a goal overwritten because words were shared. The model-free arms make no call. The model-judged arm (a paid arm) is built
with the cheapest Gemini model and runs only when asked with ``--max-calls``."""
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
    arm = implementation(plumbing=Plumbing(meter)) if "plumbing" in inspect.signature(implementation).parameters else implementation()
    return lambda kind, args: arm.resolve(args["phrase"], args["candidates"])["id"]


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    row = judge(got, case)
    return dict(row, kind=case["kind"], wrong_match=bool(not row["ok"] and str(got or "")))


def aggregate(rows):
    out = {f"{kind}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == kind)}/{sum(1 for r in rows if r.get('kind') == kind)}"
           for kind in sorted({r.get("kind") for r in rows} - {None})}
    out["wrong_match"] = sum(bool(r.get("wrong_match")) for r in rows)
    return out
