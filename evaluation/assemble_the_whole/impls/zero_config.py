"""The hub's own one-line assembly, scored as the whole: for each seat, is it built, or does its pending line name exactly what to pass."""
import csv
import re
import sys
from pathlib import Path

from esoi.entry import Pending

import hubofhubs

PASS = re.compile(r"pass (arms|options|provided)=\{|\bset [A-Z][A-Z0-9_]+(?: or [A-Z][A-Z0-9_]+)*(?: \(|$)|: pip install '|: cannot be loaded \(")
NEEDS = re.compile(r"needs ([a-z0-9-]+(?:, [a-z0-9-]+)*); see those lines")


def state(system, seat):
    """``built``, ``pending: exact`` (the line says what to pass, or points at seats whose lines do) or ``pending: vague``."""
    if seat in system:
        return "built"
    line = system.pending.get(seat, "")
    if PASS.search(line):
        return "pending: exact"
    found = NEEDS.search(line)
    if found and all(state(system, other) != "pending: vague" for other in found.group(1).split(", ")):
        return "pending: exact"
    return "pending: vague"


def build(meter):
    def run(kind, args):
        if kind in ("needs", "run"):
            return one_line(kind, args)
        system = hubofhubs.assemble(arms=args.get("arms"), options=args.get("options"), environ=args.get("environ", {}))
        if kind == "variable":
            if args["seat"] in system:
                return "built"
            return "pending names " + ",".join(v for v in args["variables"] if v in system.pending.get(args["seat"], ""))
        found = state(system, args["seat"])
        return "ok" if found in ("built", "pending: exact") else found
    return run


class StubModel:
    """A model provider that is never asked: it lets a seat that needs one build."""
    tokens_in = tokens_out = 0

    def answer(self, messages, *, model=None, system=None, layers=None):
        return ""

    def list_models(self):
        return []

    def plan(self, *a, **k):
        raise NotImplementedError

    def supports_web_search(self, model=None):
        return False

    def web_search(self, *a, **k):
        raise NotImplementedError


def one_line(kind, args):
    """The one function: what ``needs`` reports for an id, and a real zero-configuration ``run``. No model call."""
    provided = {"call-a-model": StubModel()} if args.get("provided_model") else None
    if kind == "needs":
        lines = hubofhubs.needs(args["seat"], arms=args.get("arms"), provided=provided, environ=args.get("environ", {}))
        names = sorted(set(re.findall(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]*KEY\b", " ".join(lines))))
        return "needs " + names[0] if names else ("ready" if not lines else "needs: " + "; ".join(lines))
    try:
        result = hubofhubs.run(args["seat"], args["input"], provided=provided, environ=args.get("environ", {}))
    except Pending as error:
        names = re.findall(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]*KEY\b", str(error))
        return f"raised Pending naming {names[0]}" if names else "raised Pending"
    if isinstance(result, hubofhubs.Result):
        return f"answer {result.answer!r} with {len(result.items)} items, {len(result.events)} events"
    return f"{len(result)} cards"
