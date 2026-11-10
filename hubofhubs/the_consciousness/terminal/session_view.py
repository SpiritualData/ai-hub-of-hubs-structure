"""What a person sees of a run: a reducer from session events to a small state, and the text drawn from that state.

``SessionView.apply(event)`` keeps the goal, the steps (the latest event of a ``step_id`` replaces earlier ones), the tree of agents, the messages the
person sent (``sent``, then ``taken up`` when the harness says so), the open question, the cost and the clock. ``frame`` is the live screen (a header,
the latest steps, the agent tree, the messages, the question and the keys), ``event_line`` one plain line for an event, and ``report`` the closing
account: how it ended, what was reported, the files changed, the tree, cost and time. Plain mode uses ASCII only and no escape codes; a terminal
gets the glyphs and colour. Standard library only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from hubofhubs.the_consciousness.terminal.session_events import (
    MAIN, AgentEnded, AgentStarted, Finished, Review, RunStarted, SessionEvent, Step, Usage, Waiting, short)

ASCII_MARK = {"running": "..", "done": "ok", "failed": "!!", "blocked": "xx"}
GLYPH_MARK = {"running": "●", "done": "✓", "failed": "✗"}
COLOR = {"running": "33", "done": "32", "failed": "31", "blocked": "31", "dim": "2", "bold": "1", "ask": "35"}
KIND_WIDTH = 9


@dataclass
class Message:
    message_id: str
    text: str
    agent_id: str = ""
    taken_up: bool = False


@dataclass
class Agent:
    agent_id: str
    parent_id: str
    task: str
    state: str = "running"
    calls: int = 0
    solution: str = ""


@dataclass
class SessionView:
    goal: str = ""
    solution: str = ""
    milestone: str = ""
    frame: str = ""
    metric: str = ""
    metric_before: Optional[float] = None
    harness: str = ""
    session_id: str = ""
    status: str = "idle"                     # idle, running, stopping, waiting, stopped, finished
    steps: Dict[str, Step] = field(default_factory=dict)
    agents: Dict[str, Agent] = field(default_factory=dict)
    messages: List[Message] = field(default_factory=list)
    notices: List[str] = field(default_factory=list)
    asking: Optional[Waiting] = None
    cost_usd: Optional[float] = None
    tokens: Optional[int] = None
    calls: Optional[int] = None
    started: float = 0.0
    now: float = 0.0
    ended: Optional[float] = None
    typing: str = ""
    final: Optional[Finished] = None

    def apply(self, event: SessionEvent) -> None:
        if isinstance(event, RunStarted):
            self.goal, self.harness = event.goal or self.goal, event.harness or self.harness
            self.session_id = event.session_id or self.session_id
            self.solution, self.milestone, self.frame = event.solution or self.solution, event.milestone or self.milestone, event.frame or self.frame
            self.metric, self.metric_before = event.metric or self.metric, event.metric_before if event.metric_before is not None else self.metric_before
            self.status, self.final, self.ended = "running", None, None
        elif isinstance(event, Step):
            if event.kind == "message-received":
                for message in self.messages:
                    if not message.taken_up and (message.message_id == event.step_id or message.text == event.label or event.step_id == ""):
                        message.taken_up = True
                        break
                self.steps[event.step_id or f"received-{len(self.steps)}"] = event
            else:
                old = self.steps.get(event.step_id)
                if old is not None and not event.label:
                    event = Step(at=event.at, agent_id=old.agent_id, step_id=event.step_id, kind=old.kind, label=old.label, state=event.state, detail=event.detail)
                self.steps[event.step_id or f"step-{len(self.steps)}"] = event
            if self.status in ("waiting",):
                self.status, self.asking = "running", None
        elif isinstance(event, AgentStarted):
            self.agents[event.agent_id] = Agent(event.agent_id, event.parent_id, event.task, solution=event.solution)
        elif isinstance(event, AgentEnded):
            agent = self.agents.get(event.agent_id) or self.agents.setdefault(event.agent_id, Agent(event.agent_id, MAIN, event.agent_id))
            agent.state, agent.calls = event.state, event.calls or agent.calls
        elif isinstance(event, Waiting):
            self.asking, self.status = event, "waiting"
        elif isinstance(event, Usage):
            self.cost_usd = event.cost_usd if event.cost_usd is not None else self.cost_usd
            self.tokens = event.tokens if event.tokens is not None else self.tokens
            self.calls = event.calls if event.calls is not None else self.calls
        elif isinstance(event, Review):
            self.notices.append("review: " + (event.text or "done"))
        elif isinstance(event, Finished):
            self.final, self.asking = event, None
            self.status = "stopped" if event.outcome == "stopped" else "finished"
            self.session_id = event.session_id or self.session_id
            self.cost_usd = event.cost_usd if event.cost_usd is not None else self.cost_usd
            self.tokens = event.tokens if event.tokens is not None else self.tokens
            self.ended = self.now

    def sent(self, message_id: str, text: str, agent_id: str = "") -> None:
        self.messages.append(Message(message_id, text, agent_id))

    def notice(self, text: str) -> None:
        self.notices.append(text)

    def elapsed(self) -> float:
        return max(0.0, (self.ended if self.ended is not None else self.now) - self.started)

    def find_agent(self, token: str) -> str:
        """The agent a person means by ``token``: its id, or the one whose task has the word. Empty when none or more than one."""
        token = token.strip().lower()
        if not token:
            return ""
        if token in self.agents:
            return token
        hits = [a.agent_id for a in self.agents.values() if token in a.task.lower() or token in a.agent_id.lower()]
        return hits[0] if len(hits) == 1 else ""

    def blocked(self) -> List[str]:
        rows = [f"{s.label}: {s.detail or 'blocked'}" for s in self.steps.values() if s.state == "blocked"]
        for line in (self.final.blocked if self.final else ()):
            if line not in rows:
                rows.append(line)
        return rows

    def changed(self) -> List[str]:
        names: Dict[str, None] = {}
        for step in self.steps.values():
            if step.kind == "edit" and step.state != "failed" and step.label:
                names.setdefault(step.label)
        if self.final is not None:
            for name in self.final.changed:
                names.setdefault(name)
        return list(names)

    def children(self, parent: str) -> List[Agent]:
        return [a for a in self.agents.values() if a.parent_id == parent]

    def tree_lines(self, glyphs: bool = False) -> List[str]:
        lines: List[str] = []

        def walk(parent: str, depth: int) -> None:
            for agent in self.children(parent):
                mark = ("`- " if not glyphs else "└─ ") if depth else ""
                calls = f", {agent.calls} call{'' if agent.calls == 1 else 's'}" if agent.calls else ""
                lines.append(f"{'   ' * max(depth - 1, 0)}{mark}{short(agent.task, 50)}{f' ({agent.solution})' if agent.solution else ''}  [{agent.state}{calls}]")
                walk(agent.agent_id, depth + 1)
        top = [a for a in self.agents.values() if a.parent_id not in self.agents]
        if top:
            lines.append(f"main  [{'running' if self.final is None else 'finished'}]")
            for agent in top:
                calls = f", {agent.calls} call{'' if agent.calls == 1 else 's'}" if agent.calls else ""
                lines.append(f"{'`- ' if not glyphs else chr(0x2514) + chr(0x2500) + ' '}{short(agent.task, 50)}{f' ({agent.solution})' if agent.solution else ''}  [{agent.state}{calls}]")
                walk(agent.agent_id, 2)
        return lines


def replay(events: Sequence[SessionEvent]) -> "SessionView":
    """The view a surface draws after a reconnect: the same events applied in order give the same screen."""
    view = SessionView()
    for event in events:
        view.now = view.started + event.at
        view.apply(event)
    return view


def clock(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def money(view: SessionView) -> str:
    parts = [clock(view.elapsed())]
    parts.append(f"${view.cost_usd:.4f}" if view.cost_usd is not None else "cost unknown")
    if view.calls:
        parts.append(f"{view.calls} calls")
    if view.tokens:
        parts.append(f"{view.tokens} tokens")
    return " | ".join(parts)


def paint(text: str, code: str, color: bool) -> str:
    return f"\x1b[{COLOR[code]}m{text}\x1b[0m" if color else text


def step_row(step: Step, color: bool = False, who: str = "") -> str:
    mark = (GLYPH_MARK if color else ASCII_MARK).get(step.state, "..")
    who = f"[{who}] " if who else "" if step.agent_id == MAIN else f"[{step.agent_id[:8]}] "
    if step.kind == "message-received":
        return f"{paint(mark, step.state, color)} taken up   {short(step.label, 70)}"
    return f"{paint(mark, step.state, color)} {step.kind:<{KIND_WIDTH - 1}} {who}{short(step.label, 70)}"


def metric_line(view: SessionView) -> str:
    after = view.final.metric_after if view.final else None
    if view.metric_before is None and after is None:
        return ""
    before = "unknown" if view.metric_before is None else f"{view.metric_before:g}"
    now = "unknown" if after is None else f"{after:g}"
    change = f" ({after - view.metric_before:+g})" if after is not None and view.metric_before is not None else ""
    return f"Metric {view.metric or ''}: before {before}, after {now}{change}".replace("  ", " ")


def event_line(event: SessionEvent, view: SessionView) -> str:
    """One plain line for an event, for a log or a screen that cannot redraw. Empty when the event adds nothing to read."""
    stamp = f"[{clock(view.now - view.started)}] "
    if isinstance(event, RunStarted):
        return f"{stamp}{'resumed' if event.resumed else 'started'}: {short(event.goal, 80)} ({event.harness or 'harness'})"
    if isinstance(event, Step):
        if event.state == "running" and event.kind != "delegate":
            return ""
        agent = view.agents.get(event.agent_id)
        return stamp + step_row(event, who=short(agent.task, 24) if agent else "")
    if isinstance(event, AgentStarted):
        return f"{stamp}agent started: {short(event.task, 50)}" + (f" ({event.solution})" if event.solution else "") + (" under " + short(view.agents[event.parent_id].task, 24) if event.parent_id in view.agents else "")
    if isinstance(event, AgentEnded):
        name = view.agents[event.agent_id].task if event.agent_id in view.agents else event.agent_id
        return f"{stamp}agent {event.state}: {short(name, 60)}"
    if isinstance(event, Review):
        return f"{stamp}review: {event.text or 'done'}"
    if isinstance(event, Usage):
        bits = [f"{event.calls} call{'' if event.calls == 1 else 's'}"] if event.calls else []
        if event.cost_usd is not None:
            bits.append(f"${event.cost_usd:.4f}")
        return f"{stamp}so far: {', '.join(bits)}" if bits else ""
    if isinstance(event, Waiting):
        return f"{stamp}WAITING FOR YOU: {event.question}" + (f" It will change: {short(event.preview, 80).rstrip(".")}." if event.preview else "") + " (y to approve, n to refuse)"
    return ""


def frame(view: SessionView, width: int = 80, color: bool = False, rows: int = 8) -> List[str]:
    """The live screen as lines (no trailing newline). The caller redraws it in place."""
    glyphs = color
    head = f"ahohs  {view.harness or 'run'}  [{view.status}]  {money(view)}"
    out = [paint(head, "bold", color), paint(f"goal: {short(view.goal, max(width - 8, 20))}", "dim", color)]
    if view.solution or view.milestone:
        out.append(paint(f"serves: {view.solution} | milestone: {short(view.milestone, 50)}", "dim", color))
    shown = list(view.steps.values())[-rows:]
    out.extend(step_row(s, color) for s in shown)
    if view.agents:
        out.append(paint("agents", "dim", color))
        out.extend("  " + line for line in view.tree_lines(glyphs))
    for message in view.messages[-3:]:
        out.append(f"you: {short(message.text, 60)}  ({'taken up' if message.taken_up else 'sent, not taken up yet'})")
    for note in view.notices[-2:]:
        out.append(paint(note, "dim", color))
    if view.asking is not None:
        out.append(paint(f"? {view.asking.question}  [y] approve  [n] refuse", "ask", color))
        if view.asking.preview:
            out.append(paint(f"  will change: {short(view.asking.preview, max(width - 20, 20))}", "ask", color))
    keys = {"waiting": "y approve | n refuse | Esc stop", "stopping": "stopping, session is kept", "stopped": "type resume to continue | quit to leave"}.get(
        view.status, "Esc stop | type + Enter to steer | @name text steers one agent | /stop name stops one")
    out.append(paint(keys, "dim", color))
    out.append(f"> {view.typing}")
    return [line[:max(width - 1, 20)] if "\x1b" not in line else line for line in out]


def report(view: SessionView, color: bool = False) -> List[str]:
    """The closing account of the run."""
    done = view.final
    outcome = done.outcome if done else view.status
    glyphs = color
    title = {"met": "Done: the goal was met", "unmet": "Finished: the goal was not met", "stopped": "Stopped: your work is kept",
             "failed": "Failed"}.get(outcome, outcome)
    out = [paint(title, "bold", color)]
    if done and done.report:
        out.extend(["", done.report.strip()])
    if done and done.error and outcome != "met":
        out.append(f"reason: {short(done.error, 120)}")
    files = view.changed()
    if view.solution or view.milestone:
        out.append(f"Served: {view.solution} | milestone: {short(view.milestone, 80)}")
    if view.frame:
        out.append(f"Frame: {short(view.frame, 160)}")
    line = metric_line(view)
    if line:
        out.append(line)
    out.append("")
    out.append(f"Changed ({len(files)}): " + (", ".join(files) if files else "nothing"))
    blocked = view.blocked()
    if blocked:
        out.append("Blocked or refused:")
        out.extend("  " + short(row, 120) for row in blocked)
    tree = view.tree_lines(glyphs)
    if tree:
        out.append("Agents:")
        out.extend("  " + line for line in tree)
    if done and done.unseen:
        out.append("Not yet taken up (sent again on resume): " + "; ".join(short(m, 40) for m in done.unseen))
    out.append(f"Cost and time: {money(view)}")
    if outcome == "stopped":
        out.append(f"Session {view.session_id or '(none)'} is kept. Type resume to continue it.")
    return out


__all__ = ["Agent", "Message", "SessionReport", "SessionView", "clock", "replay", "event_line", "frame", "money", "report", "step_row"]


@dataclass
class SessionReport:
    """What ``attend`` returns: the last ``Finished`` and every run's, all events in order, the controls sent with whether the harness took each, the
    final view and the text written."""
    final: Optional[Finished] = None
    runs: Tuple[Finished, ...] = ()
    events: Tuple[SessionEvent, ...] = ()
    controls: Tuple[Tuple[object, bool], ...] = ()
    view: SessionView = field(default_factory=SessionView)
    text: str = ""
