"""The interface of Conversing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Iterable, TextIO, runtime_checkable, Optional

from hubofhubs.the_consciousness.ai_session_experience.session_events import Harness
from esoi import solution


@solution("terminal-session", kind="event", entry="converse", example={"lines": ["/quit"]})
@runtime_checkable
class Conversing(typing.Protocol):
    """Lets a person talk to the hub in a plain terminal: it reads a person's lines, runs each through the front door it is given, and draws the
    work summary, the interim updates and any question the hub puts to the person, with the commands to see more or leave. An open question takes
    the person's next line as its answer. It ends on a quit command, end of input or an interrupt and returns the exit code (0 for a clean end)."""

    def converse(self, front_door: Optional[Callable[[str], Any]] = None, lines: Iterable[str] = (), out: Optional[TextIO] = None, viewer_id: str = "", prompt: str = "> ") -> int: ...

    def structure_lines(self, view: Any, width: int = 100) -> list:
        """The result of Structure In View as plain lines: one per solution while collapsed, the fields and connections only of an expanded one."""
        ...

    def attend(self, harness: Harness, goal: str, out: TextIO, keys: Any = None, resume_session_id: str = "", **options: Any) -> Any:
        """Run ``goal`` on any ``Harness`` while the person watches. A live arm reads keys: Escape or Ctrl-C stops and keeps the session, ``resume`` continues
        it, a typed line steers and is shown as taken up, ``y`` or ``n`` answers a question. It returns a ``SessionReport`` (the last ``Finished``, every run,
        all events, the controls sent and whether each was taken, and the text written)."""
        ...
