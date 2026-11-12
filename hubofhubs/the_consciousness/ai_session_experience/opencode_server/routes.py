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
EMPTY_LISTS = ("/api/command", "/api/skill", "/api/mcp", "/api/reference", "/api/integration", "/api/shell", "/api/form", "/api/vcs/branch", "/api/vcs/status", "/api/plugin")
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
        return 200, wrapped(bridge, [MODEL_INFO])
    if path == "/api/model/default":
        return 200, wrapped(bridge, MODEL_INFO)
    if path == "/api/provider":
        return 200, wrapped(bridge, [PROVIDER])
    if path == "/api/config":
        return 200, [{"type": "directory", "path": store.directory}]
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
    if rest in ("view", "model", "agent") and method in ("POST", "GET"):
        return 204, None
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
