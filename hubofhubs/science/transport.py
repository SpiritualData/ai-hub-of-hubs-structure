"""The one HTTP call the scholarly arms make, and how a response becomes a typed error.

A transport is ``(url, *, params, headers, timeout) -> response`` where the response has ``status_code``, ``headers`` and
``json()``. The default uses ``httpx`` (extra ``science``), imported only when it runs, so a test or a consumer can hand in
a fake. It raises ``TransportError`` with a kind; the arms turn that into a ``ScholarlyError``.
"""
from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from ..ports.scholarly import ScholarlyError

Transport = Callable[..., Any]


class TransportError(Exception):
    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind


def default_transport(url: str, *, params: Mapping[str, Any], headers: Mapping[str, str], timeout: float) -> Any:
    try:
        import httpx
    except ImportError as exc:
        raise TransportError("missing_dependency", "httpx is not installed (install the hubofhubs[science] extra)") from exc
    try:
        return httpx.get(url, params=dict(params), headers=dict(headers), timeout=timeout, follow_redirects=True)
    except httpx.TimeoutException as exc:
        raise TransportError("timeout", f"no answer within {timeout:g} seconds") from exc
    except httpx.HTTPError as exc:
        raise TransportError("network", f"request failed: {type(exc).__name__}") from exc


def header_number(headers: Any, name: str) -> Optional[float]:
    try:
        value = (headers or {}).get(name)
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError, AttributeError):
        return None


def error_for_status(response: Any, service: str) -> Optional[ScholarlyError]:
    """The typed error for a non-success response, or ``None`` for a success. The body is read only for OpenAlex's
    ``key_not_activated`` code; nothing else in it is trusted."""
    status = getattr(response, "status_code", 200)
    if status < 400:
        return None
    retry = header_number(getattr(response, "headers", None), "retry-after")
    if status == 429:
        return ScholarlyError("rate_limited", f"{service}: HTTP 429, the daily allowance or the per-second limit is used up",
                              status, retry)
    if status in (401, 403):
        code = ""
        try:
            body = response.json()
            code = str((body or {}).get("code") or "") if isinstance(body, dict) else ""
        except Exception:  # noqa: BLE001  a body that is not JSON is read as no code
            code = ""
        if code == "key_not_activated":
            return ScholarlyError("key_not_activated", f"{service}: the key exists but its owner has not clicked the activation link",
                                  status)
        return ScholarlyError("unauthorized", f"{service}: HTTP {status}, the key was refused", status)
    if status == 404:
        return ScholarlyError("not_found", f"{service}: HTTP 404, no such record", status)
    if status == 400:
        return ScholarlyError("bad_request", f"{service}: HTTP 400, the request was refused as malformed", status)
    kind = "server" if status >= 500 else "bad_request"
    return ScholarlyError(kind, f"{service}: HTTP {status}", status, retry)
