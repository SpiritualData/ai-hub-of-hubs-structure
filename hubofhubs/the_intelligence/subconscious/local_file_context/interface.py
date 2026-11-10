"""The interface of Local File Context: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, List, Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("local-file-context", kind="event", entry="prepare", example={"goal": "what does the venue cost according to the budget notes?", "root": ".", "budget_chars": 24000})
@runtime_checkable
class LocalFileContexting(typing.Protocol):
    """Makes the files of a local working folder usable as context for a piece of work. ``prepare`` takes the goal, the working folder and a character budget
    and returns ``{"folder_view": FolderChoice}``: the files to show first and the folders left out, each with its reason (Folder View). ``build`` proposes the
    cards a folder's files need, in the card-store record shape (Cards From Files). Both read the folder and write nothing."""

    def prepare(self, goal: str, root: str, budget_chars: int = 100000) -> Mapping[str, Any]: ...
    def build(self, root: str, files: Sequence[str], existing: Mapping[str, Mapping[str, Any]]) -> List[dict]: ...
