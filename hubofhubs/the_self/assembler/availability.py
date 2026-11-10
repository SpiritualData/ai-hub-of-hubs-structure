"""Availability: when the selected arm of a solution cannot run on this machine, the best-measured arm that can stands in.

A selected arm may need a library that is not installed, a key that is not in the environment mapping, a program that is not on its path or an
option nobody passed. Each arm declares these (``REQUIRES``, ``ENVIRON``, its constructor), and esoi checks them against the mapping the caller
gave. Where one is unmet, this module walks the solution's arms in the order they were measured (``hubofhubs/arm_order.json``, written by
``scripts/sync_arm_order.py`` from the leaderboard) and takes the first whose needs are met. Availability chooses among measured arms and never by
preference; an arm the caller named is never replaced; a solution no arm can serve is left as it was, so it is reported as a pending step.
Reads no environment: the mapping is an argument. Standard library plus the hub and ``esoi``."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

from esoi import AssemblyConfig, AssemblyError
from esoi.runtime.assemble_by_name.environ_options import environ_lacking
from esoi.runtime.assemble_by_name.seat_blockers import lacks_option, unmet_checks

ORDER_FILE = Path(__file__).resolve().parents[2] / "arm_order.json"


@dataclass(frozen=True)
class StandIn:
    """One solution whose selected arm could not run here and the arm that did the job instead, with the plain reason."""
    solution: str
    selected: str
    arm: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {"solution": self.solution, "selected": self.selected, "arm": self.arm, "reason": self.reason}

    def __str__(self) -> str:
        return f"{self.solution}: {self.arm} stood in for {self.selected} ({self.reason})"


def arm_order() -> Mapping[str, List[str]]:
    """``{solution id: arm names, best-measured first}`` as packaged; a solution with one arm is not listed."""
    try:
        return json.loads(ORDER_FILE.read_text())
    except (OSError, ValueError):
        return {}


def unmet(hub: Any, solution: str, arm: str, environ: Mapping[str, str], options: Mapping[str, Any]) -> str:
    """Why ``arm`` of ``solution`` cannot run here (one plain clause), or an empty string when it can."""
    try:
        target = hub.load(solution, arm)
        needs = hub.needs_of(target)
    except (AssemblyError, TypeError, ImportError) as error:
        return f"it cannot be loaded ({type(error).__name__})"
    lacking = environ_lacking(target, options, environ)
    if lacking:
        return "needs " + " or ".join(name for names in lacking.values() for name in names)
    found = unmet_checks(target, environ, options)
    if found:
        return "; ".join(dict.fromkeys(one.remedy for one in found if one.remedy)) or "a requirement is unmet"
    if lacks_option(target, needs, options):
        return "it needs an object only a consumer can pass"
    return ""


def stand_ins(hub: Any, environ: Mapping[str, str], arms: Optional[Mapping[str, str]] = None, options: Optional[Mapping[str, Any]] = None,
              lock: Any = None) -> Tuple[Dict[str, str], Tuple[StandIn, ...]]:
    """``(arms to use, what stood in)``: ``arms`` with, for every solution whose selected arm cannot run with ``environ`` and ``options``, the best-measured
    arm that can. An arm the caller named in ``arms`` stays; a solution with no arm that can run keeps its selected arm."""
    chosen: Dict[str, str] = dict(arms or {})
    given = dict(options or {})
    config = AssemblyConfig(selections=dict(chosen), options=given, consumer_environ=dict(environ), lock=lock)
    order = arm_order()
    found: List[StandIn] = []
    for solution in hub.visible():
        if solution in chosen or solution not in order:
            continue
        try:
            picked = hub.pick(solution, None, config)
        except AssemblyError:
            continue
        if picked is None:
            continue
        base = picked.name.split("@", 1)[0]
        why = unmet(hub, solution, base, environ, given.get(solution, {}))
        if not why:
            continue
        names = set(hub.names(solution))
        for name in order[solution]:
            if name != base and name in names and not unmet(hub, solution, name, environ, given.get(solution, {})):
                chosen[solution] = name
                found.append(StandIn(solution, base, name, why))
                break
    return chosen, tuple(found)
