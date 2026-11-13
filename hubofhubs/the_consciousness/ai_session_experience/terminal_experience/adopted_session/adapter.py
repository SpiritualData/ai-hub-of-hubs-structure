"""The adapter between the hub's session contract and the screen adopted from an existing terminal agent: session events in, the typed entries and events that screen is driven by out.

``ScreenAdapter.translate(event)`` is a pure, stateful mapping (no screen, no thread): a ``Step`` becomes one effect entry that later events of the same ``step_id`` update in place (each
update has one home), a note of the harness becomes a finished assistant message unless it turns out to be the answer, ``AgentStarted`` and ``AgentEnded`` become child sessions (the sub-agent
list and transcripts), ``Waiting`` becomes an approval callback (or a question when its options are not approve and refuse), and what only the hub has (who the AI acts for, the structure
of the solutions the work serves, the metric before and after, a note the person sent and its being taken up) becomes small events of its own (``HubLine``, ``NoteSent``, ``NoteTakenUp``,
``AskClosed``, ``Closing``). The controls go the other way through the shared driver (``live.Attendance``): the screen presses keys and the driver sends ``Stop``, ``Steer``, ``Approve``
and ``Refuse``. The screen's models are imported inside the functions that need them, so importing this module needs no screen library."""
from __future__ import annotations

from dataclasses import dataclass, replace
from types import SimpleNamespace
from typing import Any, Dict, List, Optional, Tuple

from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    MAIN, AgentEnded, AgentStarted, Finished, Notice, Review, RunStarted, SessionEvent, Step, Waiting, short)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import agent_focus, present
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionView, report_parts, row_of

#: kind -> (present participle, past tense, failure phrase): the verb of a step's row in each state
KIND_WORDS = {"read": ("Reading", "Read", "Could not read"), "search": ("Searching", "Searched", "Could not search"), "edit": ("Editing", "Edited", "Could not edit"), "run": ("Running", "Ran", "Command failed:"),
              "check": ("Checking", "Checked", "Check failed:"), "tool": ("Using", "Used", "Could not use"), "delegate": ("Handing off", "Handed off", "Could not hand off")}
SESSION_ID = "hub-session"
TURN_ID = "hub-turn"


@dataclass(frozen=True)
class HubLine:
    """One quiet line the hub adds to the transcript (``kind``: ``who``, ``notice``, ``limit``, ``stopping``, ``stopped``, ``resuming``, ``review``, ``help``)."""
    kind: str
    text: str


@dataclass(frozen=True)
class GoalSent:
    """The person's goal, drawn as their own message."""
    text: str


@dataclass(frozen=True)
class NoteSent:
    """A note the person typed while the AI works: shown once as sent (queued) until the harness takes it up."""
    message_id: str
    text: str
    agent_id: str = ""


@dataclass(frozen=True)
class NoteTakenUp:
    """The harness read the note (``message_id`` empty: the oldest one still waiting)."""
    message_id: str
    text: str


@dataclass(frozen=True)
class AskClosed:
    """The question was answered (by a key on the screen or from outside), so its screen goes away."""
    ask_id: str


@dataclass(frozen=True)
class Closing:
    """What the end of a run draws: the answer once, the quiet detail (metric before and after, what changed), the one outcome line and the resume command on its own line."""
    answer: str
    detail: Tuple[str, ...]
    outcome: Tuple[str, ...]
    resume: Tuple[str, ...]
    state: str


@dataclass(frozen=True)
class Figures:
    """What the header, the key line, the status line and the structure row say now."""
    header: str
    hint: str
    status: str
    structure: Tuple[str, ...]
    help: Tuple[str, ...]
    running: bool
    asking: bool
    stopped: bool
    note_count: int


def vendored() -> SimpleNamespace:
    """The adopted screen's models, loaded on first use (they need the pydantic library). Not cached here: the import system keeps the one copy, so the adapter and the screen always
    share the same classes."""
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.vendor.mistral_vibe_ui.protocol import events, models, questions, tool_presentation
    return SimpleNamespace(events=events, models=models, questions=questions, display=tool_presentation)


def stamp(event: SessionEvent) -> int:
    return int(max(event.at, 0.0) * 1000)


class ScreenAdapter:
    """Session events to the screen's typed events. One adapter serves one attended session; it keeps the entries it has made so an update replaces them in place."""

    def __init__(self, view: SessionView):
        self.view = view
        self.steps: Dict[str, Step] = {}
        self.entries: Dict[str, Any] = {}
        self.children: Dict[str, Any] = {}
        self.owner: Dict[str, str] = {}
        self.asked_options: Dict[str, Tuple[str, ...]] = {}
        self.held = ""
        self.counter = 0

    def options_of(self, ask_id: str) -> Tuple[str, ...]:
        """The options a question offered, so the label picked on its screen maps back to approve (the first) or refuse (any other)."""
        return self.asked_options.get(ask_id, ())

    def history_for(self, agent_id: str) -> List[Any]:
        """The entries of one helper, oldest first, led by the task it was given as the first message (what its transcript view shows)."""
        m = vendored().models
        agent = self.view.agents.get(agent_id)
        task = agent.task if agent is not None else agent_id
        lead = m.PublicMessageEntry(id=f"task-{agent_id}", session_id=agent_id, turn_id=TURN_ID, created_at=0, updated_at=0, generation_status=m.PublicEntryGenerationStatus.COMPLETED,
                                    role="user", content=[m.TextContentBlock(text=task)], source="turn_start")
        notes = [m.PublicMessageEntry(id=f"note-{agent_id}-{note.message_id}", session_id=agent_id, turn_id=TURN_ID, created_at=0, updated_at=0,
                                      generation_status=m.PublicEntryGenerationStatus.COMPLETED, role="user",
                                      content=[m.TextContentBlock(text=note.text + ("" if note.taken_up else "  (queued: it reads it at its next step)"))], source="turn_start")
                 for note in list(self.view.messages) if note.agent_id == agent_id]        # what the person sent to this helper, shown in its own transcript
        result = ([m.PublicMessageEntry(id=f"result-{agent_id}", session_id=agent_id, turn_id=TURN_ID, created_at=0, updated_at=0, generation_status=m.PublicEntryGenerationStatus.COMPLETED,
                                        role="assistant", content=[m.TextContentBlock(text=agent.summary)])] if agent is not None and agent.summary else [])        # what it reported, in its own transcript
        return [lead] + result + [entry.model_copy(update={"session_id": agent_id}) for key, entry in self.entries.items() if self.owner.get(key) == agent_id] + notes      # what it reported first, then what it did, so a long report does not push its steps off the screen

    # --- entries ---------------------------------------------------------------------------------------------------------------------

    def base(self, event: SessionEvent, entry_id: str) -> Dict[str, Any]:
        m = vendored().models
        return dict(id=entry_id, session_id=SESSION_ID, turn_id=TURN_ID, created_at=stamp(event), updated_at=stamp(event), generation_status=m.PublicEntryGenerationStatus.COMPLETED)

    def message(self, event: SessionEvent, text: str) -> Any:
        """A finished assistant message (the harness's narration between two steps)."""
        m = vendored().models
        self.counter += 1
        return vendored().events.HistoryEntryAdded(entry=m.PublicMessageEntry(**self.base(event, f"note-{self.counter}"), role="assistant", content=[m.TextContentBlock(text=text)]))

    def release(self, event: SessionEvent, answer: str = "") -> List[Any]:
        """The held narration as a message, unless it is the answer (shown once, in the closing)."""
        held, self.held = self.held, ""
        if not held or (answer and present.is_the_answer(held, answer)):
            return []
        return [self.message(event, held)]

    def helper_name(self, agent_id: str) -> str:
        agent = self.view.agents.get(agent_id)
        return short(present.one_line(agent.task), 24) if agent is not None and agent_id != MAIN else ""

    def detail(self, step: Step, label: str, call: Any) -> Any:
        m = vendored().models
        kind = step.kind
        if kind == "read":
            return m.FileReadEffectDetail(tool_name="read", display=call, input=m.FileReadEffectInput(file_path=label))
        if kind == "edit":
            return m.FileEditEffectDetail(tool_name="edit", display=call, input=None)
        if kind in ("run", "check"):
            return m.ShellEffectDetail(tool_name="bash" if kind == "run" else "check", display=call, input=m.ShellEffectInput(command=label))
        if kind == "delegate":
            agent = self.view.agents.get(step.step_id)
            return m.SubagentEffectDetail(tool_name="task", display=call, input=m.SubagentEffectInput(task=label, agent=(agent.solution if agent else "") or "helper"),
                                          child_session_id=step.step_id, agent_name=label)
        return m.GenericEffectDetail(tool_name=(label.split() or ["tool"])[0], display=call, input=None)

    def state(self, step: Step, label: str, words: Tuple[str, str, str], suffix: str) -> Any:
        m, d = vendored().models, vendored().display
        if step.state == "running":
            return m.RunningEffectState()
        if step.state == "failed":
            if present.is_failed_command(step):       # a command that did not work is said in a few plain words, never as its raw shell text
                shown = d.EffectResultDisplay(success=False, verb="Did not work", message=present.tried_words(step.label) if step.kind == "run" else "a check", suffix=suffix)
                return m.FailedEffectState(error=m.PublicError(message=step.detail or "did not work"), display=shown, output_text=step.detail)       # the raw text stays in the detail
            shown = d.EffectResultDisplay(success=False, verb=words[2], message=label, suffix=suffix)
            return m.FailedEffectState(error=m.PublicError(message=step.detail or "failed"), display=shown, output_text=step.detail)
        if step.state == "blocked":
            why = f" ({short(present.one_line(step.detail), 60)})" if step.detail else ""
            if present.is_failed_command(step):
                return m.CancelledEffectState(reason=step.detail or "refused", display=d.EffectResultDisplay(success=False, verb="Skipped", message=present.refusal_words(step.detail).replace("Skipped ", "", 1), suffix=suffix))
            return m.CancelledEffectState(reason=step.detail or "refused", display=d.EffectResultDisplay(success=False, verb="Refused", message=label + why, suffix=suffix))
        return m.CompletedEffectState(display=d.EffectResultDisplay(success=True, verb=words[1], message=label, suffix=suffix))

    def effect(self, step: Step) -> List[Any]:
        """One effect entry per ``step_id``: the first event adds it, each later one updates it in place."""
        old = self.steps.get(step.step_id)
        if old is not None and not step.label:
            step = Step(at=step.at, agent_id=old.agent_id, step_id=step.step_id, kind=old.kind, label=old.label, state=step.state, detail=step.detail)
        self.steps[step.step_id] = step
        m, d = vendored().models, vendored().display
        words = KIND_WORDS.get(step.kind, ("Using", "Used", "Could not use"))
        label = (present.subject_of(step) if step.kind in ("read", "edit", "search") else present.helper_name(step.label, 40) if step.kind == "delegate"
                 else present.clip_words(present.one_line(step.label), 70)) or step.kind      # never a full path, and a helper by its short name
        helper = self.helper_name(step.agent_id)
        suffix = f" {present.HELPER_GLYPH}" if helper else ""       # the marker of a helper's rows; its name is said once, when it starts
        call = d.EffectCallDisplay(summary=label, verb=words[0], suffix=suffix, status_text=words[0])       # the loading line says the kind of work; the row says what (one home)
        entry = m.PublicEffectEntry(**self.base(step, step.step_id), title=label, detail=self.detail(step, label, call), state=self.state(step, label, words, suffix))
        before = self.entries.get(step.step_id)
        self.entries[step.step_id] = entry
        self.owner[step.step_id] = step.agent_id
        events = vendored().events
        return [events.HistoryEntryAdded(entry=entry)] if before is None else [events.HistoryEntryUpdated(previous=before, entry=entry, patch=[])]

    # --- the events ------------------------------------------------------------------------------------------------------------------

    def translate(self, event: SessionEvent) -> List[Any]:
        """The screen's events for one session event, in order. ``self.view`` has already applied the event."""
        if isinstance(event, RunStarted):
            out: List[Any] = [HubLine("resuming", "continuing the earlier session")] if event.resumed else []
            return out + ([GoalSent(present.one_line(event.goal))] if event.goal and not event.resumed else [])
        if isinstance(event, Step):
            return self.step(event)
        if isinstance(event, AgentStarted):
            return self.child(event, running=True)
        if isinstance(event, AgentEnded):
            said = [HubLine("result", f"{self.helper_name(event.agent_id) or 'Helper'} result: {short(present.one_line(event.summary), 160)}")] if event.summary else []       # its result, once, in the parent
            return said + self.child(event, running=False)
        if isinstance(event, Review):
            return self.release(event) + [HubLine("review", f"Review: {present.one_line(event.text) or 'done'}")]
        if isinstance(event, Waiting):
            return self.release(event) + [vendored().events.CallbackRequested(callback=self.asked(event))]
        if isinstance(event, Notice):
            text = row_of(event, self.view, True)
            return self.release(event) + ([HubLine("limit" if event.kind in ("soft-limit", "hard-limit") else "notice", text)] if text else [])
        if isinstance(event, Finished):
            return self.release(event, event.report)        # a stop is said once, in the closing (``present.stop_lines``)
        return []

    def step(self, step: Step) -> List[Any]:
        if step.kind == "message-received":
            return self.release(step) + [NoteTakenUp(step.step_id, present.one_line(step.label))]
        if step.kind == "note":
            if present.is_lifecycle(step):
                return []
            held, text = self.held, step.label.strip()
            self.held = text
            if held and not (present.is_the_answer(text, held) or present.is_the_answer(held, text)):
                return [self.message(step, held)]       # an earlier note that was not this one is narration between two steps: shown once
            return []
        return self.release(step) + self.effect(step)

    def child(self, event: SessionEvent, running: bool) -> List[Any]:
        m = vendored().models
        agent = self.view.agents.get(event.agent_id)
        task = agent.task if agent is not None else event.agent_id
        stopped = ""
        if running:
            status: Any = m.RunningSessionStatus(active_turn_id=TURN_ID)
        else:
            state = getattr(event, "state", "met")
            status = (m.IdleSessionStatus() if state in ("met", "not_started", "stopped")       # a stopped helper stays in the list (an archived one would leave it) and is named as stopped
                      else m.FailedSessionStatus(message="did not meet its goal" if state == "unmet" else "failed"))
            stopped = " (stopped)" if state == "stopped" else ""
        old = self.children.get(event.agent_id)
        child = m.PublicChildSession(id=event.agent_id, name=present.helper_name(task, 22) + stopped, agent_type=(agent.solution if agent else "") or "helper", status=status,
                                     created_at=old.created_at if old is not None else stamp(event), updated_at=stamp(event))
        self.children[event.agent_id] = child
        return [vendored().events.ChildSessionUpdated(child_session=child)]

    def asked(self, event: Waiting) -> Any:
        """The open question as a callback entry: an approval (approve or refuse, with what will change) or, for other options, a question."""
        m, d, q = vendored().models, vendored().display, vendored().questions
        helper = self.helper_name(event.agent_id)
        title = event.question + (f" ({helper} asks)" if helper else "")
        options = tuple(event.options or ())
        self.asked_options[event.ask_id or "ask"] = options
        if set(options) <= {"approve", "refuse"}:
            effect = m.GenericEffectDetail(tool_name=short(present.one_line(event.risky) or "action", 30), input={"preview": event.preview} if event.preview else None,
                                           display=d.EffectCallDisplay(summary=title, content=event.preview or None, status_text="Waiting for you"))
            detail: Any = m.ApprovalCallbackDetail(effect=effect, choices=[m.ApprovalDecisionType.APPROVE, m.ApprovalDecisionType.DENY], reason=title)
        else:
            request = q.UserQuestionRequest(questions=[q.UserQuestion(question=title, options=[q.QuestionChoice(label=o) for o in options] * (2 if len(options) < 2 else 1))])
            detail = m.UserInputCallbackDetail(request=request)
        return m.PublicCallbackEntry(**self.base(event, event.ask_id or "ask"), callback_id=event.ask_id or "ask", title=title, detail=detail, state=m.OpenCallbackState())

    # --- what only the hub has -------------------------------------------------------------------------------------------------------

    def closing(self, width: int = 0) -> Optional[Closing]:
        """The end of the run: the answer once, then the quiet detail, the outcome line and the command that resumes it, from the shared closing rules."""
        done = self.view.final
        if done is None:
            return None
        self.view.final = replace(done, report="")
        try:
            body, tail = report_parts(self.view, color=False, width=width)
        finally:
            self.view.final = done
        resume = tuple(present.resume_lines(self.view))
        outcome = tuple(row for row in tail if row and row not in resume)
        return Closing(answer=done.report.strip(), detail=tuple(body), outcome=outcome, resume=resume, state=present.state_of(self.view))


def hint_of(status: str) -> str:
    """The key line for a state of the run: whole hints only, the last ones dropped first on a narrow screen."""
    return {"waiting": present.TEXT["keys_waiting"], "stopping": present.TEXT["keys_stopping"], "stopped": present.TEXT["keys_stopped"],
            "idle": present.TEXT["prompt_goal_enter"] + " | / for commands | ? keys"}.get(status, present.TEXT["keys_default"])


def figures_of(view: SessionView, width: int, title: str = "", running: bool = False, notes: int = 0) -> Figures:
    """The header, key line, status line and structure rows from the view (the shared rules: ``present.header``, the structure rows the driver keeps)."""
    status = present.join([present.count_text(view.calls, "call"), present.count_text(view.tokens, "token")])
    structure = tuple(view.structure_panel) if view.show_structure and view.structure_panel else (
        (present.TEXT["structure"] + ": " + view.structure_compact,) if view.structure_compact else ((f"Serves: {view.solution} | Milestone: {short(view.milestone, 50)}",) if view.solution or view.milestone else ()))
    activity = tuple(present.activity_rows(view, max(width - 4, 20)))       # this screen draws no step of its own as a row: what is happening now is one compact block above the input
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import HELP_ROWS
    room = max(width - 4 - len(status), 20)         # the key line shares its row with the status line: whole hints only
    crumb = (agent_focus.breadcrumb(view, view.focus, max(width - 2, 20)),) if view.focus.path else ()      # where the person is: one row, the same at every depth
    keys = agent_focus.keys_hint(view, view.focus, view.key_labels) if view.status == "running" else ""
    return Figures(header=present.header(view, max(width - 1, 20), False, view.segments, title), hint=present.fit_parts(keys or hint_of(view.status), room), status=status,
                   structure=crumb + activity + structure, help=tuple(HELP_ROWS) if view.show_help else (), running=running and view.status in ("running", "waiting", "stopping"),
                   asking=view.asking is not None, stopped=view.status == "stopped" and not running, note_count=notes)


__all__ = ["AskClosed", "Closing", "Figures", "GoalSent", "HubLine", "NoteSent", "NoteTakenUp", "ScreenAdapter", "figures_of", "hint_of", "vendored"]
