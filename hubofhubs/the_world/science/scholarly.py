"""The scholarly port's values: ``Work``, ``ScholarlyError`` and ``WorksResult``.

Plain data, no network and no consumer. An arm that searches the research literature (``hubofhubs.science``) returns a
``WorksResult``: either works with the fields a citation needs, or one typed error. It never raises for a service failure.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Work:
    """One scholarly work as a service reported it. Empty means the service did not say; nothing here is filled in."""
    title: str
    authors: Tuple[str, ...] = ()
    year: Optional[int] = None
    venue: str = ""
    doi: str = ""                 # bare, e.g. "10.1234/abc"; empty when the service has none
    url: str = ""                 # a landing page (http or https only); empty when the service gave none that is a web link
    cited_by_count: int = 0
    abstract: str = ""            # rebuilt text, empty when the service holds none
    open_access: Optional[bool] = None
    oa_status: str = ""
    work_id: str = ""             # the service's own id
    source: str = ""              # which service answered ("openalex", "crossref")
    retracted: Optional[bool] = None   # True when the service knows the work was retracted; None when it did not say

    @property
    def doi_url(self) -> str:
        return f"https://doi.org/{self.doi}" if self.doi else ""

    @property
    def link(self) -> str:
        """The link a citation points at: the DOI link when there is a DOI, else the landing page."""
        return self.doi_url or self.url


@dataclass(frozen=True)
class ScholarlyError:
    """Why a lookup returned no works. ``kind`` is one of: ``rate_limited``, ``budget`` (a daily allowance, the service's or
    the caller's), ``key_not_activated``, ``unauthorized``, ``bad_request``, ``not_found``, ``server``, ``timeout``,
    ``network``, ``bad_response``, ``missing_dependency``, ``not_a_doi``."""
    kind: str
    message: str
    status_code: Optional[int] = None
    retry_after: Optional[float] = None


@dataclass
class WorksResult:
    works: List[Work] = field(default_factory=list)
    total: int = 0                          # how many works the service says match (may exceed ``len(works)``)
    query: str = ""
    source: str = ""
    cost_usd: Optional[float] = None        # what the call cost, when the service reports it
    remaining_usd: Optional[float] = None   # what is left of today's allowance, when the service reports it
    error: Optional[ScholarlyError] = None
    cached: bool = False

    @property
    def ok(self) -> bool:
        return self.error is None
