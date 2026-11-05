"""The interface of JudgmentCalling: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("judgment-calls", kind="event", entry="decide", example={"signal": {"signal": "proceed"}, "person": ""})
@runtime_checkable
class JudgmentCalling(typing.Protocol):
    """Decides for one person whether to ask, proceed or decline on a risk signal (severity and reason) or on a flow that stopped (``context``
    carries ``stopped``: budget or authority); the decision may be to a human, another agent or a delegate. It also owns ask timing: whether the
    ask blocks or waits, whether it is batched, and what may continue meanwhile. It decides, too, whether a change to specs or learning needs an ask."""

    def decide(self, signal: Mapping[str, Any], person: str = "", context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
