"""What the polished screen says, as plain functions of a ``SessionView`` (no screen library in here, so every rule is testable without a terminal).

Every decision reads a structured field (``Finished.outcome``, a step's state, an agent's state, the count of messages), never the words of the worker's report. One clock
(``hub_lines.clock``, ``m:ss``) is the only way a time is written: the header, the work panel, the transcript stamps and the closing line. A wait shows its clock only once
it passes ``CLOCK_AFTER`` seconds. Standard library and the hub only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_consciousness.ai_session_experience.session_events import MAIN, Finished, Step, short
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import hub_lines
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.words import say
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionView, money, report_parts, step_row

CLOCK_AFTER = 3          # a wait shorter than this shows no clock: a counter on every instant step would be noise
GOAL_CHARS = 160
STEP_CHARS = 70
NOTE = "note"
YES = ("y", "yes", "approve")
NO = ("n", "no", "refuse")
SGR = re.compile(r"\x1b\[[0-9;]*m")


def clock(seconds: float) -> str:
    """The one way an elapsed time is written."""
    return hub_lines.clock(seconds)


def ellipsize(text: str, limit: int) -> str:
    """``text`` on one line, at most ``limit`` characters, cut at a word where it can and ended with an ellipsis."""
    one = " ".join(str(text or "").split())
    if len(one) <= limit:
        return one
    cut = one[:max(limit - 1, 1)]
    if " " in cut and len(cut.rsplit(" ", 1)[0]) >= limit * 0.6:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-") + "…"


def plain(text: str) -> str:
    return SGR.sub("", text)


# --- the placeholder, the activity bar and the header -------------------------------------------------------------------------------

def newline_hint(environ: Mapping[str, str]) -> str:
    """The newline keys to advertise: a VTE terminal sends Shift+Enter as Enter, so only the keys that reach the prompt are named."""
    return say("polished.prompt.newlineVte" if environ.get("VTE_VERSION") else "polished.prompt.newline")


def placeholder(state: str, environ: Optional[Mapping[str, str]] = None) -> str:
    """The prompt's hint: ``ready``, ``busy`` (names the key that stops the work), ``asking`` or ``stopped``."""
    if state == "busy":
        return say("polished.prompt.busy")
    if state == "asking":
        return say("polished.prompt.asking")
    if state == "stopped":
        return say("polished.prompt.stopped")
    return say("polished.prompt.ready", newline=newline_hint(environ or {}))


def prompt_state(view: SessionView, running: bool) -> str:
    if view.asking is not None:
        return "asking"
    if running and view.status in ("running", "stopping", "waiting"):
        return "busy"
    if view.status == "stopped":
        return "stopped"
    return "ready"


def activity_text(view: SessionView) -> str:
    """What the AI is doing now, from the newest running step (a status that is true), or a plain fallback."""
    if view.status == "stopping":
        return say("polished.activity.stopping")
    if view.asking is not None:
        return say("polished.activity.waiting")
    running = [s for s in view.steps.values() if s.state == "running" and s.kind != "message-received"]
    if running:
        step = running[-1]
        key = f"polished.activity.{step.kind}" if step.kind in ("read", "edit", "run", "check", "tool", "delegate", "note") else "polished.activity.note"
        return say(key, label=short(step.label, 50))
    return say("polished.activity.working")


def waiting_notes(view: SessionView, held: int = 0) -> int:
    """How many notes the person typed that the work has not taken up yet."""
    return sum(1 for message in view.messages if not message.taken_up) + held


def header_text(view: SessionView, title: str = "", segments: Sequence[str] = (), width: int = 0) -> str:
    """The header, from the shared rule (``present.header``): the product's full name, the worker, the state as a glyph, the time and cost right-aligned."""
    return present.header(view, width, False, segments, title)


def key_hints(*, busy: bool, asking: bool, stopped: bool, runs: int, detail: bool, structure: bool) -> List[Tuple[str, str]]:
    """The keys worth showing now, most useful first, only those that would do something: Esc only while the AI works, Tab only with more than one run, Ctrl+C only when idle."""
    hints: List[Tuple[str, str]] = []
    if asking:
        hints.append(("y/n", say("polished.key.answer")))
    if busy:
        hints.append(("esc", say("polished.key.stop")))
    if stopped:
        hints.append(("alt+k", say("polished.key.resume")))
    if runs:
        hints.append(("alt+d", say("polished.key.details")))
    if runs > 1:
        hints.append(("tab", say("polished.key.nextRun")))
    if structure:
        hints.append(("alt+t", say("polished.key.structure")))
    hints.append(("pgup/pgdn", say("polished.key.scroll")))
    if not busy:
        hints.append(("ctrl+c", say("polished.key.quit")))
    return hints


def fit_hints(hints: Sequence[Tuple[str, str]], room: int) -> List[Tuple[str, str]]:
    """As many whole hints as fit ``room`` columns, never a key cut in half."""
    out: List[Tuple[str, str]] = []
    used = 0
    for key, label in hints:
        need = (2 if out else 0) + len(key) + 1 + len(label)
        if used + need > room:
            break
        out.append((key, label))
        used += need
    return out


# --- the work panel -----------------------------------------------------------------------------------------------------------------

@dataclass(frozen=True)
class Run:
    """One run on the panel: the main run, or a helper still working."""
    agent_id: str
    title: str


def runs_of(view: SessionView) -> List[Run]:
    """The runs a person can open: the main run while it lasts, then each helper that is still running."""
    runs: List[Run] = []
    if view.final is None:
        runs.append(Run(MAIN, ellipsize(view.goal, GOAL_CHARS) or say("polished.work.untitled")))
    for agent in view.agents.values():
        if agent.state == "running":
            runs.append(Run(agent.agent_id, ellipsize(agent.task, GOAL_CHARS) + (f" ({agent.solution})" if agent.solution else "")))
    return runs


def lines_per_run(count: int) -> int:
    """Output rows per run: calm for one, tighter as runs are added, so the block does not balloon."""
    return 3 if count <= 1 else (2 if count == 2 else 1)


def step_text(step: Step) -> str:
    return f"{step.kind} {short(step.label, STEP_CHARS)}"


def dashboard(view: SessionView, active: str = "", extra: Sequence[str] = ()) -> Tuple[List[Tuple[str, str]], Dict[int, str]]:
    """The calm per-run block: ``([(row, kind)], {row index: run id})``. A run is its title, its clock and status, and the steps running now (the finished ones are in the transcript,
    so each update has one home). ``kind`` is ``head``, ``open`` (the run the detail shows), ``clock``, ``step`` or ``hint``. Empty when nothing runs."""
    runs = runs_of(view)
    if not runs:
        return [], {}
    each = lines_per_run(len(runs))
    rows: List[Tuple[str, str]] = []
    line_map: Dict[int, str] = {}
    now = clock(view.elapsed())
    status = say("polished.work.asking") if view.asking is not None else say("polished.work.stopping") if view.status == "stopping" else say("polished.work.running")
    for run in runs:
        start = len(rows)
        rows.append((f"{'▾' if run.agent_id == active else '▸'} {run.title}", "open" if run.agent_id == active else "head"))
        rows.append((f"  ● {now}  {status}", "clock"))
        steps = [s for s in view.steps.values() if s.state == "running" and s.agent_id == run.agent_id and s.kind != "message-received"]
        for step in steps[-each:]:
            rows.append((f"  → {step_text(step)}" if "/" in step.label else f"    {step_text(step)}", "step"))
        for index in range(start, len(rows)):
            line_map[index] = run.agent_id
    rows.extend((row, "step") for row in extra)
    rows.append(("  " + say("polished.work.openMany" if len(runs) > 1 else "polished.work.open"), "hint"))
    return rows, line_map


def history_lines(view: SessionView, agent_id: str, stamps: bool = True) -> List[str]:
    """Everything one run did, in order, newest last: the detail panel's body."""
    out = []
    for step in view.steps.values():
        if step.agent_id != agent_id:
            continue
        out.append((f"[{clock(step.at)}] " if stamps else "") + step_row(step))
    return out


# --- what the person typed while the AI worked --------------------------------------------------------------------------------------

def is_note(text: str, *, running: bool, stopping: bool, asking: bool) -> bool:
    """True when a typed line is a note for the AI (not a command, a helper address, an answer or a control word)."""
    word = text.strip().lower()
    if not word or not running or stopping or word.startswith(("/", "@")) or word in ("?", "resume", "quit", "exit"):
        return False
    return not (asking and word in YES + NO)


def combine_notes(notes: Sequence[str]) -> str:
    """Several notes as one next message, in the order they were typed."""
    return "\n\n".join(note.strip() for note in notes if note and note.strip())


def leftover_notes(unsent: Sequence[str], unseen: Sequence[str], held: Sequence[str]) -> List[str]:
    """The notes no run took up, once each, in the order they were typed (held first, then those the harness gave back)."""
    out: List[str] = []
    for note in list(held) + list(unsent) + list(unseen):
        if note and note.strip() and note not in out:
            out.append(note)
    return out


def pickup_line(count: int) -> str:
    return say("polished.note.pickedUp", count=count)


def flush_line(count: int) -> str:
    return say("polished.note.flushed", count=count)


def back_in_box_line(count: int) -> str:
    return say("polished.note.back", count=count)


# --- the end of a run ---------------------------------------------------------------------------------------------------------------

def outcome_of(view: SessionView) -> str:
    """How the run ended, from the structured outcome only (never from the report's words)."""
    return view.final.outcome if view.final is not None else ""


def closing_line(view: SessionView, color: bool = False) -> str:
    """The one closing line, the same shape for every run (``present.outcome_line``): how it ended, the time, the cost, the calls and the files; a missing figure leaves its segment out."""
    return present.outcome_line(view, color)


def closing_rows(view: SessionView, color: bool = False, width: int = 0) -> Tuple[List[str], List[str]]:
    """``(above, closing)``: the metric before and after once (first, so it sits right under the answer), then the quiet detail the hub's report holds (what was served, what changed,
    what was blocked, the helpers, what is left), and last the closing: the one outcome line and the command that resumes, alone on its own line. The answer itself is left to the
    screen to draw."""
    done = view.final
    if done is None:
        return [], [closing_line(view, color)]
    stub = Finished(**{**done.__dict__, "report": ""})
    kept = view.final
    view.final = stub
    try:
        body, tail = report_parts(view, color=color, width=width)
    finally:
        view.final = kept
    metric = [r for r in body if plain(r).startswith("Metric ")]
    detail = [r for r in body if r.strip() and r not in metric]
    return metric + detail, tail


__all__ = ["CLOCK_AFTER", "Run", "activity_text", "back_in_box_line", "clock", "closing_line", "closing_rows", "combine_notes", "dashboard", "ellipsize", "fit_hints",
           "flush_line", "header_text", "history_lines", "is_note", "key_hints", "leftover_notes", "lines_per_run", "newline_hint", "outcome_of", "pickup_line",
           "placeholder", "plain", "prompt_state", "runs_of", "waiting_notes"]
