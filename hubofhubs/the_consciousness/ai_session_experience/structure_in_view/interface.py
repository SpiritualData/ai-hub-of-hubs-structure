"""The interface of Structure In View: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("structure-in-view", kind="event", entry="view", example={"events": [{"type": "run-started", "goal": "improve the plan", "solution": "the-mind"}],
                                                                     "expanded": []})
@runtime_checkable
class StructureViewing(typing.Protocol):
    """Shows how ESOI is involved in what the AI is doing, as plain data any interface can draw. ``events`` are the session's events (objects or their
    ``to_dict`` form); ``agent-started`` and ``agent-ended`` carry the solution a sub-agent works on. ``records`` is the ESOI records root (or the tables read
    from it) the solutions are looked up in; without it a solution is shown by its id and marked unknown. The result is ``{"tree": [...], "unplaced": [...],
    "unknown": [...], "expanded": [...]}``: a tree of solution nodes (id, name, state, the agents on it, their latest activity, the children), collapsed
    by default. A solution id in ``expanded`` (or ``"*"`` for all) also carries ``detail``: its fields (purpose, approach, metric and its latest value,
    selected implementation, milestones) and its connections (problems, ideals, delegates) with their fields. Reads records, writes nothing."""

    def view(self, events: Sequence[Any], records: Any = None, expanded: Sequence[str] = ()) -> Mapping[str, Any]: ...
