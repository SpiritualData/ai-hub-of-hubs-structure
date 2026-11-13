"""The HTTP surface: the routes of opencode V2's API that the stock client calls (measured by running it against a logging server, 2026-11-11, client 2.2.7), as one pure function from a
request to ``(status, body)``. Everything outside this set answers 404 with a JSON error; the client tolerates that for what it only enriches with (it shows a toast for the migration status, so
that one is answered), and the set below is what its start and a whole session need.

Wire shapes the client insists on: lists come wrapped as ``{location, data}`` (sessions and messages as ``{data, cursor}``), the message list honours ``order``, a permission reply and a model
or agent switch answer 204, an interrupt answers ``{interrupted}``, and a prompt answers the inbox item it made (the id is the one the client gave it). Standard library only."""
from __future__ import annotations

import re
import tempfile
import time
from typing import Any, Dict, Mapping, Optional, Tuple

from hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge import Bridge
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.projection import MODEL, VERSION
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present

Reply = Tuple[int, Optional[Any]]
WAIT_SECONDS = 600.0
AGENT = {"id": "build", "name": "Build", "request": {"settings": {}, "headers": {}, "body": {}}, "description": "The hub's session worker.", "mode": "primary", "hidden": False,
         "permissions": [{"action": "*", "resource": "*", "effect": "allow"}]}
MODEL_INFO = {"id": "hub", "modelID": "hub", "providerID": "hub", "type": "chat", "family": "hub", "name": "Hub", "compatibility": {"reasoningField": "reasoning_content"},
              "package": "@opencode/ai/providers/openai-compatible", "settings": {}, "capabilities": {"tools": True, "input": ["text"], "output": ["text"], "temperature": True}, "variants": [],
              "time": {"released": 1760659200000}, "cost": [{"input": 0, "output": 0, "cache": {"read": 0, "write": 0}}], "status": "active", "enabled": True,
              "limit": {"context": 200000, "input": 160000, "output": 32000}}
# the client prints the provider's name beside the model's, so the provider is named as the product: it says what is serving the session
PROVIDER = {"id": "hub", "integrationID": "hub", "name": present.PRODUCT, "activation": "enabled", "package": "@opencode/ai/providers/openai-compatible", "settings": {}}
# The client's "Getting started" panel (connect from 75+ providers) shows until some integration has a connection, and its model picker lists the models of the providers it knows. The hub is the
# one integration, already connected (through the environment: nothing for the person to enter), and its models are the hub's tiers, so the panel stays away and the picker offers the hub's own choices.
INTEGRATION = {"id": "hub", "name": present.PRODUCT, "metadata": {}, "methods": [], "connections": [{"type": "env", "name": "AHOHS"}]}


def model_info(tier: str) -> Dict[str, Any]:
    """The model entry for one of the hub's tiers (which model serves it is the hub's choice, made when the run starts) or for an explicit model the hub serves (named as itself)."""
    from hubofhubs.the_world.model_plumbing.model_tier_chooser.role_tiers import TIERS
    return {**MODEL_INFO, "id": tier, "modelID": tier, "name": tier.capitalize() if tier in TIERS else tier, "family": "hub", "cost": []}
EMPTY_LISTS = ("/api/skill", "/api/mcp", "/api/reference","/api/shell", "/api/form", "/api/vcs/branch", "/api/vcs/status", "/api/plugin")
NOT_FOUND = {"_tag": "NotFound", "message": "this server does not implement that route"}


def first(query: Mapping[str, Any], name: str, default: str = "") -> str:
    value = query.get(name, default)
    return (value[0] if isinstance(value, (list, tuple)) and value else value) or default


def wrapped(bridge: Bridge, data: Any) -> Dict[str, Any]:
    return {"location": bridge.store.location, "data": data}


def info(bridge: Bridge, port: int) -> Dict[str, Any]:
    return {"version": VERSION, "pid": 1, "hostname": "localhost", "urls": [f"http://127.0.0.1:{port}"], "paths": {"tmp": tempfile.gettempdir()}, "capabilities": {}}


def handle(bridge: Bridge, method: str, path: str, query: Mapping[str, Any], body: Optional[Mapping[str, Any]], port: int = 0) -> Reply:
    """The answer to one request. Unknown routes are 404; a session id the server does not hold is 404 too."""
    store, body = bridge.store, dict(body or {})
    if path == "/api/info":
        return 200, info(bridge, port)
    if path == "/api/location":
        return 200, {"directory": store.directory, "project": {"id": "p" * 40, "directory": store.directory, "canonical": store.directory}}
    if path == "/api/fs/list":
        return 200, wrapped(bridge, [])
    if path == "/api/agent":
        return 200, wrapped(bridge, [AGENT])
    if path == "/api/model":
        return 200, wrapped(bridge, [model_info(t) for t in store.tiers] or [MODEL_INFO])
    if path == "/api/model/default":
        return 200, wrapped(bridge, model_info(store.model["id"]) if store.tiers else MODEL_INFO)
    if path == "/api/integration":
        return 200, wrapped(bridge, [INTEGRATION])
    if path == "/api/provider":
        return 200, wrapped(bridge, [PROVIDER])
    if path == "/api/config":
        return 200, [{"type": "directory", "path": store.directory}]
    if path == "/api/command":                           # the consumer's own slash commands (the client lists them with its own)
        return 200, wrapped(bridge, [{"name": c.name, "description": c.description} for c in bridge.commands.values()])
    if path in EMPTY_LISTS:
        return 200, wrapped(bridge, [])
    if path == "/api/mcp/resource":
        return 200, wrapped(bridge, {"resources": [], "templates": []})
    if path == "/api/vcs":
        return 200, wrapped(bridge, {"branch": {}})
    if path == "/api/vcs/base":
        return 200, wrapped(bridge, None)
    if path == "/api/project":
        return 200, [{"id": "p" * 40, "canonical": store.directory, "time": {"created": 0, "updated": 0, "active": 0}, "sandboxes": []}]
    if path == "/api/experimental/migration/v1":
        return 200, {"status": "completed"}
    if path.startswith("/api/rpc/"):
        return 200, {"output": None}
    if path == "/api/permission/request":
        return 200, wrapped(bridge, store.open_requests())
    if path == "/api/session" and method == "GET":
        with store.lock:
            parent = first(query, "parentID")
            rows = [s for s in store.sessions.values() if (s.get("parentID", "") == parent if parent else True)]
        return 200, {"data": rows, "cursor": {"previous": None, "next": None}}
    if path == "/api/session/active":
        return 200, {"data": dict(store.active)}
    found = re.fullmatch(r"/api/(experimental/)?session/([^/]+)(?:/(.*))?", path)
    if not found:
        return 404, NOT_FOUND
    sid, rest = found.group(2), found.group(3)
    if sid not in store.sessions:
        return 404, {"_tag": "SessionNotFoundError", "message": "no such session"}
    if found.group(1):
        if rest == "wait" and method == "POST":            # a long poll: answers once the session settles (the inline interface waits on it)
            deadline = time.monotonic() + WAIT_SECONDS
            while (bridge.running or sid in store.active) and time.monotonic() < deadline:
                time.sleep(0.05)
            return 204, None
        return (200, {"data": []}) if rest == "terminal" else (404, NOT_FOUND)
    if rest is None and method == "GET":
        return 200, {"data": store.sessions[sid]}
    if rest == "message":
        return 200, store.page(sid, first(query, "order", "asc"), int(first(query, "limit", "0") or 0))
    if rest == "context":
        return 200, {"data": store.page(sid)["data"]}
    if rest == "inbox":
        return 200, {"data": list(store.pending[sid])}
    if rest in ("form", "diff"):
        return 200, {"data": []}
    if rest == "permission":
        return 200, {"data": store.open_requests(sid)}
    if rest == "model" and method == "POST":           # the person picked a tier in the client's model picker: it is the tier of the next run
        chosen = body.get("model")
        bridge.select_tier(str(chosen.get("id") or "") if isinstance(chosen, dict) else "")
        return 204, None
    if rest in ("view", "model", "agent") and method in ("POST", "GET"):
        return 204, None
    if rest == "command" and method == "POST":         # the person chose one of the consumer's commands in the slash menu
        known = bridge.command(str(body.get("name") or ""), str(body.get("text") or ""))
        return (204, None) if known else (404, {"_tag": "NotFound", "message": "no such command"})
    if rest == "interrupt" and method == "POST":
        return 200, {"interrupted": bridge.interrupt()}
    if rest == "prompt" and method == "POST":
        made = bridge.prompt(str(body.get("text") or ""), str(body.get("id") or ""))
        return 200, {"data": {"id": made["id"], "sessionID": sid, "time": {"created": store.now()}, "type": "user", "payload": {"text": str(body.get("text") or "")}, "delivery": "steer"}}
    reply = re.fullmatch(r"permission/([^/]+)/reply", rest or "")
    if reply and method == "POST":
        bridge.reply(reply.group(1), str(body.get("decision") or "reject"), str(body.get("message") or ""))
        return 204, None
    return 404, NOT_FOUND


__all__ = ["handle", "MODEL"]
