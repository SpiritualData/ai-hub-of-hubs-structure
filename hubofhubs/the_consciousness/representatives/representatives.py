"""Representatives: the AI persona that acts for one person, with the person's authority, preferences and quality profile.

The authority is what every handoff carries: ``allow`` (the worker categories the person lets the AI use; none declared means the read-only
ones), ``data_scope`` (whose data the AI may read: the person's own unless declared otherwise, enforced by Body's adapters and by Tools)
and ``ask`` (the person's own asking policy, read by Judgment Calls). A person who declared nothing gets the least authority, never another
person's. Standard library plus the hub and ``esoi``."""
from typing import Any, Dict, Mapping, Optional

from esoi import implementation

READ_ONLY = ("web-search", "the-science")


def least_authority(person: str) -> Dict[str, Any]:
    return {"allow": list(READ_ONLY), "data_scope": [person] if person else [], "ask": {}}


@implementation("the-representatives", "declared_authority")
class DeclaredAuthority:
    """Each person's representative is what that person declared (a mapping of person to authority, preferences and quality profile); a
    person with no declaration, or no person at all, gets the least authority over their own data only."""
    REQUIRES = ()     # the declarations are a constructor argument

    def __init__(self, declarations: Optional[Mapping[str, Mapping[str, Any]]] = None):
        self.declarations = dict(declarations or {})

    def represent(self, person: str = "") -> Mapping[str, Any]:
        declared = self.declarations.get(person) if person else None
        authority = {**least_authority(person), **dict((declared or {}).get("authority") or {})}
        authority["person"] = person
        authority["data_scope"] = list(authority["data_scope"]) if person in authority["data_scope"] or not person else [person, *authority["data_scope"]]
        return {"person": person, "authority": authority, "preferences": dict((declared or {}).get("preferences") or {}),
                "quality_profile": (declared or {}).get("quality_profile")}
