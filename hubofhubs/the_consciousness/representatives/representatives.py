"""Representatives: each AI representative is one identity, whether it stands for a person or is a character with no person behind it.

The authority is what every handoff carries: ``allow`` (the worker categories the representative may use; none declared means the read-only
ones), ``data_scope`` (whose data it may read: the person it stands for unless declared otherwise, enforced by Body's adapters and by Tools,
and never wider than what the asker may open) and ``ask`` (the asking policy, read by Judgment Calls). A representative that declared nothing
gets the least authority, never another's. A declaration may name the ``person`` it stands for (when absent, a representative id that is a person
id stands for that person) or be a ``character`` with no person. Standard library plus the hub and ``esoi``."""
from typing import Any, Dict, Mapping, Optional

from esoi import implementation

READ_ONLY = ("web-search", "the-science")


def least_authority(person: str) -> Dict[str, Any]:
    return {"allow": list(READ_ONLY), "data_scope": [person] if person else [], "ask": {}}


@implementation("the-representatives", "declared_authority")
class DeclaredAuthority:
    """Each representative is what was declared for it (a mapping of representative id to authority, preferences, quality profile and optionally
    the ``person`` it stands for, or ``character: True`` for one with no person). One with no declaration, or no id at all, gets the least authority
    over the asker's own data only; a character's data scope never reaches past what its asker may open, and with no asker it is empty. A representative with no asker is asked by the person it stands for."""
    REQUIRES = ()     # the declarations are a constructor argument

    def __init__(self, declarations: Optional[Mapping[str, Mapping[str, Any]]] = None):
        self.declarations = dict(declarations or {})

    def represent(self, representative: str = "", person: str = "") -> Mapping[str, Any]:
        declared = self.declarations.get(representative) if representative else None
        stands_for = "" if (declared or {}).get("character") else str((declared or {}).get("person") or representative)
        authority = {**least_authority(stands_for or person), **dict((declared or {}).get("authority") or {})}
        scope = list(authority["data_scope"])
        if stands_for and stands_for not in scope:
            scope = [stands_for, *scope]
        if person and person != stands_for:
            scope = [d for d in scope if d == person]       # what the asker may open is the ceiling
        elif not stands_for:
            scope = []                                      # a character with no asker reaches no one's data (fails closed)
        authority["person"] = stands_for
        authority["data_scope"] = scope
        return {"representative": representative, "person": stands_for, "authority": authority,
                "preferences": dict((declared or {}).get("preferences") or {}), "quality_profile": (declared or {}).get("quality_profile")}
