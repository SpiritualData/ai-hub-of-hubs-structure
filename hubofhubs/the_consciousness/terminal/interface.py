"""The interface of Conversing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Iterable, TextIO, runtime_checkable
from esoi import solution


@solution("terminal-session", kind="event", entry="converse", example={"lines": ["/quit"]})
@runtime_checkable
class Conversing(typing.Protocol):
    """Lets a person talk to the hub in a plain terminal: it reads a person's lines, runs each through the front door it is given, and draws the
    work summary, the interim updates and any question the hub puts to the person, with the commands to see more or leave. An open question takes
    the person's next line as its answer. It ends on a quit command, end of input or an interrupt and returns the exit code (0 for a clean end)."""

    def converse(self, front_door: Callable[[str], Any], lines: Iterable[str], out: TextIO, viewer_id: str = "", prompt: str = "> ") -> int: ...
