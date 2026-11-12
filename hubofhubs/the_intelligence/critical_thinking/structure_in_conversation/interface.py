"""The interface of StructureInConversation: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("structure-in-conversation", kind="event", entry="decide", example={"turn": {"move": "none"}})
@runtime_checkable
class StructureInConversation(typing.Protocol):
    """Decides what structure a reply to one conversational turn carries: given the move the turn calls for and the records the system holds, answers the
    structure block the reply is written from (and a caller shows), and at most one offer to keep the missing pieces as one batch of ensure-one edits."""

    def decide(self, turn: Mapping[str, Any]) -> Mapping[str, Any]: ...
