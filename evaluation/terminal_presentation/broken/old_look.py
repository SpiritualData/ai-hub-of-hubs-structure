"""A deliberately broken arm: the look the owner pasted on 2026-11-11, written by this arm itself from the same events (the renderers it replaces no longer draw it). A header with
the acronym and a bracketed state, the goal as a ``started:`` line, the harness's lifecycle note, a step as a raw kind word in a column, the interim note shown as a truncated step
next to the full answer, markdown markers left in, a figure line that lost its number, cost to four decimals, ``Changed (0): nothing``, and a resume command wrapped in the middle.
The presentation metric's revision 2 must fail it on its new checks (``terminal_presentation/pasted.py`` is its scenario)."""
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import score  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.session_events import Finished, RunStarted, Step, Usage  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionReport, SessionView  # noqa: E402


class OldLook:
    presentation = "stream"

    def attend(self, harness, goal, out, keys=None, resume_session_id="", tick=0.0, live=None, width=56, **options):
        view, events = SessionView(), []
        write = lambda text, indent=" ", hang="   ": [out.write(row + "\n") for row in textwrap.wrap(text, max(width - 1, 20), initial_indent=indent, subsequent_indent=hang, break_long_words=False) or [""]]

        def sink(event):
            events.append(event)
            view.apply(event)
            if isinstance(event, RunStarted):
                out.write(f"ahohs  {event.harness}  [running]  0:00 of 4:00:00 | $0.0000\n")
                write("Type a goal and press Enter; it runs in this folder. /help lists commands.")
                write(f"[0:00] started: {event.goal} ({event.harness})")
            elif isinstance(event, Step) and event.state == "done":
                write(f"[0:01] ok {event.kind:<8} {event.label}")
            out.flush()
        done = harness.start(goal, sink, resume_session_id)
        out.write("\n")
        for row in done.report.splitlines():
            write(row, " ", " ") if row.strip() else out.write("\n")
        write("Changed (0): nothing")
        write(f" calls | {done.tokens} tokens", "", "")
        write("To continue later, in this folder: ahohs work --resume " + done.session_id + " --harness native", " ", "   ")
        write(f"✓ Done: the goal was met · 0:05 of 4:00:00 · ${done.cost_usd:.4f} of $20.0000 · 2 calls", "", " ")
        out.flush()
        return SessionReport(final=done, runs=(done,), events=tuple(events), controls=(), view=view, text=out.getvalue() if hasattr(out, "getvalue") else "")


def build(meter):
    return score.adapt(OldLook, meter)
