"""The interface of FolderViewing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution
from hubofhubs.the_intelligence.subconscious.folder_view.choice import FolderChoice


@solution("folder-view", kind="event", entry="choose", example={"goal": "what does the venue cost according to the budget notes?", "context": "", "root": ".",
                                                                 "budget_chars": 24000})
@runtime_checkable
class FolderViewing(typing.Protocol):
    """Chooses which files of a working folder a piece of work should be shown before it starts, and which folders it leaves out. ``choose`` takes
    the goal text, the context text, the folder and a character budget and returns a ``FolderChoice``: ``picks`` best first (a relative path and the
    reason for each; a file the goal names inside a risky folder comes back flagged and is not to be shown unasked), ``left_out`` (each folder, or risky
    file, not scanned, with the reason) and ``skipped`` (counts of files passed over one by one). ``trail`` is the ranked files earlier runs of the same
    work used (``{path, runs, changed}``); ``file_limit`` caps the files scanned. It reads the folder and writes nothing."""

    def choose(self, goal: str, context: str, root: str, budget_chars: int = 100000, trail: Sequence[Mapping[str, Any]] = (),
               file_limit: int = 5000) -> FolderChoice: ...
