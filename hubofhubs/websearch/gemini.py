"""gemini -- the Gemini Google Search grounding arm of the search-backend seat (key-light fallback beyond a Gemini key).

Third-party libraries are loaded lazily, only when this arm runs: ``google-genai`` (extra ``gemini``) for the client and
``httpx`` (extra ``web``) for resolving the redirect links Gemini returns. The hub reads no environment: the key is a
constructor argument (``backends.gemini_api_key_from_env(env)`` reads it from a mapping the caller passes).
"""
from __future__ import annotations

import concurrent.futures
import threading
from typing import Any, Dict, List

from esoi import implementation

from ..ports.search import SearchBackendError, SearchHit, SearchResponse
from .backends import HttpCallable, DEFAULT_GEMINI_MODEL, default_http

REDIRECT_TIMEOUT = 3.0


def timeout_error() -> type:
    """The HTTP library's timeout exception class (``httpx.TimeoutException``), imported when first needed."""
    import httpx
    return httpx.TimeoutException


def location_header(resp: Any) -> str:
    headers = getattr(resp, "headers", None) or {}
    try:
        return headers.get("Location") or headers.get("location") or ""
    except Exception:  # noqa: BLE001
        return ""


@implementation("search-backend", "gemini")
class GeminiGroundingBackend:
    """Searches via Gemini's native Google Search grounding tool (``google.genai``).

    Uses its OWN client (not the planner's provider), so it works regardless of which provider
    is running the planner/answer calls. Resolves the ``vertexaisearch`` redirect URLs Gemini
    returns to their real destinations (concurrent HEAD, falling back to GET, 3s timeout each,
    per-instance cache) so citations point at the actual source page.
    """

    name = "gemini-grounding"

    def __init__(
        self,
        api_key: str = "",
        model: str = DEFAULT_GEMINI_MODEL,
        client: Any = None,
        http: HttpCallable = default_http,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.http = http
        self._client = client
        self.tokens_in = 0
        self.tokens_out = 0
        self.calls = 0
        self._redirect_cache: Dict[str, str] = {}
        self._redirect_lock = threading.Lock()

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import google.genai as genai
        except ImportError as exc:
            raise SearchBackendError("gemini-grounding: google-genai is not installed (install the hubofhubs[gemini] extra)") from exc
        if not self.api_key:
            raise SearchBackendError("gemini-grounding: no Gemini API key configured")
        self._client = genai.Client(api_key=self.api_key)
        return self._client

    def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
        client = self._get_client()
        try:
            from google.genai import types

            tool = types.Tool(google_search=types.GoogleSearch())
            prompt = (
                "Search the web and answer concisely in at most 120 words with the key facts, "
                f"numbers and dates. Query: {query}"
            )
            response = self._generate(client, types, tool, prompt)
        except SearchBackendError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SearchBackendError(f"gemini-grounding: {exc}") from exc

        self.calls += 1
        meta = getattr(response, "usage_metadata", None)
        if meta:
            self.tokens_in += getattr(meta, "prompt_token_count", 0) or 0
            self.tokens_out += getattr(meta, "candidates_token_count", 0) or 0

        answer = getattr(response, "text", "") or ""
        hits, queries_issued = self._parse_grounding(response, max_results)
        if not hits and not answer:
            raise SearchBackendError(f"gemini-grounding: no results for {query!r}")
        return SearchResponse(hits=hits, answer=answer, queries_issued=queries_issued or [query])

    def _generate(self, client: Any, types: Any, tool: Any, prompt: str) -> Any:
        """One ``generate_content`` call; Gemini 3.x gets minimal thinking (retried once without
        it if the model rejects the config), matching ``gemini_provider.GeminiProvider._generate``.
        """
        if "gemini-3" in self.model:
            try:
                config = types.GenerateContentConfig(
                    tools=[tool], thinking_config={"thinking_level": "minimal"}
                )
                return client.models.generate_content(model=self.model, contents=prompt, config=config)
            except Exception as exc:  # noqa: BLE001
                if "think" not in str(exc).lower():
                    raise
        config = types.GenerateContentConfig(tools=[tool])
        return client.models.generate_content(model=self.model, contents=prompt, config=config)

    def _parse_grounding(self, response: Any, max_results: int) -> Any:
        queries_issued: List[str] = []
        chunks: List[Any] = []
        supports: List[Any] = []
        for cand in getattr(response, "candidates", None) or []:
            gm = getattr(cand, "grounding_metadata", None)
            if not gm:
                continue
            chunks = list(getattr(gm, "grounding_chunks", None) or [])
            supports = list(getattr(gm, "grounding_supports", None) or [])
            queries_issued = list(getattr(gm, "web_search_queries", None) or [])
            break  # first candidate carries the grounding metadata

        if not chunks:
            return [], queries_issued

        snippets_by_index: Dict[int, List[str]] = {}
        for support in supports:
            segment = getattr(support, "segment", None)
            text = getattr(segment, "text", "") if segment else ""
            if not text:
                continue
            for idx in getattr(support, "grounding_chunk_indices", None) or []:
                bucket = snippets_by_index.setdefault(idx, [])
                if text not in bucket:
                    bucket.append(text)

        raw_hits: List[Dict[str, str]] = []
        urls_to_resolve: List[str] = []
        for i, chunk in enumerate(chunks[:max_results]):
            web = getattr(chunk, "web", None)
            if web is None:
                continue
            uri = getattr(web, "uri", "") or ""
            title = getattr(web, "title", "") or ""
            snippet = " ".join(snippets_by_index.get(i, [])).strip()
            if len(snippet) > 300:
                snippet = snippet[:300].rsplit(" ", 1)[0] + "..."
            raw_hits.append({"title": title, "url": uri, "snippet": snippet})
            if uri:
                urls_to_resolve.append(uri)

        resolved = self._resolve_redirects(urls_to_resolve)
        hits = [
            SearchHit(title=h["title"], url=resolved.get(h["url"], h["url"]), snippet=h["snippet"])
            for h in raw_hits
        ]
        return hits, queries_issued

    def _resolve_redirects(self, urls: List[str]) -> Dict[str, str]:
        """Resolve grounding-redirect URLs to their real destination. Failures keep the original URL."""
        resolved: Dict[str, str] = {}
        to_resolve: List[str] = []
        with self._redirect_lock:
            for u in urls:
                cached = self._redirect_cache.get(u)
                if cached is not None:
                    resolved[u] = cached
                else:
                    to_resolve.append(u)
        if not to_resolve:
            return resolved

        def resolve_one(u: str) -> str:
            try:
                resp = self.http("HEAD", u, timeout=REDIRECT_TIMEOUT, follow_redirects=False)
                loc = location_header(resp)
                if loc:
                    return loc
                # HEAD answered but carried no usable Location (e.g. 405 Method Not Allowed, or
                # 200 with no redirect): a GET may behave differently, so fall through and try it.
            except timeout_error():
                # HEAD timed out: keep the redirect URL as-is. Retrying with GET would double the
                # worst-case latency for a dead or slow redirector, for no better outcome.
                return u
            except Exception:  # noqa: BLE001
                # Some other HEAD failure (connection refused, TLS error, ...): a GET may still work.
                pass
            try:
                resp = self.http("GET", u, timeout=REDIRECT_TIMEOUT, follow_redirects=False)
                loc = location_header(resp)
                if loc:
                    return loc
            except Exception:  # noqa: BLE001
                pass
            return u

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, len(to_resolve))) as pool:
            futures = {pool.submit(resolve_one, u): u for u in to_resolve}
            for fut in concurrent.futures.as_completed(futures):
                u = futures[fut]
                try:
                    resolved[u] = fut.result()
                except Exception:  # noqa: BLE001
                    resolved[u] = u

        with self._redirect_lock:
            self._redirect_cache.update(resolved)
        return resolved


