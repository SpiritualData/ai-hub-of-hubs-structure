"""Scores a Decision Check arm: is the checked decision right, and what did it cost?

A ``pick`` case is right when the arm's pick is the option the evidence supports (or an abstain where the evidence decides nothing); a ``reply`` case is right when every span the case lists in
``remove`` is gone from the checked reply and every span in ``keep`` is still there. One number: the share of cases decided right. Beside it: ``wrong`` (a pick that is not the expected one, which
excludes an abstain), the calls per decision and the share of decisions whose opinions agreed. The floor makes no call. The model-calling arms ask the ``cheap`` tier through Model Plumbing
(the tier chooser picks the model; this file names none) and run only when asked with ``--max-calls``."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class Plumbing:
    """Model Plumbing for this component: one question at the cheap tier, counted by the meter."""

    def __init__(self, meter):
        import hubofhubs.api as hub
        from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
        self.hub, self.options, self.meter = hub, {"vendor-model-caller": {"primary": ClaudeCliProvider()}}, meter

    def ask(self, prompt, tier=""):
        return self.hub.run("model-plumbing", {"prompt": prompt, "tier": tier or "cheap"}, options=self.options)


def adapt(implementation, meter):
    import inspect
    arm = implementation(plumbing=Plumbing(meter)) if "plumbing" in inspect.signature(implementation).parameters else implementation()
    return lambda kind, args: dict(arm.check(args["draft"], args["binding"]))


def right(got, case):
    if case["kind"] == "pick":
        return got.get("pick", "") == case["expect"]
    text = got.get("text", "")
    return all(s not in text for s in case["expect"]["remove"]) and all(s in text for s in case["expect"]["keep"])


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    ok = right(got, case)
    return dict(ok=ok, kind=case["kind"], used=got.get("calls", 0), agreement=got.get("agreement", 0.0), outcome=got.get("outcome", ""),
                wrong=bool(case["kind"] == "pick" and not ok and got.get("pick", "") != ""),
                got=str(got.get("pick", got.get("text", "")))[:60], note="" if ok else f"expected {case['expect']!r}; {got.get('outcome')}: {got.get('why')}"[:160])


def aggregate(rows):
    out = {f"{kind}_passed": f"{sum(bool(r['ok']) for r in rows if r.get('kind') == kind)}/{sum(1 for r in rows if r.get('kind') == kind)}" for kind in sorted({r.get("kind") for r in rows} - {None})}
    out["wrong_picks"] = sum(bool(r.get("wrong")) for r in rows)
    out["calls_per_decision"] = round(sum(r.get("used", 0) for r in rows) / max(1, len(rows)), 2)
    out["agreement"] = round(sum(r.get("agreement", 0.0) for r in rows) / max(1, len(rows)), 3)
    return out
