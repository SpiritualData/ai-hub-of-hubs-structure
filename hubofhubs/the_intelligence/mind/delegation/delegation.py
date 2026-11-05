"""Delegation: hands each piece of a plan to the worker its ``tool`` names, only when a worker is needed, and returns one result per piece.

Every handoff carries the Representative's authority and the piece's sub-goal. Three limits are enforced here and nowhere else in the
flow: **authority** (a piece whose worker category is not allowed is refused, never run), the **budget** on the goal record (a count of
pieces and a dollar limit; a piece past it is refused), and **cancellation** (a ``cancelled`` callable is checked before each piece and is
handed through Tools to the worker's own stop hook (``cancel_check``) when the worker takes one, so a running agent session is stopped, not only the next
piece). A refused or cancelled piece comes back with the reason, so the replan loop and Judgment Calls can see why the work stopped.
Standard library plus the hub and ``esoi``."""
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi.assemble import Lazy

from hubofhubs.the_world.tools.interface import Tooling
from hubofhubs.the_world.science.interface import WorldKnowing

READ_ONLY = ("web-search", "the-science")      # what a representative with no declared authority may use
SCIENCE = "the-science"


def allowed(category: str, authority: Mapping[str, Any]) -> bool:
    return category in (authority.get("allow") or READ_ONLY)


def from_view(context: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """The result of a piece answered with no worker: what the view holds, with the sources of the view that name a link, or an honest
    ``met`` false when the view holds nothing."""
    view = str((context or {}).get("view") or "").strip()
    if not view:
        return {"text": "", "items": [], "met": False, "error": "nothing is known about this yet: no worker was needed and the context held nothing"}
    items = [{"title": s.get("title") or s["url"], "url": s["url"]} for s in (context or {}).get("sources") or () if s.get("url")]
    return {"text": view, "items": items, "met": True}


def worker_request(category: str, piece: Mapping[str, Any]) -> Any:
    if piece.get("request") is not None:
        return piece["request"]
    text = str(piece.get("piece", ""))
    return {"goal": text, "brief": text} if category in ("file-editing", "connected-system-operations", "delegated-agent-sessions") else text


def outcome(category: str, got: Any) -> Dict[str, Any]:
    """A worker's return value as the fields every result carries: ``text``, ``items`` and ``met`` (None when the worker does not say)."""
    if hasattr(got, "hits"):      # a search response
        items = [{"title": h.title, "url": h.url, "snippet": h.snippet} for h in got.hits]
        text = got.answer or "\n".join(f"{i['title']}: {i['snippet']}" for i in items)
        return {"text": text, "items": items, "met": bool(text)}
    if hasattr(got, "met"):       # a goal run
        return {"text": str(got.output or got.error or ""), "items": [], "met": bool(got.met)}
    return {"text": str(getattr(got, "text", got) or ""), "items": [], "met": None}


@implementation("delegation", "to_tools")
class ToTools:
    """Routes a piece to Tools (web search, file editing, connected systems, agent sessions) or to Science for a literature lookup."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, tools: Lazy[Tooling], science: Lazy[WorldKnowing]):
        self.tools, self.science = tools, science

    def delegate(self, pieces: Sequence[Mapping[str, Any]], authority: Optional[Mapping[str, Any]] = None,
                 budget: Optional[Mapping[str, Any]] = None, cancelled: Optional[Callable[[], bool]] = None,
                 context: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]:
        authority, budget = authority or {}, budget or {}
        results: List[Dict[str, Any]] = []
        spent = 0.0
        for index, piece in enumerate(pieces):
            base = {"piece": str(piece.get("piece", "")), "tool": str(piece.get("tool", "")), "sub_goal": piece.get("sub_goal"),
                    "authority": dict(authority), "items": [], "text": "", "met": None}
            category = base["tool"]
            if cancelled is not None and cancelled():
                results.append({**base, "refused": "cancelled"})
                continue
            if not category:       # no worker is needed: the piece is answered from the view Context Intake built
                results.append({**base, **from_view(context)})
                continue
            if not allowed(category, authority):
                results.append({**base, "refused": "authority"})
                continue
            over = (budget.get("pieces") is not None and index >= budget["pieces"]) or (budget.get("usd") is not None and spent >= budget["usd"])
            if over:
                results.append({**base, "refused": "budget"})
                continue
            try:
                if category == SCIENCE:
                    got = self.science.search(base["piece"])
                    results.append({**base, "text": str(getattr(got, "text", "")), "met": getattr(got, "kind", "") != "error"})
                    continue
                got = self.tools.use(category=category, request=worker_request(category, piece), cancel_check=cancelled, authority=authority)
                spent += float(getattr(got, "cost_usd", 0.0) or 0.0)
                results.append({**base, **outcome(category, got)})
            except Exception as error:      # noqa: BLE001  a failing worker is a result, not a crash of the flow
                results.append({**base, "error": f"{type(error).__name__}: {error}"})
        return results
