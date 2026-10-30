"""The search port's values: ``SearchHit``, ``SearchResponse`` and ``SearchBackendError``.

The seat Protocol itself is ``hubofhubs.seats.SearchBackend``. These are plain data and one exception, moved out of a
consumer's adapters; they know no search service, no consumer and no network.
"""
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str = ""
    date: str = ""


@dataclass
class SearchResponse:
    hits: List[SearchHit]
    answer: str = ""
    queries_issued: List[str] = field(default_factory=list)


class SearchBackendError(Exception):
    """Raised by a backend's ``search()`` on any failure (HTTP error, bad shape, no results)."""

    def __init__(self, message: str, *, status_code: Optional[int] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
