"""A plain line REPL over the terminal blocks: read a line, run it through the front door, draw the run's events.

``LineRepl().converse(front_door, lines, out)`` is the whole loop and takes its input and output as arguments, so a script, a test and the ``ahohs chat``
command are one call. ``front_door(text)`` is what answers a line and returns a result with ``answer``, ``events`` and ``note``
(``hubofhubs.run`` bound to the whole hub, exactly as ``ahohs run`` calls it). A run that cannot start raises ``esoi.Pending`` and its
lines are shown. Lines starting with ``/`` are commands: ``/help``, ``/quit``, ``/trail`` (show or hide the work behind each reply),
``/later`` (fold an open ask, nothing is answered). While an ask is open the next line is its answer (``parse_answer``: a number picks an
option, anything else is free text) and goes to the front door as the next message. The front door takes one input and no history, so
none is kept. The session ends on ``/quit``, end of input or Ctrl-C. Standard library only.
"""
from __future__ import annotations

import sys
import time
from types import SimpleNamespace
from typing import Any, Callable, Iterable, Optional, TextIO

from esoi import EntryError, Pending, implementation

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.structure_lines import structure_lines
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionReport, SessionView, event_line, report
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import TerminalState, answer_ask, close_ask, fold_ask, render, settle, to_text

HELP = "\n".join((
    "Type a message and press Enter to run it through the hub.",
    "/help   show this list",
    "/trail  show or hide the work behind each reply",
    "/later  fold an open question without answering it",
    "/quit   leave (Ctrl-D or Ctrl-C also leave)",
    "When a question is open, your next line answers it (a number picks an option).",
))
#: Blocks drawn while the turn runs; the rest (the live line, folded rows) are drawn once by ``settle``.
LIVE_KINDS = ("interim", "ask")
SETTLED_KINDS = ("trail_summary", "stopped", "ask")


def show(out: TextIO, blocks: Iterable[Any], kinds: Iterable[str]) -> None:
    kept = [b for b in blocks if b.kind in kinds and not b.removed]
    text = to_text(kept)
    if text:
        out.write(text + "\n")


def turn(front_door: Callable[[str], Any], text: str, state: TerminalState, trail_on: bool, out: TextIO, number: int) -> None:
    try:
        result = front_door(text)
    except Pending as pending:
        out.write(f"needs setup: {pending}\n")
        return
    except EntryError as error:
        out.write(f"failed: {error}\n")
        return
    state.new_turn(f"turn-{number}")
    if trail_on:
        state.trail_view = "open"
    for event in getattr(result, "events", ()):
        show(out, render(event, state), LIVE_KINDS)
    answer = str(getattr(result, "answer", "") or "")
    if answer:
        out.write(answer + "\n")
    note = str(getattr(result, "note", "") or "")
    if note:
        out.write(f"({note})\n")
    show(out, settle(state), SETTLED_KINDS)


@implementation("terminal-session", "line_repl")
class LineRepl:
    """A plain line REPL: prompt, read a line, run it, draw it; commands start with a slash."""
    REQUIRES = ()     # the seats it is handed

    def structure_lines(self, view: Any, width: int = 100) -> list:
        """The solutions the AI is working on, one line each, with the fields of the expanded ones (see ``structure_lines.py``)."""
        return structure_lines(view, width)

    def converse(self, front_door: Optional[Callable[[str], Any]] = None, lines: Iterable[str] = (), out: Optional[TextIO] = None, viewer_id: str = "", prompt: str = "> ") -> int:
        """Run the REPL until /quit, end of input or Ctrl-C. Returns 0."""
        out = out if out is not None else sys.stdout                # a terminal with no stream given writes to the standard one
        if front_door is None:                                       # nothing to answer with: say so for each line, never make an answer up
            front_door = lambda text: SimpleNamespace(answer="No front door was given to this terminal, so nothing answers.", events=[], note="")
        state = TerminalState(viewer_id=viewer_id)
        trail_on = False
        number = 0
        out.write("ahohs chat: type /help for commands, /quit to leave.\n")
        iterator = iter(lines)
        try:
            while True:
                out.write(prompt)
                out.flush()
                try:
                    line = next(iterator)
                except StopIteration:
                    out.write("\n")
                    break
                text = line.strip()
                if not text:
                    continue
                if text in ("/quit", "/exit"):
                    break
                if text == "/help":
                    out.write(HELP + "\n")
                elif text == "/trail":
                    trail_on = not trail_on
                    out.write(f"Trail {'on' if trail_on else 'off'}.\n")
                elif text == "/later":
                    if state.ask is None:
                        out.write("Nothing is waiting on you.\n")
                    else:
                        show(out, fold_ask(state), ("ask",))
                elif text.startswith("/"):
                    out.write(f"Unknown command {text.split()[0]}. Type /help.\n")
                else:
                    if state.ask is not None and not state.ask_folded:
                        answered = answer_ask(state, text)
                        if answered is None:
                            out.write("That answer cannot be used. Try again, or /later.\n")
                            continue
                        text = answered.response_text
                        show(out, close_ask(state), ("ask",))
                    number += 1
                    turn(front_door, text, state, trail_on, out, number)
        except KeyboardInterrupt:
            out.write("\n")
        out.write("Goodbye.\n")
        return 0

    def attend(self, harness: Any, goal: str, out: TextIO, keys: Any = None, resume_session_id: str = "", clock: Callable[[], float] = time.monotonic,
               tick: float = 0.02, live: Any = None, width: int = 0) -> SessionReport:
        """The plain way to watch a run: run it to its end on this thread, write each event as a line, then the closing report. No key is read, so the
        run cannot be stopped, steered or answered while it works (a question waits for its harness to give up)."""
        view = SessionView()
        view.started = view.now = clock()
        events = []

        def sink(event: Any) -> None:
            events.append(event)
            view.now = clock()
            view.apply(event)
            line = event_line(event, view)
            if line:
                out.write(line + "\n")
        done = harness.start(goal, sink, resume_session_id)
        for row in report(view):
            out.write(row + "\n")
        return SessionReport(final=done, runs=(done,), events=tuple(events), controls=(), view=view, text=out.getvalue() if hasattr(out, "getvalue") else "")
