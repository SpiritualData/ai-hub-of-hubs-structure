"""The interface of AgentSessions: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import runtime_checkable
from esoi import solution
from hubofhubs.the_world.tools.goal_running import GoalRunning


@solution("delegated-agent-sessions", kind="event", entry="run_goal", example={"goal": "read notes.txt and tell me which city the meeting is in", "brief": "read the file, then report the city"})
@runtime_checkable
class AgentSessions(GoalRunning, typing.Protocol):
    """Hands open-ended work to an agent that runs in its own session and reports back (a ``DeepResult``). The three arms are Claude Code
    agents, which are coding-oriented agents used as general ones; a general agent not tied to coding is a researched candidate with no arm yet."""
