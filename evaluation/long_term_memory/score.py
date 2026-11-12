"""Scores a Long-Term Memory arm: after retaining dated items for people, does a request recall exactly the right items, in the right order?

The cases are invented and neutral (``build_cases.py``). One number: the share of cases that recall exactly the expected ids in order. No model call, no network."""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from offline import judge  # noqa: E402


def adapt(implementation, meter):
    """Each case gets a fresh arm: a temporary folder for the file arms, a fresh in-memory Card Store for the arm that builds on it."""
    needs_store = "store" in inspect.signature(implementation.__init__).parameters

    def fresh():
        if needs_store:
            from hubofhubs.the_body.internal_context.card_store.cardstore import LocalCardStore
            return implementation(LocalCardStore())
        return implementation()

    def run(kind, args):
        arm = fresh()
        for stored in args["items"]:
            arm.retain({key: stored[key] for key in ("id", "text", "at", "scope_tags") if key in stored}, stored["person"])
        return [found["id"] for found in arm.recall(args["query"], args["person"], args["limit"], args["now"], args.get("scope_tags", []), args.get("scope_mode", "fence"))]
    return run


def score_case(fn, case):
    return judge(fn(case["kind"], case["args"]), case)
