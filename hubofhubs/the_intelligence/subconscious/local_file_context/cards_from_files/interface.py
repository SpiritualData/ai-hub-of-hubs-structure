"""The interface of CardsFromFiles: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, List, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("cards-from-files", kind="event", entry="build", example={"root": ".", "files": [], "existing": {}})
@runtime_checkable
class CardsFromFiles(typing.Protocol):
    """Proposes cards for the files of a folder, in the card-store record shape; writes nothing."""

    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]: ...
    def changed(self, root: str, cards: Mapping[str, Mapping[str, Any]]) -> List[str]: ...
