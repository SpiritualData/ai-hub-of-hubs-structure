"""The interface of ContextRetrieval: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("context-retriever", kind="event", entry="retrieve", example={"query": "where is the retry delay computed?", "files": {"net.py": "def retry_delay(attempt):\n    return 2 ** attempt\n", "ui.py": "def draw():\n    pass\n"}})
@runtime_checkable
class ContextRetrieval(typing.Protocol):
    """Picks, from a corpus of files, the pieces of text a task needs and returns them best first within a token budget (a list of hits: unit
    id, file, first line, score, tokens). An empty list means the arm judged that no context is needed. The corpus is passed as files (path to
    text), with an optional history of past changes (date, subject, files) that arms may learn from; an arm indexes a corpus once and keeps it."""

    def retrieve(self, query: str, files: Optional[Mapping[str, str]] = None, budget_tokens: int = 4000, history: Sequence[Mapping[str, Any]] = ()) -> Sequence[Any]: ...
