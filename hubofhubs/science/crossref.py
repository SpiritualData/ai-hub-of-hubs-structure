"""crossref -- a DOI-lookup helper: does this DOI exist at Crossref, and what are its title, authors, year and venue?

Not a seat arm. It checks a reference the way a person would, by asking the registry that issued the DOI, so a consumer can
confirm a citation before showing it. Facts, read 2026-10-30:
  * ``GET https://api.crossref.org/works/{doi}`` answers ``{"status": "ok", "message": {...}}`` with ``title``,
    ``container-title``, ``issued.date-parts``, ``author`` (``given``, ``family``), ``is-referenced-by-count`` and ``URL``;
    an unknown DOI answers HTTP 404 (observed 2026-10-30).
  * Identify the caller with the ``mailto`` parameter or an agent header to join the polite pool.
    https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/  (page updated 2025-10-16;
    its table lists public 5 and polite 10, time unit not stated there.) The research report of 2026-10-30 records the
    2026-07-21 limit change as lookups 5 a second public and 10 polite, lists 1 and 3 a second
    (https://community.crossref.org/t/refining-rest-api-limits-for-improved-stability-and-reliability/16137); not re-fetched.
The contact address and the transport are arguments; nothing is read from the environment.
"""
from __future__ import annotations

from typing import Any, Mapping, Optional
from urllib.parse import quote

from ..ports.scholarly import ScholarlyError, Work, WorksResult
from .openalex import doi_of, one_line, web_url
from .transport import Transport, TransportError, default_transport, error_for_status

BASE_URL = "https://api.crossref.org/works/"
SERVICE = "crossref"


def work_from_message(message: Mapping[str, Any]) -> Work:
    parts = ((message.get("issued") or {}).get("date-parts") or [[None]])[0] or [None]
    names = []
    for author in message.get("author") or []:
        name = " ".join(p for p in (str(author.get("given") or "").strip(), str(author.get("family") or "").strip()) if p)
        if name or author.get("name"):
            names.append(name or str(author.get("name")))
    title = message.get("title") or [""]
    venue = message.get("container-title") or [""]
    doi = doi_of(message.get("DOI"))
    return Work(title=one_line(title[0] if title else ""), authors=tuple(one_line(n) for n in names),
                year=parts[0] if isinstance(parts[0], int) else None, venue=one_line(venue[0] if venue else ""),
                doi=doi, url=web_url(message.get("URL")), cited_by_count=int(message.get("is-referenced-by-count") or 0),
                work_id=doi, source=SERVICE)


def lookup_doi(doi_or_url: str, *, mailto: str = "", transport: Optional[Transport] = None, timeout: float = 10.0) -> WorksResult:
    """One work by DOI from Crossref. ``error.kind == "not_found"`` means Crossref holds no such DOI (it may still exist at
    another registration agency). Never raises."""
    doi = doi_of(doi_or_url)
    if not doi:
        return WorksResult(query=str(doi_or_url)[:80], source=SERVICE,
                           error=ScholarlyError("not_a_doi", "a DOI looks like 10.xxxx/..."))
    params = {"mailto": mailto} if mailto else {}
    headers = {"Accept": "application/json", "User-Agent": "hubofhubs-science" + (f" (mailto:{mailto})" if mailto else "")}
    try:
        response = (transport or default_transport)(BASE_URL + quote(doi, safe="/"), params=params, headers=headers, timeout=timeout)
    except TransportError as exc:
        return WorksResult(query=doi, source=SERVICE, error=ScholarlyError(exc.kind, f"{SERVICE}: {exc}"))
    except Exception as exc:  # noqa: BLE001
        return WorksResult(query=doi, source=SERVICE, error=ScholarlyError("network", f"{SERVICE}: request failed: {type(exc).__name__}"))
    error = error_for_status(response, SERVICE)
    if error:
        return WorksResult(query=doi, source=SERVICE, error=error)
    try:
        work = work_from_message(response.json()["message"])
    except Exception:  # noqa: BLE001
        return WorksResult(query=doi, source=SERVICE, error=ScholarlyError("bad_response", f"{SERVICE}: the reply was not readable"))
    return WorksResult(works=[work], total=1, query=doi, source=SERVICE)
