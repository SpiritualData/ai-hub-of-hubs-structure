"""The search port's values: ``SearchHit``, ``SearchResponse`` and ``SearchBackendError``.

The seat Protocol itself is ``hubofhubs.seats.SearchBackend``. These are plain data and one exception, moved out of a
consumer's adapters; they know no search service, no consumer and no network.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

PASSAGE_KINDS = ("verbatim", "attributed", "snippet")


@dataclass
class SearchHit:
    """One page. ``snippet`` is the first passage (or the backend's existing text) and stays as it always was.

    ``passages`` are the separate passages for the page, uncapped. ``passage_kind`` says what they are, so a consumer that cites
    sources can be honest: ``"verbatim"`` (quoted from the page by the backend, as the model's native search tool does),
    ``"attributed"`` (a sentence a model wrote and tied to the page, as grounding does; never quote it) or ``"snippet"`` (the
    excerpt a search API returns for the page, as the API returned it). Empty when the backend gave no passage or does not say.
    ``date`` is the page date as the backend states it, empty when it has none.
    """
    title: str
    url: str
    snippet: str = ""
    date: str = ""
    passages: Tuple[str, ...] = ()
    passage_kind: str = ""

    def __post_init__(self) -> None:
        self.passages = tuple(self.passages or ())
        if not self.passages and self.snippet and self.passage_kind:
            self.passages = (self.snippet,)


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
