"""The interface of Objectives: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("live-objectives", kind="event", entry="current", example="")
@runtime_checkable
class Objectives(typing.Protocol):
    """The live hierarchy of intents and goals across requests. The system hands over the person's recorded ``objectives`` (each a mapping with ``id``,
    ``title``, an optional ``parent`` id, ``done_when`` (criteria, each with ``text`` and ``met``) and an optional ``met`` flag for one with no criteria);
    the hub holds no store of its own. ``current`` returns the hierarchy in order, each with its ``depth``, ``state`` (not started, in progress or met) and
    ``progress`` rolled up from its criteria and children; ``place`` puts a request under the live objective it serves and returns it with its ``path`` from the
    top, or no objective when none is served."""

    def current(self, person: str = "", objectives: Sequence[Mapping[str, Any]] = ()) -> Sequence[Mapping[str, Any]]: ...
    def place(self, request: str, person: str = "", objectives: Sequence[Mapping[str, Any]] = ()) -> Mapping[str, Any]: ...
