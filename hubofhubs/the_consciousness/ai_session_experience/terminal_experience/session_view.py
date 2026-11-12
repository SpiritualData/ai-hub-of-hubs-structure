"""What a person sees of a run: a reducer from session events to a small state, and the text drawn from that state.

``SessionView.apply(event)`` keeps the goal, the steps (the latest event of a ``step_id`` replaces earlier ones), the tree of agents, the messages the
person sent (``sent``, then ``taken up`` when the harness says so), the open question, the cost and the clock. ``frame`` is the live screen (a header,
the latest steps, the agent tree, the messages, the question and the keys), ``event_line`` one plain line for an event, and ``report`` the closing
account: how it ended, what was reported, the files changed, the tree, cost and time. Plain mode uses ASCII only and no escape codes; a terminal
gets the glyphs and colour. Standard library only.
"""
from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    MAIN, AgentEnded, AgentStarted, Finished, Notice, Review, RunStarted, SessionEvent, Step, Usage, Waiting, short)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import hub_lines, present
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.markdown_text import markdown_lines

COLOR = {"running": "33", "done": "32", "failed": "31", "blocked": "31", "dim": "", "bold": "1", "ask": "35"}
HELP_ROWS = ("Esc or Ctrl-C  stop the run and keep the session (type resume to continue)",
             "type + Enter    steer the run; @name text steers one helper, /stop name stops one",
             "Tab             show or hide the structure tree (which solution each helper works on)",
             "Up, Down, Right the tree: move, open the solution's fields and connections; Left closes",
             "y or n          answer a question the run asks",
             "?               show or hide this list (on an empty line)")


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
    held_notes: List[str] = field(default_factory=list)     # the interim notes of the harness since the last row drawn, held until a row that draws something shows whether they were the answer (``present.is_the_answer``)
    final: Optional[Finished] = None
    ceiling_usd: Optional[float] = None       # the ceilings the run was given, when it says
    ceiling_seconds: Optional[float] = None
    soft_limit: bool = False                  # the run was asked to wrap up at its soft limit
    hard_limit: str = ""                      # which ceiling stopped it ("spend" or "time")
    decisions: List[str] = field(default_factory=list)      # the hub's own stop or continue, one line each
    outside: List[str] = field(default_factory=list)
    command: str = "ahohs work"               # how this surface is started, for the resume command
    show_structure: bool = False              # the structure tree is open (collapsed by default)
    selected: int = 0                         # the row of the tree the arrow keys are on
    opened: List[str] = field(default_factory=list)         # the solutions whose fields are shown
    structure_compact: str = ""               # the one-line structure summary, kept by the surface from the events
    structure_panel: List[str] = field(default_factory=list)
    show_help: bool = False
    acting_for: str = ""                      # who the AI acts for (a Representative), shown as a quiet header segment; empty shows nothing
    authority: List[str] = field(default_factory=list)      # the authority in force, opened with the structure panel or /who
    segments: List[str] = field(default_factory=list)       # extra status segments a consumer supplies, appended to the header
    panels: List[str] = field(default_factory=list)         # extra panel lines a consumer supplies, drawn under the steps

    def apply(self, event: SessionEvent) -> None:
        if isinstance(event, RunStarted):
            self.goal, self.harness = event.goal or self.goal, event.harness or self.harness
            self.session_id = event.session_id or self.session_id
            self.solution, self.milestone, self.frame = event.solution or self.solution, event.milestone or self.milestone, event.frame or self.frame
            self.metric, self.metric_before = event.metric or self.metric, event.metric_before if event.metric_before is not None else self.metric_before
            self.status, self.final, self.ended = "running", None, None
            self.soft_limit, self.hard_limit = False, ""
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
            self.ceiling_usd = event.ceiling_usd if event.ceiling_usd is not None else self.ceiling_usd
            self.ceiling_seconds = event.ceiling_seconds if event.ceiling_seconds is not None else self.ceiling_seconds
        elif isinstance(event, Notice):
            if event.kind == "soft-limit":
                self.soft_limit = True
            elif event.kind == "hard-limit":
                self.hard_limit = event.reason or "ceiling"
            elif event.kind == "decision":
                self.decisions.append(hub_lines.decision_line(event.decision, event.reason))
            elif event.kind == "outside-folder":
                self.outside = [item for item in event.items if item not in self.outside] + self.outside
        elif isinstance(event, Review):
            self.notices.append("review: " + (event.text or "done"))
        elif isinstance(event, Finished):
            self.final, self.asking = event, None
            self.status = "stopped" if event.outcome == "stopped" else "finished"
            self.session_id = event.session_id or self.session_id
            self.cost_usd = event.cost_usd if event.cost_usd is not None else self.cost_usd
            self.tokens = event.tokens if event.tokens is not None else self.tokens
            self.outside = list(event.outside) + [item for item in self.outside if item not in event.outside]
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

    def tree_lines(self, glyphs: bool = False, running_only: bool = False) -> List[str]:
        """The helpers as an indented tree; ``running_only`` leaves out the helpers that ended (a surface whose transcript already has their ending line)."""
        lines: List[str] = []
        known = {key: a for key, a in self.agents.items() if not running_only or a.state == "running"}

        def walk(parent: str, depth: int) -> None:
            for agent in [a for a in known.values() if a.parent_id == parent]:
                mark = ("`- " if not glyphs else "└─ ") if depth else ""
                calls = f", {agent.calls} call{'' if agent.calls == 1 else 's'}" if agent.calls else ""
                lines.append(f"{'   ' * max(depth - 1, 0)}{mark}{short(agent.task, 50)}{f' ({agent.solution})' if agent.solution else ''}  [{agent.state}{calls}]")
                walk(agent.agent_id, depth + 1)
        top = [a for a in known.values() if a.parent_id not in known]
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
    return hub_lines.clock(seconds)


def money(view: SessionView) -> str:
    """The time, the cost, the calls and the tokens as one quiet line; a figure that is missing leaves its segment out, a ceiling is named once it is half used."""
    when_ceiling, spend_ceiling = present.ceilings_in_view(view)
    return present.join([present.join([hub_lines.clock(view.elapsed()), when_ceiling], " "), present.join([present.cost_text(view.cost_usd), spend_ceiling], " "),
                         present.count_text(view.calls, "call"), present.count_text(view.tokens, "token")])


def paint(text: str, code: str, color: bool) -> str:
    """``text`` in the style named ``code``. ``dim`` is no style at all: the rows it names (the goal, the structure line, the keys) carry information, SGR 2 (faint) is drawn at a
    strength each terminal chooses (some halve the intensity, some ignore it, reports differ) so its contrast cannot be known, and an explicit grey is unreadable on a light theme;
    the person's own foreground colour is the one that always has the contrast their theme was set for. The rows stay in order and in place, so the hierarchy is the layout's."""
    return f"\x1b[{COLOR[code]}m{text}\x1b[0m" if color and COLOR[code] else text


def step_row(step: Step, color: bool = False, who: str = "") -> str:
    """One row for a step (``present.step_line``): a glyph and a plain phrase; a helper's step names the helper."""
    return present.step_line(step, color, who or ("" if step.agent_id == MAIN else "helper"))


def metric_line(view: SessionView) -> str:
    after = view.final.metric_after if view.final else None
    if view.metric_before is None and after is None:
        return ""
    before = "unknown" if view.metric_before is None else f"{view.metric_before:g}"
    now = "unknown" if after is None else f"{after:g}"
    change = f" ({after - view.metric_before:+g})" if after is not None and view.metric_before is not None else ""
    return f"Metric {view.metric or ''}: before {before}, after {now}{change}".replace("  ", " ")


def event_line(event: SessionEvent, view: SessionView, panel: bool = False) -> str:
    """One plain line for an event, for a log or a screen that cannot redraw. Empty when the event adds nothing to read.

    ``panel`` says a live panel sits beside this transcript: what the panel shows while it is happening (a running delegation, a helper that started, the running cost)
    is left out here, so each thing has one home and the transcript keeps only what finished."""
    if isinstance(event, Step) and event.kind == "note":
        if present.is_lifecycle(event):
            return ""
        text = present.one_line(event.label)
        if text:
            if view.held_notes and (present.is_the_answer(text, view.held_notes[-1]) or present.is_the_answer(view.held_notes[-1], text)):
                view.held_notes[-1] = max(text, view.held_notes[-1], key=len)      # the same note again, longer (a harness reports the text it has so far): one note
            else:
                view.held_notes.append(text)
        return ""
    own = row_of(event, view, panel)
    if not own and not isinstance(event, Finished):
        return ""            # an event that draws nothing (a figure update, a helper's start beside a panel) neither shows nor drops the notes held: they wait for a row that draws something
    held, view.held_notes = view.held_notes, []
    if isinstance(event, Finished):          # text the AI wrote on the way that is, or is part of, the answer has one home, the closing; a remark that is genuinely different stays a quiet row
        held = [note for note in held if not present.is_the_answer(note, event.report)]
    return "\n".join(row for row in (*held, own) if row)


def row_of(event: SessionEvent, view: SessionView, panel: bool) -> str:
    """The row of an event other than an interim note: no clock stamp (the header and the closing say the time), no raw kind word, no harness lifecycle."""
    if isinstance(event, RunStarted):
        return "\n".join(present.goal_line(event.goal, event.resumed))
    if isinstance(event, Step):
        if event.state == "running" and (event.kind != "delegate" or panel):
            return ""
        agent = view.agents.get(event.agent_id)
        return step_row(event, who=short(present.one_line(agent.task), 24) if agent else "")
    if isinstance(event, AgentStarted) and panel:
        return ""
    if isinstance(event, Usage):
        return ""
    if isinstance(event, AgentStarted):
        return f"{present.HELPER_GLYPH} Helper started: {short(present.one_line(event.task), 50)}" + (f" ({event.solution})" if event.solution else "") + (" under " + short(present.one_line(view.agents[event.parent_id].task), 24) if event.parent_id in view.agents else "")
    if isinstance(event, AgentEnded):
        name = view.agents[event.agent_id].task if event.agent_id in view.agents else event.agent_id
        state = {"met": "done", "running": "running"}.get(event.state, "failed")
        word = {"met": "finished", "unmet": "did not meet its goal", "stopped": "was stopped", "failed": "failed"}.get(event.state, event.state)
        return f"{present.GLYPHS[state]} Helper {word}: {short(present.one_line(name), 60)}"
    if isinstance(event, Review):
        return f"Review: {present.one_line(event.text) or 'done'}"
    if isinstance(event, Notice):
        if event.kind == "soft-limit":
            return hub_lines.soft_limit_line(view.elapsed(), view.cost_usd, view.ceiling_usd, view.ceiling_seconds)
        if event.kind == "hard-limit":
            return hub_lines.hard_limit_line(event.reason)
        if event.kind == "decision":
            return hub_lines.decision_line(event.decision, event.reason)
        if event.kind == "outside-folder":
            return "outside the folder: " + "; ".join(short(item, 80) for item in event.items)
    if isinstance(event, Waiting):
        helper = view.agents.get(event.agent_id)       # a question from a helper names the helper, so the person knows who is asking
        asker = f" ({short(helper.task, 30)} asks)" if helper is not None and event.agent_id != MAIN else ""
        return f"{present.GLYPHS['waiting']} Waiting for you{asker}: {event.question}" + (f" It will change: {short(event.preview, 80).rstrip(".")}." if event.preview else "") + " (y to approve, n to refuse)"
    return ""


SGR = re.compile(r"\x1b\[[0-9;]*m")


def clip(line: str, width: int) -> str:
    """``line`` cut to ``width`` visible characters, colour codes kept (they take no room), so a drawn row never wraps and the in-place redraw counts its rows right."""
    if len(SGR.sub("", line)) <= width:
        return line
    out, seen, at = [], 0, 0
    for found in SGR.finditer(line):
        take = min(found.start() - at, width - seen)
        out.append(line[at:at + take])
        seen += take
        out.append(found.group())
        at = found.end()
    take = max(min(len(line) - at, width - seen), 0)
    out.append(line[at:at + take])
    return "".join(out) + ("\x1b[0m" if "\x1b" in line else "")


def frame(view: SessionView, width: int = 80, color: bool = False, rows: int = 8, transcript: bool = False) -> List[str]:
    """The live screen as lines (no trailing newline). The caller redraws it in place.

    ``transcript`` says a scrolling transcript already holds what finished (a finished step, an ended helper, a note, the question, a limit line), so the screen shows only
    what is happening now: running steps, running helpers, messages not yet taken up, cost and time. Each piece of information then has one home."""
    glyphs = color
    out = [present.header(view, max(width - 1, 20), color, view.segments)]
    if view.goal and not transcript:      # beside a transcript the goal is the person's first message there, and has one home
        out.append(f"{present.paint(present.GOAL_GLYPH, present.CYAN, color)} {present.paint(short(present.one_line(view.goal), max(width - 4, 20)), present.CYAN, color)}")
    if view.solution or view.milestone:
        out.append(paint(f"serves: {view.solution} | milestone: {short(view.milestone, 50)}", "dim", color))
    if view.show_structure and view.structure_panel:
        out.extend(view.structure_panel)
    elif view.structure_compact:
        out.append(paint(view.structure_compact, "dim", color))
    steps = [s for s in view.steps.values() if not present.is_lifecycle(s) and not (s.kind == "note" and s.state == "done")]       # the harness's own lifecycle and its narration are not rows
    steps = [s for s in steps if s.state == "running"] if transcript else steps
    out.extend(step_row(s, color) for s in steps[-rows:])
    out.extend(view.panels)
    tree = view.tree_lines(glyphs, running_only=transcript)
    if tree:
        out.append(paint("agents", "dim", color))
        out.extend("  " + line for line in tree)
    if transcript:
        waiting = sum(1 for message in view.messages if not message.taken_up)      # the note itself is a finished fact in the transcript; the panel keeps only how many wait
        if waiting:
            out.append(f"{waiting} note{'' if waiting == 1 else 's'} waiting: read after the current step")
    else:
        for message in view.messages[-3:]:
            out.append(f"you: {short(message.text, 60)}  ({'taken up' if message.taken_up else 'queued: read after the current step'})")
    if not transcript:
        for note in view.notices[-2:]:
            out.append(paint(note, "dim", color))
        if view.soft_limit and view.status in ("running", "waiting", "stopping"):
            out.append(paint(hub_lines.soft_limit_line(view.elapsed(), view.cost_usd, view.ceiling_usd, view.ceiling_seconds), "running", color))
        for line in view.decisions[-1:]:
            out.append(paint(line, "dim", color))
    if view.show_help:
        out.extend(paint(row, "dim", color) for row in HELP_ROWS)
    if view.asking is not None and not transcript:
        out.append(paint(f"? {view.asking.question}  [y] approve  [n] refuse", "ask", color))
        if view.asking.preview:
            out.append(paint(f"  will change: {short(view.asking.preview, max(width - 20, 20))}", "ask", color))
    keys = {"waiting": "y approve | n refuse | Esc stop", "stopping": "stopping, session is kept", "stopped": "type resume to continue | quit to leave"}.get(
        view.status, "Esc stop | type + Enter to steer | Tab structure | ? keys")
    out.append(paint(present.fit_parts(keys, max(width - 1, 20)), "dim", color))
    out.append(f"> {view.typing}")
    return [clip(line, max(width - 1, 20)) for line in out]


def report_parts(view: SessionView, color: bool = False, width: int = 0) -> Tuple[List[str], List[str]]:
    """``(body, tail)`` of the closing account: the answer and the quiet detail, then the outcome line and the resume command."""
    done = view.final
    outcome = done.outcome if done else view.status
    glyphs = color
    out: List[str] = []
    if done and done.report:
        out.extend(markdown_lines(done.report, width, color))      # the answer, once, with its markdown drawn (or its markers taken out when there is no colour)
    if done and done.error and outcome not in ("met", "stopped"):
        out.append(f"reason: {short(present.one_line(done.error), 120)}")
    files = view.changed()
    if view.solution or view.milestone:
        out.append(f"Served: {view.solution} | milestone: {short(view.milestone, 80)}")
    if view.frame:
        out.append(f"Frame: {short(view.frame, 160)}")
    line = metric_line(view)
    if line:
        out.append(line)
    if files:
        out.append(f"Changed ({len(files)}): " + ", ".join(files))        # a list of files only when there are some; the outcome line says "no files changed" otherwise
    if view.outside:
        out.append("Outside the folder (report only, not undone):")
        out.extend("  " + short(row, 140) for row in view.outside)
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
    for line in view.decisions:
        out.append(line)
    if done:
        left = hub_lines.left_line(outcome, done.error, done.end_reason, len(done.unseen))
        if left:
            out.append("Left: " + left)
    if width:       # words wrap at word boundaries with a hanging indent; the lines that are copied or drawn as they are (the command, code, tables) are never cut
        out = [piece for line in out for piece in ([line] if "\x1b" in line or len(line) <= width or line.startswith(("|", "```", "    ", "ahohs ")) else
                                                  textwrap.wrap(line, width, subsequent_indent="  " if line.startswith("  ") else "", break_long_words=False, break_on_hyphens=False) or [line])]
    tail: List[str] = [""]
    tail.extend(present.outcome_rows(view, color, width))
    if outcome == "stopped":
        tail.append(f"Session {view.session_id or '(none)'} is kept. Type resume to continue it.")
    resume = present.resume_lines(view)
    if resume:
        tail.extend(["", *resume])      # the command alone on its own line, whole, so it can be copied
    return out, tail


def report(view: SessionView, color: bool = False, width: int = 0) -> List[str]:
    """The closing account of the run: the answer, the quiet detail, one outcome line, and the command that resumes it."""
    body, tail = report_parts(view, color, width)
    return body + tail


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
