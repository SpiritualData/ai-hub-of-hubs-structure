"""The interface of GoalRunning: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Callable, Optional
from hubofhubs.the_world.tools.deep import DeepResult, ProgressEvent


class GoalRunning(typing.Protocol):
    """What the arms of the three goal-running tools share: take a goal with a written done-standard and try to bring it about, then return
    a ``DeepResult`` that says whether the goal was met. Never raises: a refusal or failure comes back as ``met=False`` with the reason, and
    nothing is changed when it declines. An arm also carries ``write_surface`` (what kind of change it can make: files, operations or an
    agent) and may stream ``ProgressEvent`` rows through ``emit``. The model it needs and the writer it is granted (``FileWriter``,
    ``OperationWriter``) are constructor arguments the consumer provides."""

    def run_goal(self, *, goal: str, brief: str, model: Optional[str] = None, max_turns: Optional[int] = None,
                 emit: Optional[Callable[[ProgressEvent], None]] = None, context_preamble: Optional[str] = None,
                 run_id: Optional[str] = None) -> DeepResult: ...
