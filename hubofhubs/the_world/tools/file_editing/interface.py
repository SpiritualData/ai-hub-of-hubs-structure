"""The interface of FileEditing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import runtime_checkable
from esoi import solution
from hubofhubs.the_world.tools.goal_running import GoalRunning


@solution("file-editing", kind="event", entry="run_goal", example={"goal": "add a line to NOTES.md", "brief": "one line, then stop"})
@runtime_checkable
class FileEditing(GoalRunning, typing.Protocol):
    """Changes a file by instruction and reports what changed (a ``DeepResult``). Every arm of this seat does that one job: a one-call
    model edit today, and exact string replacement or patch formats as researched candidates with no arm yet."""
