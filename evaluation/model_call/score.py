"""Scores a model-call arm against its adapter contract, with a recording stand-in for the call-a-model provider (no model, no network)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


class Recorder:
    """A provider that records the one call it receives and answers with fixed text, or raises."""

    def __init__(self, reply="ok", fail=False):
        self.reply, self.fail, self.calls = reply, fail, []

    def answer(self, messages, *, model, system=None, layers=None):
        self.calls.append((messages, model, system))
        if self.fail:
            raise RuntimeError("provider down")
        return self.reply

    def plan(self, prompt, *, model, tool_schema, layers=None):
        raise AssertionError("complete must not plan")

    def list_models(self):
        return []


def adapt(implementation, meter):
    def run(kind, args):
        provider = Recorder(args.get("reply", "ok"), args.get("fail", False))
        arm = implementation(provider, **args.get("build", {}))
        try:
            text = arm.complete(args["prompt"], *args.get("tier", ()))
            outcome = text
        except Exception as exc:
            outcome = type(exc).__name__
        calls = [[m, model, system] for m, model, system in provider.calls]
        return [outcome, calls]
    return run


def score_case(fn, case):
    return judge(fn(case["kind"], case["args"]), case)
