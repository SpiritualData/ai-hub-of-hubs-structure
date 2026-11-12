"""The store a client reads and the event stream it follows: sessions, messages, the inbox of messages not yet taken up, open permission requests, and one ordered log of events.

A client builds its screen from two sources, a snapshot it reads over HTTP (sessions, messages, the inbox, permissions) and the events that follow; both come from this one store, so
a client that reconnects and reads the snapshot again sees what the events built. Ids are monotonic (a client sorts messages by id). Every event kept in a bounded buffer can be replayed to
a client that names the last one it saw. Pure state: no socket, no thread of its own, no clock except the one handed in. Standard library only."""
from __future__ import annotations

import queue
import secrets
import string
import threading
import time
from collections import deque
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

VERSION = "2.2.7"            # the tested client version; a server reports it so the client says nothing about a mismatch
ALPHABET = string.ascii_letters + string.digits
BUFFER = 2000
ZERO_TOKENS = {"input": 0, "output": 0, "reasoning": 0, "cache": {"read": 0, "write": 0}}
MODEL = {"id": "hub", "providerID": "hub"}


class Ids:
    """Ids that sort in the order they were made: a prefix, twelve hex digits of a strictly increasing millisecond counter, and a random tail."""

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self.clock, self.last, self.lock = clock, 0, threading.Lock()

    def make(self, prefix: str) -> str:
        with self.lock:
            self.last = max(self.last + 1, int(self.clock() * 1000))
            return f"{prefix}_{self.last:012x}" + "".join(secrets.choice(ALPHABET) for _ in range(14))


def message_id_of(event_id: str) -> str:
    """The id a client gives the message an event makes (it replaces the event prefix)."""
    return "msg_" + event_id.split("_", 1)[-1]


class Store:
    """All the state of one served hub session set, and the events that describe changes to it."""

    def __init__(self, directory: str, clock: Callable[[], float] = time.time, buffer: int = BUFFER, shown: str = "") -> None:
        """``shown`` is what the client is told the folder is (it prints it in its footer): the folder's name, so a screen carries no machine path."""
        directory = shown or directory
        self.directory, self.clock = directory, clock
        self.location = {"directory": directory}
        self.ids = Ids(clock)
        self.lock = threading.RLock()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.messages: Dict[str, List[Dict[str, Any]]] = {}
        self.pending: Dict[str, List[Dict[str, Any]]] = {}
        self.permissions: List[Dict[str, Any]] = []
        self.active: Dict[str, str] = {}
        self.seqs: Dict[str, int] = {}
        self.log: Deque[Tuple[int, Dict[str, Any]]] = deque(maxlen=buffer)
        self.counter = 0
        self.subscribers: List["queue.Queue[Dict[str, Any]]"] = []

    # --- the event stream ----------------------------------------------------------------------------------------------------------

    def now(self) -> int:
        return int(self.clock() * 1000)

    def emit(self, kind: str, data: Dict[str, Any], sid: str = "", durable: bool = True, version: int = 1) -> Dict[str, Any]:
        with self.lock:
            event = {"id": self.ids.make("evt"), "created": self.now(), "type": kind, "location": self.location, "data": data}
            if durable and sid:
                event["durable"] = {"aggregateID": sid, "seq": self.seqs.get(sid, 0), "version": version}
                self.seqs[sid] = self.seqs.get(sid, 0) + 1
            self.counter += 1
            self.log.append((self.counter, event))
            for waiting in list(self.subscribers):
                waiting.put(event)
            return event

    def subscribe(self, after: str = "") -> "queue.Queue[Dict[str, Any]]":
        """A queue that gets every event from now on, after the events kept since ``after`` (an event id; empty: none replayed)."""
        with self.lock:
            waiting: "queue.Queue[Dict[str, Any]]" = queue.Queue()
            if after:
                seen = False
                for _, event in self.log:
                    if seen:
                        waiting.put(event)
                    elif event["id"] == after:
                        seen = True
            self.subscribers.append(waiting)
            return waiting

    def unsubscribe(self, waiting: "queue.Queue[Dict[str, Any]]") -> None:
        with self.lock:
            if waiting in self.subscribers:
                self.subscribers.remove(waiting)

    def connected(self) -> Dict[str, Any]:
        """The first event of every stream, which tells a client to read the snapshot again."""
        return {"id": self.ids.make("evt"), "type": "server.connected", "data": {}}

    # --- sessions ------------------------------------------------------------------------------------------------------------------

    def create_session(self, sid: str, title: str = "", parent: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self.lock:
            info: Dict[str, Any] = {"id": sid, "projectID": "p" * 40, "cost": 0, "tokens": {**ZERO_TOKENS, "cache": dict(ZERO_TOKENS["cache"])}, "agent": "build", "model": dict(MODEL),
                                    "time": {"created": self.now(), "updated": self.now()}, "title": title, "location": dict(self.location), "metadata": dict(metadata or {})}
            if parent:
                info["parentID"] = parent
            self.sessions[sid], self.messages[sid], self.pending[sid] = info, [], []
            data = {"sessionID": sid, "projectID": info["projectID"], "location": self.location, "subpath": "", "slug": "hub-session", "version": VERSION, "title": title, "agent": "build",
                    "model": dict(MODEL), "metadata": dict(info["metadata"])}
            if parent:
                data["parentID"] = parent
            self.emit("session.created", data, sid)
            return info

    def rename(self, sid: str, title: str) -> None:
        with self.lock:
            self.sessions[sid]["title"] = title
            self.emit("session.renamed", {"sessionID": sid, "title": title}, sid)

    def set_metadata(self, sid: str, metadata: Dict[str, Any]) -> None:
        with self.lock:
            self.sessions[sid]["metadata"] = metadata
            self.emit("session.metadata.updated", {"sessionID": sid, "metadata": metadata}, sid)

    def set_usage(self, sid: str, cost: float, input_tokens: int, output_tokens: int) -> None:
        with self.lock:
            info = self.sessions[sid]
            info["cost"], info["tokens"] = cost, {"input": input_tokens, "output": output_tokens, "reasoning": 0, "cache": {"read": 0, "write": 0}}
            self.emit("session.usage.updated", {"sessionID": sid, "cost": cost, "tokens": info["tokens"]}, sid, durable=False)

    def execution(self, sid: str, kind: str, **data: Any) -> None:
        """``started``, ``succeeded``, ``failed`` or ``interrupted``: the session is busy or idle, and an idle marker joins the messages (as the client's own projection does)."""
        with self.lock:
            event = self.emit(f"session.execution.{kind}", {"sessionID": sid, **data}, sid)
            if kind == "started":
                self.active[sid] = "running"
                return
            self.active.pop(sid, None)
            outcome = {"succeeded": "succeeded", "failed": "failed", "interrupted": "interrupted"}[kind]
            marker: Dict[str, Any] = {"id": message_id_of(event["id"]), "type": "idle", "outcome": outcome, "time": {"created": event["created"]}}
            if kind == "failed":
                marker["error"] = data.get("error")
            self.messages[sid].append(marker)

    # --- messages ------------------------------------------------------------------------------------------------------------------

    def enqueue_user(self, sid: str, text: str, delivery: str = "steer", iid: str = "") -> str:
        """A person's message waits in the inbox until the run takes it up (``deliver``)."""
        with self.lock:
            iid = iid or self.ids.make("msg")
            item = {"type": "user", "payload": {"text": text}, "delivery": delivery}
            self.pending[sid].append({"id": iid, "sessionID": sid, "time": {"created": self.now()}, **item})
            self.emit("session.inbox.enqueued", {"sessionID": sid, "inboxID": iid, "item": item}, sid)
            return iid

    def deliver(self, sid: str, iid: str) -> bool:
        with self.lock:
            item = next((i for i in self.pending[sid] if i["id"] == iid), None)
            if item is None:
                return False
            self.pending[sid].remove(item)
            self.messages[sid].append({"id": iid, "time": {"created": self.now()}, "type": "user", "text": item["payload"]["text"]})
            self.emit("session.inbox.delivered", {"sessionID": sid, "inboxID": iid}, sid)
            return True

    def synthetic(self, sid: str, text: str, description: str) -> None:
        """A line in the transcript that is neither the person's nor the AI's (a notice): the client draws its description as a quiet row."""
        with self.lock:
            event = self.emit("session.synthetic", {"sessionID": sid, "text": text, "description": description}, sid)
            self.messages[sid].append({"id": message_id_of(event["id"]), "type": "synthetic", "text": text, "description": description, "time": {"created": event["created"]}})

    def assistant(self, sid: str, mid: str) -> Dict[str, Any]:
        return next(m for m in self.messages[sid] if m["id"] == mid)

    def begin_step(self, sid: str, agent: str = "build") -> str:
        with self.lock:
            mid = self.ids.make("msg")
            self.messages[sid].append({"id": mid, "time": {"created": self.now()}, "type": "assistant", "agent": agent, "model": dict(MODEL), "content": []})
            self.emit("session.step.started", {"sessionID": sid, "assistantMessageID": mid, "agent": agent, "model": dict(MODEL), "started": self.now()}, sid)
            return mid

    def start_tool(self, sid: str, mid: str, name: str, inp: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> str:
        with self.lock:
            tid = self.ids.make("call")
            self.assistant(sid, mid)["content"].append({"type": "tool", "id": tid, "name": name, "time": {"created": self.now()},
                                                        "state": {"status": "running", "input": inp, "metadata": dict(metadata or {})}})
            self.emit("session.tool.input.started", {"sessionID": sid, "assistantMessageID": mid, "id": tid, "name": name}, sid)
            self.emit("session.tool.called", {"sessionID": sid, "assistantMessageID": mid, "id": tid, "input": inp, "executed": True}, sid)
            if metadata:
                self.emit("session.tool.progress", {"sessionID": sid, "assistantMessageID": mid, "id": tid, "metadata": metadata}, sid, durable=False)
            return tid

    def tool(self, sid: str, mid: str, tid: str) -> Dict[str, Any]:
        return next(p for p in self.assistant(sid, mid)["content"] if p["type"] == "tool" and p["id"] == tid)

    def tool_succeeded(self, sid: str, mid: str, tid: str, text: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        with self.lock:
            part, content, meta = self.tool(sid, mid, tid), ([{"type": "text", "text": text}] if text else []), dict(metadata or {})
            part["state"] = {"status": "completed", "input": part["state"]["input"], "content": content, "metadata": meta}
            self.emit("session.tool.success", {"sessionID": sid, "assistantMessageID": mid, "id": tid, "content": content, "metadata": meta, "executed": True}, sid, version=2)

    def tool_failed(self, sid: str, mid: str, tid: str, message: str, kind: str = "tool.failed", metadata: Optional[Dict[str, Any]] = None) -> None:
        with self.lock:
            part, error, meta = self.tool(sid, mid, tid), {"type": kind, "message": message}, dict(metadata or {})
            part["state"] = {"status": "error", "input": part["state"]["input"], "error": error, "metadata": meta}
            self.emit("session.tool.failed", {"sessionID": sid, "assistantMessageID": mid, "id": tid, "error": error, "metadata": meta, "executed": True}, sid)

    def end_step(self, sid: str, mid: str, finish: str = "tool-calls", cost: float = 0.0, tokens: Optional[Dict[str, Any]] = None) -> None:
        with self.lock:
            tokens = tokens or {**ZERO_TOKENS, "cache": dict(ZERO_TOKENS["cache"])}
            message = self.assistant(sid, mid)
            message.update(finish=finish, cost=cost, tokens=tokens)
            message["time"]["completed"] = self.now()
            self.emit("session.step.ended", {"sessionID": sid, "assistantMessageID": mid, "finish": finish, "cost": cost, "tokens": tokens}, sid)

    def fail_step(self, sid: str, mid: str, kind: str, message: str) -> None:
        with self.lock:
            error = {"type": kind, "message": message}
            self.assistant(sid, mid).update(finish="error", error=error)
            self.emit("session.step.failed", {"sessionID": sid, "assistantMessageID": mid, "error": error}, sid)

    def add_text(self, sid: str, mid: str, text: str, chunk: int = 80) -> None:
        """A text part, streamed in pieces and closed whole (the closing event carries the full text, so a client that missed a piece still ends right)."""
        with self.lock:
            self.assistant(sid, mid)["content"].append({"type": "text", "text": text})
            self.emit("session.text.started", {"sessionID": sid, "assistantMessageID": mid, "ordinal": 0}, sid)
            for start in range(0, len(text), chunk):
                self.emit("session.text.delta", {"sessionID": sid, "assistantMessageID": mid, "ordinal": 0, "delta": text[start:start + chunk]}, sid, durable=False)
            self.emit("session.text.ended", {"sessionID": sid, "assistantMessageID": mid, "ordinal": 0, "text": text}, sid)

    def replace_text(self, sid: str, mid: str, text: str) -> None:
        """The whole text of a closed text part replaced (the client ends the part with the text the closing event carries)."""
        with self.lock:
            part = next(p for p in self.assistant(sid, mid)["content"] if p["type"] == "text")
            part["text"] = text
            self.emit("session.text.ended", {"sessionID": sid, "assistantMessageID": mid, "ordinal": 0, "text": text}, sid)

    # --- permissions ---------------------------------------------------------------------------------------------------------------

    def ask(self, request: Dict[str, Any]) -> None:
        with self.lock:
            self.permissions.append(request)
            self.emit("permission.asked", request, request["sessionID"], durable=False)

    def answer(self, request_id: str, reply: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            request = next((r for r in self.permissions if r["id"] == request_id), None)
            if request is None:
                return None
            self.permissions.remove(request)
            self.emit("permission.replied", {"sessionID": request["sessionID"], "requestID": request_id, "reply": reply}, request["sessionID"], durable=False)
            return request

    # --- reads ---------------------------------------------------------------------------------------------------------------------

    def page(self, sid: str, order: str = "asc", limit: int = 0) -> Dict[str, Any]:
        with self.lock:
            data = list(self.messages.get(sid, []))
            if order == "desc":
                data.reverse()
            if limit:
                data = data[:limit]
            return {"data": data, "cursor": {"previous": None, "next": None}}

    def open_requests(self, sid: str = "") -> List[Dict[str, Any]]:
        with self.lock:
            return [r for r in self.permissions if not sid or r["sessionID"] == sid]
