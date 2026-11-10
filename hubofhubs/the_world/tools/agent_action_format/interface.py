"""The interface of ActionFormat: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, List, Mapping, Optional, runtime_checkable
from esoi import solution


@solution("agent-action-format", kind="event", entry="execute", example={"reply": "READ: README.md", "working_dir": "."})
@runtime_checkable
class ActionFormat(typing.Protocol):
    """Turns what a model wrote as its actions into effects in a folder: the words of the action are a format, and a model does best in the format it was
    trained on. Returns one outcome per action (``kind``, ``ok``, ``text``), in the order the model wrote them."""

    def execute(self, reply: str, working_dir: str, environment: Optional[Mapping[str, str]] = None) -> List[Mapping[str, Any]]: ...
