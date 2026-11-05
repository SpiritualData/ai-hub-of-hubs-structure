"""The Planner: breaks a request into pieces, each with the sub-goal it must meet and the worker category that fits it. The pieces are what
Delegation hands on. A piece names a ``tool`` (a Tools category, ``the-science`` for scholarly lookups, or empty when the piece is
answered from the context already taken in). On a replan the Planner reads ``unmet``, the sub-goals that failed and why, and does not
repeat a piece that already met its sub-goal. Standard library plus the hub and ``esoi``."""
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation

SEARCH, EDIT, SCIENCE = "web-search", "file-editing", "the-science"
STEP = re.compile(r"(?:^|\n)\s*(?:\d+[.)]|[-*])\s+(.+)")
SEQUENCE = re.compile(r"\s*(?:;|\bthen\b|\band then\b)\s*", re.I)
EDIT_CUES = re.compile(r"\b(implement|complete the function|fix the bug|refactor|rename|edit|add a (?:line|function|test)|write the function|patch)\b", re.I)
SCIENCE_CUES = re.compile(r"\b(paper|papers|study|studies|literature|dataset|datasets|benchmark|citation|journal|preprint|research on)\b", re.I)
FRESH_CUES = re.compile(r"\b(latest|current|today|recent|news|price|release|version|who is|who was|when did|when was|how many|what is the (?:name|capital|population)|which)\b|\?", re.I)


def sub_goal(text: str, target: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    return {"goal": text, "done_standard": str((target or {}).get("done_standard") or f"a response that addresses: {text}")}


def pieces_of(request: str) -> List[str]:
    steps = [m.strip() for m in STEP.findall(request)]
    if len(steps) >= 2:
        return steps
    parts = [p.strip() for p in SEQUENCE.split(request) if p.strip()]
    return parts if len(parts) >= 2 else [request.strip()]


def tool_for(text: str) -> str:
    if EDIT_CUES.search(text):
        return EDIT
    if SCIENCE_CUES.search(text):
        return SCIENCE
    return SEARCH if FRESH_CUES.search(text) else ""


def unmet_pieces(unmet: Optional[Mapping[str, Any]]) -> Sequence[str]:
    return [str(p) for p in (unmet or {}).get("failed_pieces", ())]


@implementation("planner", "cue_router")
class CueRouter:
    """Splits a request at numbered or bulleted steps and at "then", and routes each piece to a worker category by the words it uses: an edit
    verb to file editing, a literature word to Science, a question or a freshness word to web search, and nothing else to no worker."""
    REQUIRES = ()     # rules only

    def plan(self, request: str, context: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
             guidance: Optional[Mapping[str, Any]] = None, unmet: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]:
        retry = set(unmet_pieces(unmet))
        every = pieces_of(request)
        chosen = [p for p in every if p in retry] or every if retry else every
        return [{"piece": p, "sub_goal": sub_goal(p, target), "tool": tool_for(p)} for p in chosen]


@implementation("planner", "one_piece")
class OnePiece:
    """The whole request as one piece with no worker: what a Mind does with no planner. It is the bound the router has to beat."""
    REQUIRES = ()     # nothing

    def plan(self, request: str, context: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
             guidance: Optional[Mapping[str, Any]] = None, unmet: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]:
        return [{"piece": request, "sub_goal": sub_goal(request, target), "tool": ""}]
