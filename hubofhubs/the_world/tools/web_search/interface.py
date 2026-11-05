"""The interface of SearchBackend: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Optional, runtime_checkable
from esoi import solution
from hubofhubs.the_world.tools.web_search.search_port import SearchResponse


@solution("web-search", kind="event", entry="search", example="latest Rust version")
@runtime_checkable
class SearchBackend(typing.Protocol):
    """Runs one web search and returns a ``SearchResponse`` (hits with title, url, snippet, date, the separate ``passages`` and
    their ``passage_kind``; an optional direct answer; the queries issued); raises ``SearchBackendError`` on failure. An arm also
    carries a ``name`` attribute (the chain's label). ``instruction`` is the caller's own wording for a model-backed arm (for
    example "include facts that count against the claim"); an arm that is not model-backed accepts it and ignores it.
    External system: the hub ships arms, the consumer may provide its own."""

    def search(self, query: str, *, max_results: int = 5, instruction: Optional[str] = None) -> SearchResponse: ...
