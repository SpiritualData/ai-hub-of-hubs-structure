"""The model planner: an arm of the Planner that asks a model to break the request into pieces and name the worker category of each, instead of
routing by the words of the request. It reads the same inputs as every arm of the Planner (the request, the context view, the target, the
guidance and what failed last time) and returns the same pieces, each with its sub-goal and one tool from a closed list. The model reaches it through Model
Plumbing. A reply that is not a list of pieces, or that names a tool outside the list, raises ``PlanError`` and is never repaired by guessing.
Standard library plus the hub and ``esoi``."""
import json
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi.assemble import Lazy

from hubofhubs.the_intelligence.mind.planner.planning import sub_goal, unmet_pieces
from hubofhubs.the_intelligence.mind.planner.schema import normalize_choice
from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing

TOOLS = ("web-search", "the-science", "file-editing", "read-files", "connected-system-operations", "delegated-agent-sessions", "none")

PROMPT = """Break the request into the smallest list of pieces that together meet it, and name the worker each piece needs. Reply with a JSON list only,
no other text. Each item is {{"piece": "<what to do, in the request's own words>", "tool": "<one of: {tools}>"}}.

Workers: web-search (a fact that may have changed or that the context does not hold), the-science (a question about published research),
file-editing (change one file), read-files (read files of a folder), connected-system-operations (a write operation of a connected system),
delegated-agent-sessions (open-ended work that needs an agent), none (answer from the context already given). Use none when the context
holds the answer. Do not use em dashes.

Request: {request}

Context already given:
{context}

What the target asks for: {target}
Nudge for the plan: {guidance}
Pieces that failed last time, to be planned again: {unmet}
"""


class PlanError(ValueError):
    """The model's reply was not a plan the Planner can use."""


def parse_pieces(raw: str) -> List[Dict[str, str]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0] if "\n" in text else text.strip("`")
    try:
        items = json.loads(text)
    except ValueError as error:
        raise PlanError(f"the plan is not JSON: {error}") from error
    if not isinstance(items, list) or not items:
        raise PlanError("the plan is not a non-empty list of pieces")
    out: List[Dict[str, str]] = []
    for item in items:
        piece = str(item.get("piece") or "").strip() if isinstance(item, dict) else ""
        tool = normalize_choice(item.get("tool") if isinstance(item, dict) else None, TOOLS)
        if not piece or tool is None:
            raise PlanError(f"a piece names no work or a tool outside the list: {item!r}")
        out.append({"piece": piece, "tool": "" if tool == "none" else tool})
    return out


@implementation("planner", "model_planner")
class ModelPlanner:
    """One model call plans the request: the pieces and the worker category of each, chosen by reading the request and the context, not by cue words."""
    REQUIRES = ()     # the model comes through Model Plumbing
    PAID = True

    def __init__(self, plumbing: Lazy[ModelPlumbing], tier: str = "cheap"):
        self.plumbing, self.tier = plumbing, tier

    def plan(self, request: str, context: Optional[Mapping[str, Any]] = None, target: Optional[Mapping[str, Any]] = None,
             guidance: Optional[Mapping[str, Any]] = None, unmet: Optional[Mapping[str, Any]] = None) -> Sequence[Mapping[str, Any]]:
        failed = list(unmet_pieces(unmet))
        prompt = PROMPT.format(tools=", ".join(TOOLS), request=request, context=str((context or {}).get("view") or "(nothing)"),
                               target=str((target or {}).get("done_standard") or "(not stated)"), guidance=str((guidance or {}).get("nudge") or "(none)"),
                               unmet=("; ".join(failed) + ": " + str((unmet or {}).get("reason", ""))) if failed else "(none)")
        pieces = parse_pieces(self.plumbing.ask(prompt, self.tier))
        return [{"piece": p["piece"], "sub_goal": sub_goal(p["piece"], target), "tool": p["tool"]} for p in pieces]
