"""The interface of FileReading: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Mapping, Sequence, runtime_checkable
from esoi import solution


@solution("read-files", kind="event", entry="read", example={"root": ".", "paths": []})
@runtime_checkable
class FileReading(typing.Protocol):
    """Reads and lists the text files of a folder, never outside it: the world-facing half of working with files that Cards From Files builds on."""

    def list(self, root: str, suffixes: Sequence[str] = ()) -> Sequence[str]: ...
    def read(self, root: str, paths: Sequence[str] = ()) -> Mapping[str, str]: ...
