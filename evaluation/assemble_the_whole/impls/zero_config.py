"""The hub's own one-line assembly, scored as the whole: for each seat, is it built, or does its pending line name exactly what to pass."""
import csv
import re
import sys
from pathlib import Path

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
        system = hubofhubs.assemble(arms=args.get("arms"), options=args.get("options"), environ=args.get("environ"))
        if kind == "variable":
            if args["seat"] in system:
                return "built"
            return "pending names " + ",".join(v for v in args["variables"] if v in system.pending.get(args["seat"], ""))
        found = state(system, args["seat"])
        return "ok" if found in ("built", "pending: exact") else found
    return run
