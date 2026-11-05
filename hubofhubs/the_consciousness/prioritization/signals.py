"""The signals Prioritization reads for the asks and goals subjects, apart from the fields every subject shares. Standard library only.

``unblocks_of`` counts what finishing an item frees: the waiting items its own ``unblocks`` names plus the other candidates that list it in ``blocked_by``. A met
or ended milestone is not a priority, so the caller passes only the live candidates."""
from typing import Any, Mapping, Sequence


def unblocks_of(item: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]) -> int:
    """How many distinct items an answer to ``item`` frees."""
    ident = str(item.get("id"))
    freed = {str(x) for x in item.get("unblocks") or ()}
    freed |= {str(c.get("id")) for c in candidates if ident in {str(b) for b in c.get("blocked_by") or ()}}
    freed.discard(ident)
    return len(freed)
