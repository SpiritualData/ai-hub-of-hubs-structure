"""The tier each model call role runs on: one table, ``role_tiers.csv`` beside this file, that the code reads.

A call names its ROLE (``tier_for("request_classification")``) and the table gives the tier; no call site names a tier of its own and no code names a
model. Tier names are the hub's four, the same as its main consumer's: ``fast``, ``balanced``, ``quality`` and ``best``. ``strong`` stays readable as an
alias of ``quality`` (here, in ``ALIASES``, and nowhere else), and the older chooser names ``cheap`` and ``mid`` read as ``fast`` and ``balanced``.
The chooser measures three tiers (cheap, mid, strong): ``quality`` is its strong arm and ``best`` is that same arm until an arm is measured for ``best``;
``resolution_note`` says so, so nothing claims a model it did not run. A person's explicit tier wins for a role whose ``person_may_set`` is ``yes``; a role
whose tier is the name of another role follows it. ``best`` is reached only by a person's explicit tier or by the role ``structure-watch`` (``BEST_ROLE``), which another part of the hub builds. The ``evidence`` cell says ``measured: ...`` with the case, or ``owner's policy, unmeasured``.
Standard library only; the table path is an argument, nothing is read from the environment."""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Mapping, Optional

TABLE = Path(__file__).with_name("role_tiers.csv")
TIERS = ("fast", "balanced", "quality", "best")
ALIASES = {"strong": "quality", "cheap": "fast", "mid": "balanced", "science": "fast"}     # science is a call role, not a tier: it reads as fast
CHOOSER_TIER = {"fast": "cheap", "balanced": "mid", "quality": "strong", "best": "strong"}
MEASURED_TIERS = ("fast", "balanced", "quality")
BEST_ROLE = "structure-watch"


def normalise(tier: str) -> str:
    """The hub's name for a tier, aliases resolved (``strong`` is ``quality``); an unknown name is returned as given, lower case."""
    name = (tier or "").strip().lower()
    return ALIASES.get(name, name)


def chooser_tier(tier: str) -> str:
    """The tier the model tier chooser measures for ``tier``."""
    return CHOOSER_TIER.get(normalise(tier), normalise(tier))


def resolution_note(tier: str) -> str:
    """What to say when the tier does not have an arm measured for itself, else an empty string."""
    if normalise(tier) == "best":
        return "no arm is measured for the best tier: it runs on the strongest measured arm (the quality tier's)"
    return ""


def read_table(path: Path = TABLE) -> Dict[str, Dict[str, str]]:
    """``{role: row}`` of the table."""
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return {row["role"]: row for row in csv.DictReader(handle)}


def tier_for(role: str, requested: str = "", table: Optional[Mapping[str, Mapping[str, str]]] = None) -> str:
    """The tier of ``role``. ``requested`` (a person's explicit tier) wins when the role lets a person set it; a role that names another role follows it.
    Raises ``KeyError`` for a role the table does not hold, so a typo fails where it is written."""
    rows = table if table is not None else read_table()
    seen = []
    while True:
        if role not in rows:
            raise KeyError(f"no tier policy for the role {role!r}; roles: {', '.join(sorted(rows))}")
        if role in seen:
            raise ValueError(f"the tier policy of {role!r} follows itself")
        seen.append(role)
        row = rows[role]
        if requested and (row.get("person_may_set") or "").strip().lower() == "yes":
            return normalise(requested)
        tier = normalise(row.get("tier") or "")
        if tier in TIERS:
            return tier
        role = tier
