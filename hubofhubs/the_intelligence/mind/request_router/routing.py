"""Route a request: the arms of the one seat that decides what a request asks of the system (told something, something done, text written, or not yet understood).

``single_classifier`` asks one cheap model call, through Model Plumbing, for the route from a closed list; a reply that is not a usable route raises
``RouteError`` and is never repaired by guessing. ``plan_derived`` reads the route off the plan the Planner already made: the plan reports whether it
needs a worker that changes something, whether the deliverable is text for the reply and whether it needs more from the person, and ``route_from_report``
turns that report into the route by structure alone. ``majority_floor`` always says ``information``: the bound the others have to beat. Standard library plus the hub and ``esoi``."""
import json
from typing import Any, Dict, Mapping, Optional

from esoi import implementation
from esoi import Lazy

from hubofhubs.the_intelligence.mind.planner.interface import Planning
from hubofhubs.the_intelligence.mind.planner.schema import normalize_choice
from hubofhubs.the_intelligence.mind.request_router.interface import ROUTES
from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing

#: The workers of the Planner whose work changes something outside the reply; the others only read.
CHANGING_WORKERS = ("file-editing", "connected-system-operations", "delegated-agent-sessions")

PROMPT = """Decide what this request asks of the assistant. Reply with JSON only, no other text: {{"route": "<one of: {routes}>", "reason": "<one short sentence>"}}.

information: the person wants to be told something (a question, a status, a count, a lookup, an explanation). Reading data to answer is still information.
act: the person wants something done or changed (create, update, send, schedule, run, move a milestone forward), or work that needs a worker.
draft: the person wants text written and handed back in the reply (a post, a caption, an email body, a plan), not saved or sent.
clarify: the request cannot be acted on yet (it points at something unnamed, is cut off, or is too vague to tell which of the above it is).
Judge by what the person is asking for, not by how the sentence begins. Do not use em dashes.

What the assistant can already see:
{view}

Request: {request}
"""


class RouteError(ValueError):
    """The arm could not decide the route: the model's reply was not a usable route."""


def parse_route(raw: str) -> Dict[str, str]:
    """The route and reason in a model's JSON reply (fences allowed); a reply that is not JSON or names a route outside ``ROUTES`` raises ``RouteError``."""
    text = str(raw or "").strip()
    if text.startswith("```"):
        text = text.strip("`").split("\n", 1)[-1].rsplit("```", 1)[0] if "\n" in text else text.strip("`")
    try:
        data = json.loads(text)
    except ValueError as error:
        raise RouteError(f"the reply is not JSON: {error}") from error
    route = normalize_choice(data.get("route") if isinstance(data, dict) else None, ROUTES)
    if route is None:
        raise RouteError(f"the reply names no route from the list: {data!r}")
    return {"route": route, "reason": str(data.get("reason") or "").strip()}


def route_from_report(report: Mapping[str, Any]) -> Dict[str, str]:
    """The route a plan report implies, by structure alone. The report holds ``needs_more`` (the plan cannot proceed without the person), ``reply_deliverable`` (the deliverable is
    text for the reply), ``intent`` (``act`` or ``ask``) and ``worker`` (the worker category the plan needs, or empty). Needing more is ``clarify``; a text deliverable is ``draft``;
    an ``act`` intent or a worker that changes something is ``act``; anything else is ``information``."""
    if report.get("needs_more"):
        return {"route": "clarify", "reason": "the plan needs more from the person"}
    if report.get("reply_deliverable"):
        return {"route": "draft", "reason": "the plan's deliverable is text for the reply"}
    if str(report.get("intent") or "") == "act" or str(report.get("worker") or "") in CHANGING_WORKERS:
        return {"route": "act", "reason": "the plan asks for something to be done"}
    return {"route": "information", "reason": "the plan only reads and answers"}


@implementation("route-a-request", "single_classifier")
class SingleClassifier:
    """One model call decides the route from the closed list, reading the request and what the assistant can already see; it is asked what the person wants, not how the sentence starts."""
    REQUIRES = ()     # the model comes through Model Plumbing
    PAID = True

    def __init__(self, plumbing: Lazy[ModelPlumbing], tier: str = "cheap"):
        self.plumbing, self.tier = plumbing, tier

    def route(self, request: str, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        prompt = PROMPT.format(routes=", ".join(ROUTES), view=str((context or {}).get("view") or "(nothing)"), request=request)
        return parse_route(self.plumbing.ask(prompt, self.tier))


@implementation("route-a-request", "plan_derived")
class PlanDerived:
    """The route is read off the plan the Planner makes for the request: no extra call, and the route cannot disagree with the plan. With the hub's Planner the report is built from its pieces
    (a worker that changes something is ``act``; reading workers and no worker are ``information``), which cannot tell a draft or a request that needs more; a consumer whose planner
    reports those subclasses ``report`` and keeps the rest."""
    REQUIRES = ()     # the Planner it is handed

    def __init__(self, planner: Lazy[Planning]):
        self.planner = planner

    def report(self, request: str, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        pieces = list(self.planner.plan(request, context=context) or ())
        worker = next((str(p.get("tool") or "") for p in pieces if str(p.get("tool") or "") in CHANGING_WORKERS), "")
        return {"worker": worker, "intent": "act" if worker else "ask", "reply_deliverable": False, "needs_more": not pieces}

    def route(self, request: str, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        return route_from_report(self.report(request, context))


@implementation("route-a-request", "majority_floor")
class MajorityFloor:
    """Always ``information``: the commonest route, the bound a router has to beat."""
    REQUIRES = ()     # nothing

    def route(self, request: str, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]:
        return {"route": "information", "reason": "the floor answers every request the same way"}
