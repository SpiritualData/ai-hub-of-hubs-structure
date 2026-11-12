"""The hub's session events as the opencode client's events and messages (``projection.Store``), and nothing else: no thread, no socket, no clock.

What each event becomes:

* ``RunStarted``: the goal is the person's message and the session's title (shortened at a word boundary to what the client's title strip holds); the session is busy. A resumed run only
  becomes busy again. The solution, milestone, frame, who the AI acts for and the metric go into the session's metadata, which the hub's client plugin shows.
* ``Step``: one assistant step with one tool call (read, edit, run and check are the client's ``read``, ``edit`` and ``bash``; others are named by their label), completed or failed by its
  state. A step that is ``blocked`` is a refusal: its call fails with the reason, drawn as an error row. ``message-received`` takes the person's waiting message into the transcript.
  A ``note`` is held until the next event shows it was not the answer, then drawn as text; a lifecycle note is not drawn.
* ``AgentStarted`` and ``AgentEnded``: a child session, and a ``task`` call in the parent whose row names the helper and the solution it serves; the helper's steps go in the child session.
* ``Waiting``: a permission request (an edit with its diff when the preview is a diff, else a command-style request with the question and the preview).
* ``Usage``: the session's cost and tokens as the hub reports them; the next step that ends carries the cost not yet billed, so the client's per-message figures add up to the hub's.
* ``Notice`` and ``Review``: a quiet row in the transcript (not a toast that covers it).
* ``Finished``: what a stop left running is ended as interrupted; the answer, the quiet detail, one outcome line and the command that resumes (``present``'s words) are the closing text;
  the session becomes idle (succeeded, failed or interrupted).
Standard library only."""
from __future__ import annotations

import dataclasses
import re
from typing import Any, Dict, List, Optional, Tuple

from hubofhubs.the_consciousness.ai_session_experience.opencode_server.projection import Store
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    MAIN, AgentEnded, AgentStarted, Finished, Notice, Review, RunStarted, SessionEvent, Step, Usage, Waiting, short)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import hub_lines, present, session_view

TITLE_WIDTH = 28            # what the client's title strip shows of a title before it cuts it
DIFF_START = re.compile(r"^(---|@@|diff )", re.M)
TOOLS = {"read": ("read", "path"), "edit": ("edit", "path"), "run": ("bash", "command"), "check": ("bash", "command")}


def title_of(goal: str, width: int = TITLE_WIDTH) -> str:
    """The goal as a title: whole when it fits, else cut at a word boundary with an ellipsis (never in the middle of a word)."""
    text = present.one_line(goal)
    if len(text) <= width:
        return text
    cut = text[:width - 1].rsplit(" ", 1)[0] if " " in text[:width - 1] else text[:width - 1]
    return cut.rstrip(" ,.;:") + "…"


GENERATED_ID = re.compile(r"^(tool|toolu|call|agent|helper)?[-_]?[0-9a-z]*\d[0-9a-z]*$", re.I)      # a generated id is letters and digits (the CLI's call ids are mixed case, not only hex)


def helper_name(agent_id: str) -> str:
    """The helper's name for its row: its id read as words, or ``helper`` when the id is only a number a harness generated."""
    words = " ".join(re.split(r"[-_\s]+", agent_id.strip())).strip()
    return "helper" if not words or GENERATED_ID.match(agent_id.strip()) else words


def looks_like_diff(text: str) -> bool:
    return bool(DIFF_START.search(text or ""))


def counts(diff: str) -> Tuple[int, int]:
    lines = diff.splitlines()
    return (sum(1 for l in lines if l.startswith("+") and not l.startswith("+++")), sum(1 for l in lines if l.startswith("-") and not l.startswith("---")))


class Translator:
    """One run's events turned into store changes, in order. ``root`` is the session id; ``acting_for`` is who the AI acts for; ``command`` is how the resume command starts."""

    def __init__(self, store: Store, root: str, acting_for: str = "", command: str = "ahohs work") -> None:
        self.store, self.root, self.acting_for = store, root, acting_for
        self.view = session_view.SessionView(command=command, acting_for=acting_for)
        self.steps: Dict[Tuple[str, str], Tuple[str, str, str]] = {}      # (agent, step id) -> (session, message, tool call)
        self.open: Dict[str, Tuple[str, str]] = {}                       # message -> (session, tool call) of a call still running
        self.sessions: Dict[str, str] = {MAIN: root}                    # agent id -> session id
        self.helpers: Dict[str, Tuple[str, str, str]] = {}               # agent id -> (parent session, message, tool call) of its task call
        self.held: List[Step] = []                                       # interim notes held until a row shows whether they were (part of) the answer
        self.deferred: Dict[Tuple[str, str], Step] = {}                  # a helper's running step, not drawn until its own event says more
        self.linked: set = set()                                         # step keys whose row is a helper's
        self.closed: Optional[Tuple[str, str]] = None                    # (session, message) of the closing text, kept so a later ``Finished`` (the metric after) replaces it
        self.billed = 0.0
        self.corrections: List[Dict[str, Any]] = []
        self.counter = 0
        self.titled = False

    # --- the metadata a client plugin reads --------------------------------------------------------------------------------------------

    def hub_metadata(self) -> Dict[str, Any]:
        view = self.view
        when_ceiling, spend_ceiling = present.ceilings_in_view(view)
        done = view.final
        spend = present.join([present.cost_text(view.cost_usd), spend_ceiling], " ")
        quiet = spend if spend_ceiling or (view.cost_usd is not None and 0 < view.cost_usd < 0.005) else ""       # the client shows the cost itself; this says more only when a ceiling is near or the cost is under a cent
        when_full, spent_full = hub_lines.status_segment(view.elapsed(), view.cost_usd, view.ceiling_usd, view.ceiling_seconds)
        return {"hub": {"quiet": quiet, "time_full": when_full, "spend_full": spent_full, "helpers": len(view.agents), "serves": view.solution, "milestone": view.milestone, "frame": view.frame, "acting_for": self.acting_for, "harness": view.harness, "status": view.status,
                        "spend": spend, "time": present.join([hub_lines.clock(view.elapsed()), when_ceiling], " "),
                        "calls": view.calls or 0, "tokens": view.tokens or 0, "metric": session_view.metric_line(view),
                        "outcome": done.outcome if done else "", "corrections": list(self.corrections), "structure": view.tree_lines(glyphs=True),
                        "authority": list(view.authority)}}

    def publish(self) -> None:
        self.store.set_metadata(self.root, self.hub_metadata())

    # --- the person's own words ----------------------------------------------------------------------------------------------------

    def correction_sent(self, message_id: str, text: str) -> None:
        self.corrections.append({"id": message_id, "text": short(text, 80), "taken_up": False})
        self.publish()

    # --- events --------------------------------------------------------------------------------------------------------------------

    def handle(self, event: SessionEvent) -> None:
        self.view.now = self.view.started + event.at
        self.view.apply(event)
        if isinstance(event, RunStarted):
            self.run_started(event)
        elif isinstance(event, Step):
            self.step(event)
        elif isinstance(event, AgentStarted):
            self.flush(hand_offs=False)
            self.agent_started(event)
        elif isinstance(event, AgentEnded):
            self.agent_ended(event)
        elif isinstance(event, Waiting):
            self.flush()
            self.waiting(event)
        elif isinstance(event, Usage):
            self.usage(event)
        elif isinstance(event, Notice):
            self.notice(event)
        elif isinstance(event, Review):
            self.store.synthetic(self.root, "review: " + (event.text or "done"), "Review: " + short(present.one_line(event.text or "done"), 120))
        elif isinstance(event, Finished):
            self.finished(event)
        self.publish()

    def run_started(self, event: RunStarted) -> None:
        waiting = self.store.pending[self.root]
        self.closed = None                       # a new run has its own closing
        if not event.resumed and not self.titled:
            self.titled = True
            self.store.rename(self.root, title_of(event.goal or self.view.goal))
        self.publish()
        if waiting:                       # the person's own message (the client gave it an id), taken into the transcript as theirs
            self.store.deliver(self.root, waiting[0]["id"])
        elif not event.resumed:
            self.store.deliver(self.root, self.store.enqueue_user(self.root, event.goal or self.view.goal))
        self.store.execution(self.root, "started")

    def key_of(self, event: Step) -> Tuple[str, str]:
        if not event.step_id:
            self.counter += 1
            return (event.agent_id, f"auto-{self.counter}")
        return (event.agent_id, event.step_id)

    def step(self, event: Step) -> None:
        sid = self.sessions.get(event.agent_id, self.root)
        if event.kind == "message-received":
            self.taken_up(event, sid)
            return
        if event.kind == "note":
            if not present.is_lifecycle(event) and present.one_line(event.label):
                last = self.held[-1] if self.held else None
                if last is not None and (present.is_the_answer(event.label, last.label) or present.is_the_answer(last.label, event.label)):
                    self.held[-1] = max(event, last, key=lambda s: len(s.label))      # the same note again, longer: one note
                else:
                    self.held.append(event)
            return
        key = self.key_of(event)
        if event.kind == "delegate" and key not in self.steps:
            known = next((h for a, h in self.helpers.items() if h[2] not in {v[2] for v in self.steps.values()} and present.one_line(self.view.agents[a].task) == present.one_line(event.label)), None)
            if known is not None:                 # the helper's own event came first: its row is this step's row
                self.steps[key] = known
                self.linked.add(key)
            elif event.state == "running":
                self.flush()
                self.deferred[key] = event        # a helper's own event may come next and say more (its name and the solution it serves); the row is drawn then, else at the next event
                return
        self.deferred.pop(key, None)
        self.flush()
        if key not in self.steps:
            self.begin(sid, key, event)
        sid, mid, tid = self.steps[key]
        if event.kind == "delegate" and key in self.linked and mid in self.open and event.state == "done":
            return                                # the helper's own ending completes its row, with its summary
        if event.state in ("done", "failed", "blocked") and mid in self.open:
            meta = self.metadata_of(event)
            if event.state == "done":
                self.store.tool_succeeded(sid, mid, tid, event.detail, meta)
            elif event.state == "blocked":
                self.store.tool_failed(sid, mid, tid, "Refused: " + (present.one_line(event.detail) or "this step was not allowed"), "refused", meta)
            else:
                self.store.tool_failed(sid, mid, tid, present.one_line(event.detail) or "failed", "tool.failed", meta)
            self.end(sid, mid, "tool-calls")

    def begin(self, sid: str, key: Tuple[str, str], event: Step) -> None:
        mid = self.store.begin_step(sid)
        name, inp = self.tool_of(event)
        tid = self.store.start_tool(sid, mid, name, inp)
        self.steps[key] = (sid, mid, tid)
        self.open[mid] = (sid, tid)

    def tool_of(self, event: Step) -> Tuple[str, Dict[str, Any]]:
        label = present.one_line(event.label)
        if event.kind in TOOLS:
            name, field = TOOLS[event.kind]
            return name, ({field: label, "description": label} if name == "bash" else {field: label})
        if event.kind == "delegate":
            return "task", {"description": label, "agent": "helper"}
        name = re.sub(r"[^a-z0-9_]+", "_", label.split(":")[0].split(" ")[0].lower()).strip("_") or "tool"
        return name, {"description": label}

    def metadata_of(self, event: Step) -> Dict[str, Any]:
        if event.kind == "edit" and looks_like_diff(event.detail):
            added, removed = counts(event.detail)
            path = present.one_line(event.label)
            return {"files": [{"file": path, "filePath": path, "relativePath": path, "type": "update", "status": "modified", "patch": event.detail, "additions": added, "deletions": removed}]}
        return {}

    def taken_up(self, event: Step, sid: str) -> None:
        item = next((i for i in self.store.pending[sid] if i["id"] == event.step_id), None) or next((i for i in self.store.pending[sid] if i["payload"]["text"] == event.label), None) \
            or next(iter(self.store.pending[sid]), None)
        if item is not None:
            self.store.deliver(sid, item["id"])
        for note in self.corrections:
            if not note["taken_up"] and (note["id"] == event.step_id or note["id"] == (item or {}).get("id")):
                note["taken_up"] = True
                break

    def flush(self, hand_offs: bool = True) -> None:
        """Draw the held note as text, once something shows it was not the answer, and (unless a helper's own event is what is coming) the hand-off rows that waited for one."""
        notes, self.held = self.held, []
        for note in notes:
            self.text(self.sessions.get(note.agent_id, self.root), note.label)
        for key, step in list(self.deferred.items() if hand_offs else ()):
            del self.deferred[key]
            if key not in self.steps:
                self.begin(self.sessions.get(step.agent_id, self.root), key, step)

    def text(self, sid: str, text: str, finish: str = "stop") -> str:
        mid = self.store.begin_step(sid)
        self.store.add_text(sid, mid, text)
        self.end(sid, mid, finish)
        return mid

    def end(self, sid: str, mid: str, finish: str) -> None:
        """End a step, billing it what the hub has spent since the last step ended (the figures on the client's rows add up to the hub's)."""
        self.open.pop(mid, None)
        cost = max((self.view.cost_usd or 0.0) - self.billed, 0.0)
        self.billed += cost
        tokens = {"input": int(self.view.tokens or 0), "output": 0, "reasoning": 0, "cache": {"read": 0, "write": 0}}
        self.store.end_step(sid, mid, finish, cost, tokens)

    # --- helpers -------------------------------------------------------------------------------------------------------------------

    def agent_started(self, event: AgentStarted) -> None:
        child = self.store.ids.make("ses")
        parent = self.sessions.get(event.parent_id, self.root)
        self.sessions[event.agent_id] = child
        description = present.one_line(event.task) + (f" (serves {event.solution})" if event.solution else "")
        self.store.create_session(child, title_of(event.task), parent=parent)
        mid = self.store.begin_step(parent)
        tid = self.store.start_tool(parent, mid, "task", {"description": description, "agent": helper_name(event.agent_id), "prompt": event.task}, {"sessionId": child})
        self.helpers[event.agent_id] = (parent, mid, tid)
        self.open[mid] = (parent, tid)
        task = present.one_line(event.task)
        match = next((k for k, s in self.deferred.items() if present.one_line(s.label) == task), None)       # the harness also said the same hand-off as a step: one row, not two
        if match is not None:
            del self.deferred[match]
            self.steps[match] = (parent, mid, tid)
            self.linked.add(match)
        iid = self.store.enqueue_user(child, event.task)
        self.store.deliver(child, iid)
        self.store.execution(child, "started")

    def agent_ended(self, event: AgentEnded) -> None:
        if event.agent_id not in self.helpers:
            return
        parent, mid, tid = self.helpers[event.agent_id]
        child = self.sessions[event.agent_id]
        for key, (sid, cmid, ctid) in list(self.steps.items()):
            if sid == child and cmid in self.open:
                self.store.tool_failed(sid, cmid, ctid, "Interrupted", "interrupted", {"interrupted": True})
                self.store.fail_step(sid, cmid, "interrupted", "Step interrupted")
                self.open.pop(cmid, None)
        meta = {"sessionId": child}
        if mid not in self.open:
            self.store.execution(child, "succeeded" if event.state == "met" else "failed", **({} if event.state == "met" else {"error": {"type": event.state, "message": event.summary or event.state}}))
            return
        if event.state == "met":
            self.store.execution(child, "succeeded")
            self.store.tool_succeeded(parent, mid, tid, event.summary or "done", meta)
        else:
            self.store.execution(child, "failed", error={"type": event.state, "message": event.summary or event.state})
            self.store.tool_failed(parent, mid, tid, event.summary or event.state, event.state, meta)
        self.end(parent, mid, "tool-calls")

    # --- the rest ------------------------------------------------------------------------------------------------------------------

    def waiting(self, event: Waiting) -> None:
        helper = self.view.agents.get(event.agent_id)
        who = f" ({helper_name(event.agent_id)}: {present.one_line(helper.task)})" if helper is not None and event.agent_id != MAIN else ""
        question = present.one_line(event.question) + who
        request: Dict[str, Any] = {"id": event.ask_id or self.store.ids.make("per"), "sessionID": self.root, "message": question}
        if looks_like_diff(event.preview):
            request.update(action="edit", resources=[event.risky or "the change"], metadata={"diff": event.preview, "files": []})
        else:
            request.update(action="shell", resources=[line for line in (question, present.one_line(event.preview or event.risky)) if line], metadata={})
        source = next((v for k, v in self.steps.items() if k[0] == event.agent_id and v[2] and v[1] in self.open), None)
        if source is not None:
            request["source"] = {"type": "tool", "messageID": source[1], "id": source[2]}
        self.store.ask(request)

    def usage(self, event: Usage) -> None:
        cost = self.view.cost_usd or 0.0
        tokens = int(self.view.tokens or 0)
        self.store.set_usage(self.root, cost, tokens, 0)

    def notice(self, event: Notice) -> None:
        text = present.one_line(event.text)
        if event.kind == "decision":
            text = hub_lines.decision_line(event.decision, event.reason) if event.decision else text
        if event.kind == "outside-folder":
            return
        if text:
            self.store.synthetic(self.root, text, short(text, 160))

    def finished(self, event: Finished) -> None:
        if event.outcome != "stopped":                  # text the AI wrote on the way that is, or is part of, the answer has one home, the closing
            self.held = [note for note in self.held if not present.is_the_answer(note.label, event.report)]
        self.flush()
        for mid, (sid, tid) in list(self.open.items()):
            if event.outcome == "stopped":                # what a stop left running is ended as interrupted, so the stopped state shows
                self.store.tool_failed(sid, mid, tid, "Step interrupted", "interrupted", {"interrupted": True})
                self.store.fail_step(sid, mid, "interrupted", "Step interrupted")
                self.open.pop(mid, None)
            else:                                          # a run that ended has nothing still running
                self.store.tool_succeeded(sid, mid, tid, "")
                self.end(sid, mid, "tool-calls")
        if self.closed is not None and event.outcome != "stopped":      # a second ``Finished`` (the metric after) replaces the closing text, it does not add a second one
            text = self.closing(event)
            if text:
                self.store.replace_text(self.closed[0], self.closed[1], text)
            return
        if event.outcome == "stopped":
            text = f"Stopped, your work is kept. Session {self.view.session_id or '(none)'} is kept. Type resume to continue it."
            self.text(self.root, text, "error")           # a text of the assistant's, not a notice row: the inline client draws no notice rows, and the stopped state must show there too
            self.store.execution(self.root, "interrupted", reason="user")
            return
        closing = self.closing(event)
        if closing:
            self.closed = (self.root, self.text(self.root, closing))
        if event.outcome in ("met", "unmet"):
            self.store.execution(self.root, "succeeded")
        else:
            self.store.execution(self.root, "failed", error={"type": "failed", "message": event.error or "the run failed"})

    def closing(self, event: Finished) -> str:
        """The answer (its markdown left for the client to draw), the quiet detail, one outcome line and the command that resumes, alone on its own line."""
        view = self.view
        body, tail = session_view.report_parts(_without_report(view), False, 0)
        resume = present.resume_lines(view)
        parts = [event.report.strip()] if event.report.strip() else []
        parts += [line for line in quiet_detail(body) if line.strip()]
        parts += [row for row in tail if row.strip() and not row.startswith("Session ")] if event.outcome != "stopped" else []
        parts = [p for p in parts if p not in resume]
        text = "\n\n".join(parts)
        if resume:
            text += "\n\n" + resume[0] + "\n\n```\n" + resume[1] + "\n```"
        return text


def quiet_detail(lines: List[str]) -> List[str]:
    """The detail lines of the shared closing that the client's transcript should still carry: what changed, what was refused or done outside the folder, the metric, why it stopped. The solution
    served, the frame and the helper tree are left to the plugin's lines and its structure panel (the closing stays short enough to be seen whole on a small screen)."""
    kept: List[str] = []
    skipping = False
    for line in lines:
        if line.startswith(("Served:", "Frame:")):
            continue
        if line.startswith("Agents:"):
            skipping = True
            continue
        if skipping and line.startswith(" "):
            continue
        skipping = False
        kept.append(line)
    return kept


def _without_report(view: session_view.SessionView) -> session_view.SessionView:
    """A copy of the view whose closing carries no answer, so the shared closing rules can supply the rest of the text around the answer the client draws as markdown."""
    clone = dataclasses.replace(view)
    if view.final is not None:
        clone.final = dataclasses.replace(view.final, report="")
    return clone
