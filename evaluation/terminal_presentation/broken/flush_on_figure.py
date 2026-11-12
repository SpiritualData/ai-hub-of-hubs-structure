"""A deliberately broken arm: the full-screen Textual terminal with the OLD interim-note rule of the shared view (a held note was shown or dropped by the very next event, so the figure updates
a real harness sends between its note and its finish made it show the answer twice: the note cut with three dots, then the closing). The recorded real run (``real_run`` scenario) must fail it
on ``answer-once``; the shared rule now holds the note until a row that draws something."""
import dataclasses
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import score  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.session_events import Finished, Step  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import live, present, session_view, textual_session  # noqa: E402


@dataclasses.dataclass
class OldView(session_view.SessionView):
    pending_note: str = ""


def old_event_line(event, view, panel=False):
    if isinstance(event, Step) and event.kind == "note":
        if present.is_lifecycle(event):
            return ""
        text, held = present.one_line(event.label), view.pending_note
        view.pending_note = text
        return held if held and not (present.is_the_answer(text, held) or present.is_the_answer(held, text)) else ""
    own = session_view.row_of(event, view, panel)
    held, view.pending_note = view.pending_note, ""
    if held and isinstance(event, Finished) and present.is_the_answer(held, event.report):
        held = ""
    return "\n".join(row for row in (held, own) if row)


class FlushOnFigure(textual_session.TextualSession):
    def attending(self, *args, **kwargs):
        keep = live.event_line, live.SessionView, textual_session.SessionView
        live.event_line, live.SessionView, textual_session.SessionView = old_event_line, OldView, OldView
        try:
            return super().attending(*args, **kwargs)
        finally:
            live.event_line, live.SessionView, textual_session.SessionView = keep


def build(meter):
    return score.adapt(FlushOnFigure, meter)
