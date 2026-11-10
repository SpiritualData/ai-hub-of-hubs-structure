"""The interface of AI Session Experience: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Iterable, Mapping, Sequence, TextIO, runtime_checkable
from esoi import solution


@solution("ai-session-experience", kind="event", entry="present", example={"events": [{"type": "run-started", "goal": "improve the plan", "solution": "the-mind"}]})
@runtime_checkable
class SessionExperiencing(typing.Protocol):
    """Lets a person work with the AI while it works, on any surface, through one event and control contract that any harness satisfies. ``present`` takes
    the session's events (objects or dicts), optionally the ESOI records root and the solution ids to expand, and returns the three views of the same
    session: ``structure`` (the solutions being worked on, collapsed unless expanded), ``frontend`` (plain data for a separate frontend) and ``terminal`` (the
    structure as lines). ``converse`` is the interactive terminal entry: it reads a person's lines, runs each through the front door and draws the work."""

    def present(self, events: Sequence[Any], records: Any = None, expanded: Sequence[str] = (), controls: Sequence[Any] = (), width: int = 100) -> Mapping[str, Any]: ...
    def converse(self, front_door: Callable[[str], Any], lines: Iterable[str], out: TextIO, viewer_id: str = "", prompt: str = "> ") -> int: ...
