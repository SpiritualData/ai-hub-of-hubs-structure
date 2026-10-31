"""Scores whether a model-call arm still answers when its primary provider fails, with fake providers (no model, no network, no key).

A case names how the primary provider fails (a credit or billing error, a quota or rate limit, a timeout, an outage, or not at all) and
how the secondary one does. The arm is built over a world of two providers, the primary serving ``claude-fake-1`` and the secondary
``gemini-fake-1``, and is asked one question for the primary's model. Result: ``primary`` or ``secondary`` (which provider answered),
or ``error`` (it raised an error with a message, which is the clear failure wanted when no provider is healthy). A silent empty
answer scores as ``silent``. Pass = the result equals the case's ``expect``.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402

PRIMARY_MODEL, SECONDARY_MODEL = "claude-fake-1", "gemini-fake-1"


def make_error(spec):
    """The exception a case describes: ``{"type": "TimeoutError", "message": "..."}``; a builtin type by name, else a new Exception subclass of that name."""
    kind = spec.get("type", "Exception")
    cls = {"TimeoutError": TimeoutError, "ValueError": ValueError}.get(kind) or type(kind, (Exception,), {})
    return cls(spec["message"])


class FakeProvider:
    """Answers ``answered by <name>`` unless its case gave it an error to raise."""

    def __init__(self, name, error=None):
        self.name, self.error, self.calls = name, make_error(error) if error else None, 0
        self.tokens_in = self.tokens_out = 0

    def plan(self, prompt, *, model, tool_schema, layers=None):
        raise AssertionError("the cases ask, they do not plan")

    def answer(self, messages, *, model, system=None, layers=None):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return f"answered by {self.name}"

    def list_models(self):
        return [PRIMARY_MODEL if self.name == "primary" else SECONDARY_MODEL]


def world(args):
    return FakeProvider("primary", args.get("primary")), FakeProvider("secondary", args.get("secondary"))


def ask(arm, args):
    """Ask ``arm.answer`` one question for the primary's model and classify what came back."""
    try:
        text = arm.answer([{"role": "user", "content": "What is 2+2?"}], model=PRIMARY_MODEL)
    except Exception as exc:  # noqa: BLE001 - the failure is the result
        return "error" if str(exc).strip() else "silent"
    return text.removeprefix("answered by ") if text.startswith("answered by ") else "silent"


def adapt(implementation, meter):
    """``implementation`` is the declared router class (``MultiProvider``): it gets both providers and the secondary's model as its only fallback."""
    def run(kind, args):
        primary, secondary = world(args)
        router = implementation(primary, {"anthropic": primary, "gemini": secondary}, fallback_models=(SECONDARY_MODEL,))
        return ask(router, args)
    return run


def score_case(fn, case):
    return judge(fn(case["kind"], case["args"]), case)
