"""The interface of ConnectedOperating: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import runtime_checkable
from esoi import solution
from hubofhubs.the_world.tools.goal_running import GoalRunning


@solution("connected-system-operations", kind="event", entry="run_goal", example={"goal": "create the page Weekly notes in the connected workspace", "brief": "one write operation, then stop"})
@runtime_checkable
class ConnectedOperating(GoalRunning, typing.Protocol):
    """Calls an operation of a connected system (a write through an MCP server today; a consumer declares its own system's operations as
    another arm) and reports the result as a ``DeepResult``."""
