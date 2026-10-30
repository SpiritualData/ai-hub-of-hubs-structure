"""backends -- pluggable SERP backends behind one small search-backend contract (``search(query, max_results=) -> SearchResponse``).

Why several backends instead of one: dedicated SERP APIs (Serper, Brave, Tavily, a self-hosted
SearXNG) return real title+url+snippet results in well under a second and are cheap at volume;
Gemini's Google Search grounding tool needs no separate key beyond a Gemini key already paid for
elsewhere, so it is the key-free-beyond-an-LLM-key fallback. Rough cost per 1,000 searches (check
each provider's current pricing before relying on these):

  * Serper            ~$1/1k, down to ~$0.30/1k at volume.
  * Brave Search API   $5/1k, with a $5/month free credit.
  * Tavily             usage-based; see tavily.com/pricing.
  * SearXNG            self-hosted, no per-call cost (your own infra bill instead).
  * Gemini 2.5 Flash-Lite grounding: 1,500 grounded prompts/day free, then ~$35/1k.
  * Gemini 3.x grounding: 5,000 grounded prompts/month free, then ~$14/1k.

``select_search_backend`` picks one (or a fallback chain) from environment config; see its
docstring for the exact env vars and the "auto" selection order.

All HTTP goes through one small injectable callable per backend (``http: (method, url, **kwargs)
-> response``), defaulting to a thin wrapper over ``httpx.request``, so tests can run fully
offline with fake response objects (just ``.status_code``, ``.json()``, ``.headers``).
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional

from esoi import implementation

from ..ports.search import SearchBackendError, SearchHit, SearchResponse
from ..seats import SearchBackend  # noqa: F401  (the seat Protocol, importable from here)
from .apis import SPECS

logger = logging.getLogger("hubofhubs.websearch.backends")

DEFAULT_TIMEOUT = 8.0
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-lite"

HttpCallable = Callable[..., Any]


def default_http(method: str, url: str, **kwargs: Any) -> Any:
    try:
        import httpx
    except ImportError as exc:
        raise SearchBackendError("httpx is not installed (install the hubofhubs[web] extra)") from exc
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    return httpx.request(method, url, **kwargs)


# ---------------------------------------------------------------------------
# Shared HTTP helpers
# ---------------------------------------------------------------------------


def raise_for_status(resp: Any, backend: str) -> None:
    status = getattr(resp, "status_code", 200)
    if status == 429:
        raise SearchBackendError(f"{backend}: HTTP 429 rate limited", status_code=429)
    if status in (401, 403):
        raise SearchBackendError(f"{backend}: HTTP {status} unauthorized", status_code=status)
    if status >= 400:
        raise SearchBackendError(f"{backend}: HTTP {status}", status_code=status)


def parse_json(resp: Any, backend: str) -> Dict[str, Any]:
    try:
        return resp.json() or {}
    except Exception as exc:  # noqa: BLE001
        raise SearchBackendError(f"{backend}: invalid JSON response: {exc}") from exc


TAG_RE = re.compile(r"<[^>]+>")


def remove_tags(text: str) -> str:
    return TAG_RE.sub("", text or "")


# ---------------------------------------------------------------------------
# 1-3. Hosted JSON search APIs, described as data (apis.py) and run by one generic backend
# ---------------------------------------------------------------------------


def dotted(data: Any, path: str) -> Any:
    """``a.b`` -> ``data["a"]["b"]``, treating a missing or empty step as an empty mapping."""
    for step in path.split("."):
        data = (data or {}).get(step) if isinstance(data, dict) else None
    return data


def fill(value: Any, key: str, query: str, max_results: int) -> Any:
    """Replace ``{query}``, ``{max_results}`` (an integer) and ``{key}`` in a payload or header value."""
    if value == "{query}":
        return query
    if value == "{max_results}":
        return max_results
    if isinstance(value, str):
        return value.replace("{key}", key)
    return value


class ConfiguredJsonBackend:
    """Searches any JSON search API from a description (see ``apis.py``). Behaviour matches the hand-written
    Serper, Brave and Tavily backends this replaced: same request, same hit fields, same errors."""
    spec: Dict[str, Any] = {}

    def __init__(self, api_key: str = "", http: HttpCallable = default_http) -> None:
        self.api_key = api_key
        self.http = http
        self.name = self.spec["name"]

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Optional["ConfiguredJsonBackend"]:
        key = next((env[n] for n in cls.spec.get("key_env", []) if env.get(n)), "")
        return cls(key) if key else None

    def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
        spec, name = self.spec, self.spec["name"]
        payload = {k: fill(v, self.api_key, query, max_results) for k, v in spec.get("payload", {}).items()}
        headers = {k: fill(v, self.api_key, query, max_results) for k, v in spec.get("headers", {}).items()}
        try:
            resp = self.http(spec["method"], spec["url"], headers=headers,
                             **{"json" if spec.get("send") == "json" else "params": payload})
        except SearchBackendError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SearchBackendError(f"{name}: request failed: {exc}") from exc
        raise_for_status(resp, name)
        data = parse_json(resp, name)

        def field_of(item: Dict[str, Any], label: str) -> str:
            text = next((item.get(k) for k in spec["fields"].get(label, []) if item.get(k)), "") or ""
            return remove_tags(text) if label in spec.get("strip_tags", []) else text

        hits = [SearchHit(title=field_of(item, "title"), url=field_of(item, "url"), snippet=field_of(item, "snippet"),
                          date=field_of(item, "date"))
                for item in (dotted(data, spec["results_path"]) or [])[:max_results]]
        answer = next((dotted(data, p) for p in spec.get("answer_paths", []) if dotted(data, p)), "") or ""
        if not hits and not answer:
            raise SearchBackendError(f"{name}: no results for {query!r}")
        return SearchResponse(hits=hits, answer=answer, queries_issued=[query])


def backend_class_for(spec: Dict[str, Any]) -> type:
    """A backend class bound to one description."""
    return type(f"{spec['name'].title()}Backend", (ConfiguredJsonBackend,), {"spec": spec})


@implementation("search-backend", "serper")
class SerperBackend(ConfiguredJsonBackend):
    spec = next(x for x in SPECS if x["name"] == "serper")


@implementation("search-backend", "brave")
class BraveBackend(ConfiguredJsonBackend):
    spec = next(x for x in SPECS if x["name"] == "brave")


@implementation("search-backend", "tavily")
class TavilyBackend(ConfiguredJsonBackend):
    spec = next(x for x in SPECS if x["name"] == "tavily")


def load_file_specs(path: str) -> Dict[str, type]:
    """The search APIs a deployment describes in a JSON file (a list of entries, see ``apis.py``), as ``{name: backend class}``.
    Nothing is registered anywhere: the consumer decides what to do with the classes. A bad file logs and returns nothing:
    web search never fails the turn."""
    path = (path or "").strip()
    if not path:
        return {}
    import json
    found: Dict[str, type] = {}
    try:
        with open(os.path.expanduser(path), encoding="utf-8") as handle:
            entries = json.load(handle)
        for spec in entries:
            name = str(spec["name"]).strip().lower()
            for required in ("method", "url", "results_path", "fields"):
                spec[required]
            spec["name"] = name
            found[name] = backend_class_for(spec)
    except Exception as exc:  # noqa: BLE001
        logger.warning("search APIs file %s not used: %s", path, exc)
        return {}
    return found


# ---------------------------------------------------------------------------
# 4. SearXNG (self-hosted)
# ---------------------------------------------------------------------------


@implementation("search-backend", "searxng")
class SearxngBackend:
    name = "searxng"

    def __init__(self, base_url: str = "", http: HttpCallable = default_http) -> None:
        self.base_url = (base_url or "").rstrip("/")
        self.http = http

    def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
        try:
            resp = self.http(
                "GET",
                f"{self.base_url}/search",
                params={"q": query, "format": "json"},
            )
        except SearchBackendError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SearchBackendError(f"searxng: request failed: {exc}") from exc
        raise_for_status(resp, "searxng")
        data = parse_json(resp, "searxng")

        hits = [
            SearchHit(
                title=item.get("title", "") or "",
                url=item.get("url", "") or "",
                snippet=item.get("content", "") or "",
                date=item.get("publishedDate", "") or "",
            )
            for item in (data.get("results") or [])[:max_results]
        ]
        if not hits:
            raise SearchBackendError(f"searxng: no results for {query!r}")
        return SearchResponse(hits=hits, answer="", queries_issued=[query])


# ---------------------------------------------------------------------------
# 6. Provider-native (e.g. AnthropicProvider.web_search)
# ---------------------------------------------------------------------------


@implementation("search-backend", "provider")
class ProviderNativeBackend:
    """Wraps any ``ModelProvider`` exposing ``web_search(query, model=, max_results=)``."""

    name = "provider-native"

    def __init__(self, provider: Any = None, model: str = "") -> None:
        self.provider = provider
        self.model = model

    def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
        try:
            result = self.provider.web_search(query, model=self.model, max_results=max_results)
        except Exception as exc:  # noqa: BLE001
            raise SearchBackendError(f"provider-native: {exc}") from exc

        hits = [
            SearchHit(
                title=r.get("title", "") or "",
                url=r.get("url", "") or "",
                snippet=r.get("snippet", "") or "",
            )
            for r in (result.get("results") or [])
        ]
        answer = result.get("answer", "") or ""
        if not hits and not answer:
            raise SearchBackendError(f"provider-native: no results for {query!r}")
        return SearchResponse(hits=hits, answer=answer, queries_issued=[query])


# ---------------------------------------------------------------------------
# 7. Fallback chain
# ---------------------------------------------------------------------------


class FallbackSearchBackend:
    """Tries each backend in order; moves on on error or an empty (no hits, no answer) response.

    After a 429/401/403 from a backend, that backend sits in a cooldown so a failing primary
    isn't hammered on every subsequent search.
    """

    def __init__(self, backends: List[Any], *, cooldown_seconds: float = 60.0) -> None:
        if not backends:
            raise ValueError("FallbackSearchBackend requires at least one backend")
        self.backends = backends
        self.name = ">".join(b.name for b in backends)
        self._cooldown_seconds = cooldown_seconds
        self._cooldown_until: Dict[str, float] = {}
        self._lock = threading.Lock()

    def search(self, query: str, *, max_results: int = 5) -> SearchResponse:
        errors: List[str] = []
        now = time.time()
        for backend in self.backends:
            with self._lock:
                until = self._cooldown_until.get(backend.name, 0.0)
            if until > now:
                errors.append(f"{backend.name}: in cooldown after a recent failure")
                continue
            try:
                resp = backend.search(query, max_results=max_results)
            except SearchBackendError as exc:
                errors.append(str(exc))
                if exc.status_code in (401, 403, 429):
                    with self._lock:
                        self._cooldown_until[backend.name] = time.time() + self._cooldown_seconds
                continue
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{backend.name}: {exc}")
                continue
            if not resp.hits and not resp.answer:
                errors.append(f"{backend.name}: empty response")
                continue
            return resp
        raise SearchBackendError("; ".join(errors) if errors else "all backends failed")


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------

GEMINI_KEY_NAMES = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY")


def gemini_api_key_from_env(env: Mapping[str, str]) -> str:
    """The first Gemini key set in ``env`` (a mapping the caller passes; the hub reads no environment itself), or ''."""
    for name in GEMINI_KEY_NAMES:
        value = env.get(name)
        if value:
            return value
    return ""


@dataclass(frozen=True)
class SelectionKeys:
    """The names of the settings ``select_search_backend`` reads from the mapping it is given. A consumer that namespaces its
    settings passes its own names; the defaults are plain."""
    enabled: str = "WEB_SEARCH_ENABLED"
    backend: str = "WEB_SEARCH_BACKEND"
    apis_file: str = "WEB_SEARCH_APIS_FILE"
    model: str = "WEB_SEARCH_MODEL"
    provider_model: str = "WEB_SEARCH_PROVIDER_MODEL"
    searxng_url: str = "SEARXNG_URL"


def hub_resolver(name: str) -> Any:
    """The default way a name becomes a backend class: the hub's own resolution for the ``search-backend`` seat. Raises
    ``ValueError`` (``HubError``) for an unknown name."""
    from ..resolution import resolve
    return resolve("search-backend", name)


def select_search_backend(
    env: Mapping[str, str],
    *,
    provider: Any = None,
    keys: SelectionKeys = SelectionKeys(),
    resolver: Optional[Callable[[str], Any]] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> Optional[Any]:
    """Pick a backend (or a ``FallbackSearchBackend`` chain) from the settings in ``env``. The hub reads no environment: the
    caller passes the mapping (a consumer passes its process environment).

    Settings, under the names in ``keys``:
      enabled         -- "false"/"0"/"off"/"no" disables web search entirely (default on).
      backend         -- force exactly one: serper|brave|tavily|searxng|gemini|provider, or a name from the apis file.
                         If its key/config is missing, logs a warning and returns None rather than silently falling back.
      apis_file       -- path to a JSON file of search APIs described as data (``apis.py``); their names join the chain.
      model           -- Gemini grounding model (default "gemini-2.5-flash-lite").
      provider_model  -- model id for provider-native search (required for "provider").
    Vendor keys keep their vendors' names: SERPER_API_KEY, BRAVE_SEARCH_API_KEY / BRAVE_API_KEY, TAVILY_API_KEY /
    WEB_SEARCH_API_KEY, SEARXNG_URL (or ``keys.searxng_url``), GEMINI_API_KEY / GOOGLE_API_KEY / GOOGLE_AI_API_KEY.

    "auto" (no forced backend): collects every backend whose config is present, in this order -- serper, brave, tavily,
    searxng, gemini, provider-native, then the apis file's -- and wraps more than one in a ``FallbackSearchBackend``.
    ``provider`` (anything with ``supports_web_search(model)`` and ``web_search(...)``) is only used for "provider", and only
    when ``provider_model`` is also set and the provider reports support for that model. Returns ``None`` when nothing is
    configured.

    ``resolver(name)`` turns a backend name into its class; the default is the hub's own resolution (``hub_resolver``), so a
    consumer that owns its selection passes its own resolver and the hub never imports it. ``extra`` is a ready ``{name: class}``
    (already loaded from the apis file); without it the file named by ``keys.apis_file`` is loaded here.
    """
    enabled = (env.get(keys.enabled, "") or "").strip().lower()
    if enabled in ("false", "0", "off", "no"):
        return None

    model = env.get(keys.model) or DEFAULT_GEMINI_MODEL
    provider_model = env.get(keys.provider_model) or ""
    file_backends = dict(extra) if extra is not None else load_file_specs(env.get(keys.apis_file, ""))
    resolve_name = resolver or hub_resolver

    def constructor_args(name: str) -> Optional[Dict[str, Any]]:
        """The keyword arguments a backend is built with from this environment, or None when its
        key/config is missing (then the backend is unavailable)."""
        if name == "searxng":
            base_url = env.get(keys.searxng_url, "")
            return {"base_url": base_url} if base_url else None
        if name == "gemini":
            key = gemini_api_key_from_env(env)
            return {"api_key": key, "model": model} if key else None
        if name == "provider":
            if provider is None or not provider_model:
                return None
            fn = getattr(provider, "supports_web_search", None)
            try:
                if not (callable(fn) and fn(provider_model)):
                    return None
            except Exception:  # noqa: BLE001
                return None
            return {"provider": provider, "model": provider_model}
        return None

    def build(name: str) -> Optional[Any]:
        try:
            backend_cls = file_backends.get(name) or resolve_name(name)
        except ValueError:
            return None
        # A backend that describes how to build itself from the environment (``from_env``: the data-described JSON APIs)
        # needs no branch here; ``constructor_args`` serves the few that do not.
        from_env = getattr(backend_cls, "from_env", None)
        if callable(from_env):
            return from_env(env)
        args = constructor_args(name)
        return backend_cls(**args) if args is not None else None

    explicit = (env.get(keys.backend, "") or "").strip().lower()
    if explicit:
        backend = build(explicit)
        if backend is None:
            logger.warning(
                "%s=%s requested but its key/config is missing; web search disabled", keys.backend, explicit,
            )
        return backend

    order = ["serper", "brave", "tavily", "searxng", "gemini", "provider", *file_backends]
    available = [b for b in (build(name) for name in order) if b is not None]
    if not available:
        return None
    if len(available) == 1:
        return available[0]
    return FallbackSearchBackend(available)
