"""Adapters from what the harnesses emit today to the events of ``session_events``.

* ``LoopLines``: the progress strings of the hub's own loop (``call 2: EDIT app.py ok``, ``call 2: check passed``, ``review: no change``).
* ``loop_log_events``: the helpers a finished loop recorded in ``LoopResult.log`` (``{"delegated": task, "calls": n, "met": bool}``). Today the loop
  announces a helper only when it ends, so the tree of a loop run is complete at that point and not before.
* ``StreamJson``: the lines of a Claude Code ``stream-json`` session (tool_use and tool_result blocks, ``parent_tool_use_id`` for helpers, ``result``).
* ``report_events``: a ``SolutionReport`` tree (any object with ``solution``, ``name``, ``status``, ``calls``, ``children``).
* ``progress_events``: one ``ProgressEvent`` of the hub's runners, routed to the adapter that reads it.

All are pure and standard library only.
"""
from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from hubofhubs.the_consciousness.terminal.session_events import (
    MAIN, AgentEnded, AgentStarted, Review, SessionEvent, Step, Usage, Waiting, short)

LOOP_ACTION = re.compile(r"^call (\d+): (READ|EDIT|RUN|DELEGATE|USE|NOTE)\s*(.*?)\s+(ok|failed)$")
LOOP_CHECK = re.compile(r"^call (\d+): check (passed|failed)$")
LOOP_REVIEW = re.compile(r"^review: (.*)$")
LOOP_KINDS = {"READ": "read", "EDIT": "edit", "RUN": "run", "DELEGATE": "delegate", "USE": "tool", "NOTE": "note"}

READ_TOOLS = ("Read", "Glob", "Grep", "LS", "WebFetch", "WebSearch", "NotebookRead")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
AGENT_TOOLS = ("Task", "Agent")


class LoopLines:
    """Turns the loop's progress strings into steps. Keeps a count so a repeated label is still a new step."""

    def __init__(self) -> None:
        self.count = 0

    def events(self, text: str) -> List[SessionEvent]:
        text = str(text or "").strip()
        found = LOOP_ACTION.match(text)
        if found:
            self.count += 1
            number, word, label, ok = found.groups()
            return [Step(step_id=f"call{number}-{self.count}", kind=LOOP_KINDS[word], label=short(label or word.lower()),
                         state="done" if ok == "ok" else "failed", detail=f"call {number}")]
        found = LOOP_CHECK.match(text)
        if found:
            self.count += 1
            return [Step(step_id=f"call{found.group(1)}-{self.count}", kind="check", label="check", state="done" if found.group(2) == "passed" else "failed",
                         detail=f"call {found.group(1)}")]
        found = LOOP_REVIEW.match(text)
        if found:
            said = found.group(1)
            digits = re.findall(r"\d+", said)
            return [Review(text=said, corrections=int(digits[0]) if digits else 0)]
        if not text:
            return []
        self.count += 1
        return [Step(step_id=f"note-{self.count}", kind="note", label=short(text))]


def loop_log_events(log: Sequence[Mapping[str, Any]], parent: str = MAIN) -> List[SessionEvent]:
    """The helpers of a finished loop run: an ``AgentStarted`` and an ``AgentEnded`` for each ``delegated`` entry of ``LoopResult.log``."""
    out: List[SessionEvent] = []
    for index, entry in enumerate(entry for entry in log if "delegated" in entry):
        agent = f"helper-{index + 1}"
        out.append(AgentStarted(agent_id=agent, parent_id=parent, task=short(entry.get("delegated"))))
        out.append(AgentEnded(agent_id=agent, state="met" if entry.get("met") else "unmet", calls=int(entry.get("calls") or 0)))
    return out


class StreamJson:
    """Turns the lines of a Claude Code ``stream-json`` session into events. ``changed`` collects the files the session wrote."""

    def __init__(self) -> None:
        self.kinds: Dict[str, str] = {}
        self.labels: Dict[str, str] = {}
        self.owners: Dict[str, str] = {}
        self.agents: Dict[str, str] = {}
        self.changed: Dict[str, None] = {}
        self.session_id = ""

    def owner(self, raw: Mapping[str, Any]) -> str:
        parent = raw.get("parent_tool_use_id")
        return str(parent) if parent and str(parent) in self.agents else MAIN

    def events(self, raw: Mapping[str, Any]) -> List[SessionEvent]:
        kind = raw.get("type")
        out: List[SessionEvent] = []
        if kind == "system" and raw.get("subtype") == "init":
            self.session_id = str(raw.get("session_id") or self.session_id)
        elif kind == "assistant":
            who = self.owner(raw)
            for block in (raw.get("message") or {}).get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    out.extend(self.tool_use(block, who))
                elif block.get("type") == "text" and str(block.get("text") or "").strip():
                    out.append(Step(agent_id=who, step_id=f"text-{len(self.kinds)}", kind="note", label=short(block["text"])))
                    self.kinds[f"text-{len(self.kinds)}"] = "note"
        elif kind == "user":
            for block in (raw.get("message") or {}).get("content") or []:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    out.extend(self.tool_result(block))
        elif kind == "permission_denied":      # shape assumed from the event name in the CLI docs: tool_name, tool_use_id, reason
            ident = str(raw.get("tool_use_id") or "")
            label = self.labels.get(ident) or str(raw.get("tool_name") or "tool")
            out.append(Step(agent_id=self.owners.get(ident, MAIN), step_id=ident or f"denied-{len(self.kinds)}", kind=self.kinds.get(ident, "tool"), label=label,
                            state="blocked", detail=short(raw.get("reason") or "permission refused")))
        elif kind == "result":
            usage = raw.get("usage") or {}
            tokens = int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
            cost = raw.get("total_cost_usd")
            out.append(Usage(cost_usd=float(cost) if cost is not None else None, tokens=tokens or None,
                             calls=int(raw["num_turns"]) if raw.get("num_turns") is not None else None))
        return out

    def tool_use(self, block: Mapping[str, Any], who: str) -> List[SessionEvent]:
        name, ident, given = str(block.get("name") or ""), str(block.get("id") or ""), block.get("input") or {}
        self.owners[ident] = who
        if name in AGENT_TOOLS:
            self.agents[ident] = who
            self.kinds[ident] = "delegate"
            task = short(given.get("description") or given.get("prompt") or name)
            self.labels[ident] = task
            return [AgentStarted(agent_id=ident, parent_id=who, task=task),
                    Step(agent_id=who, step_id=ident, kind="delegate", label=task, state="running")]
        path = str(given.get("file_path") or given.get("path") or given.get("pattern") or given.get("url") or given.get("query") or "")
        if name in READ_TOOLS:
            step_kind, label = "read", path or name
        elif name in EDIT_TOOLS:
            step_kind, label = "edit", path or name
            if path:
                self.changed.setdefault(path)
        elif name == "Bash":
            step_kind, label = "run", str(given.get("command") or name)
        else:
            step_kind, label = "tool", name + (f" {path}" if path else "")
        self.kinds[ident] = step_kind
        self.labels[ident] = short(label)
        return [Step(agent_id=who, step_id=ident, kind=step_kind, label=short(label), state="running")]

    def tool_result(self, block: Mapping[str, Any]) -> List[SessionEvent]:
        ident = str(block.get("tool_use_id") or "")
        failed = bool(block.get("is_error"))
        if ident in self.agents:
            return [AgentEnded(agent_id=ident, state="failed" if failed else "met"),
                    Step(agent_id=self.agents[ident], step_id=ident, kind="delegate", label=self.labels.get(ident, "helper"), state="failed" if failed else "done")]
        if ident not in self.kinds:
            return []
        return [Step(agent_id=self.owners.get(ident, MAIN), step_id=ident, kind=self.kinds[ident], label=self.labels.get(ident, ""), state="failed" if failed else "done")]


def report_events(report: Any, parent: str = MAIN) -> List[SessionEvent]:
    """The events of a ``SolutionReport`` tree: a start and an end for each node, children after their parent, with the parent named."""
    out: List[SessionEvent] = []
    status_to_state = {"met": "met", "already_met": "met", "unmet": "unmet", "cancelled": "stopped", "not_started": "not_started"}

    def walk(node: Any, owner: str) -> None:
        ident = str(getattr(node, "solution", "") or "node")
        out.append(AgentStarted(agent_id=ident, parent_id=owner, task=str(getattr(node, "name", "") or ident)))
        for child in getattr(node, "children", None) or []:
            walk(child, ident)
        out.append(AgentEnded(agent_id=ident, state=status_to_state.get(str(getattr(node, "status", "")), "unmet"), calls=int(getattr(node, "calls", 0) or 0)))
    walk(report, parent)
    return out


def progress_events(event: Any, loop: Optional[LoopLines] = None, stream: Optional[StreamJson] = None) -> List[SessionEvent]:
    """One ``ProgressEvent`` of the hub's runners as session events: ``stream`` carries a raw stream-json line in ``data``, ``decision`` is a question
    for the person, an ``exec`` tick of the loop is a progress string; anything else is chatter and gives no event."""
    kind = getattr(event, "type", "")
    data = getattr(event, "data", None) or {}
    if kind == "stream" and stream is not None and isinstance(data, Mapping):
        return stream.events(data)
    if kind == "decision":
        return [Waiting(ask_id=str(getattr(event, "decision_id", "") or data.get("decision_id") or "ask"), question=short(getattr(event, "text", "") or data.get("question") or ""),
                        risky=str(data.get("risky") or ""), preview=short(data.get("preview") or "", 160))]
    if kind == "exec" and loop is not None and data.get("phase") == "solution_loop":
        return loop.events(getattr(event, "text", ""))
    return []


__all__ = ["LoopLines", "StreamJson", "loop_log_events", "progress_events", "report_events"]
