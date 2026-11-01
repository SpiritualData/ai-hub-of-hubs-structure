"""The hub's own one-line assembly, scored as the whole: for each seat, is it built, or does its pending line name exactly what to pass."""
import csv
import re
import sys
from pathlib import Path

import hubofhubs
import hubofhubs.oneline

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
        if kind in ("needs", "alias", "run"):
            return one_line(kind, args)
        system = hubofhubs.assemble(arms=args.get("arms"), options=args.get("options"), environ=args.get("environ", {}))
        if kind == "variable":
            if args["seat"] in system:
                return "built"
            return "pending names " + ",".join(v for v in args["variables"] if v in system.pending.get(args["seat"], ""))
        found = state(system, args["seat"])
        return "ok" if found in ("built", "pending: exact") else found
    return run


def one_line(kind, args):
    """The one-line functions: what ``needs`` reports, which seat an alias names, and a real zero-config run. No model call."""
    if kind == "alias":
        try:
            return hubofhubs.oneline.seat_of(args["seat"])
        except ValueError:
            return "refused"
    if kind == "needs":
        lines = hubofhubs.needs(args["seat"], arms=args.get("arms"), environ=args.get("environ", {}))
        names = sorted(set(re.findall(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]*KEY\b", " ".join(lines))))
        return "needs " + names[0] if names else ("ready" if not lines else "needs: " + "; ".join(lines))
    try:
        result = hubofhubs.run(args["input"], args["seat"], environ=args.get("environ", {}))
    except hubofhubs.Needs as error:
        names = re.findall(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]*KEY\b", str(error))
        return f"raised Needs naming {names[0]}" if names else "raised Needs"
    return f"answer {result.answer!r} with {len(result.items)} items, {len(result.events)} events"
