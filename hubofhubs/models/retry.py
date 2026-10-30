"""Retry helpers for transient provider errors (503, rate limits, timeouts) and for model output that will not parse."""
import json
import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Optional

from . import outage

log = logging.getLogger("hubofhubs.models.retry")


def parse_json_with_retry(produce: Callable[[], Any], *, max_retries: int = 2, base_delay: float = 0.5,
                          validate: Optional[Callable[[Any], bool]] = None, label: str = "json") -> Any:
    """Call ``produce`` (a FRESH model call each time, returning a string or an already decoded dict/list) and return the parsed
    JSON, retrying with backoff when parsing or ``validate(obj)`` fails. Raises the last error after the final attempt, so the
    caller applies its own fallback in one place."""
    last_err: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            raw = produce()
            obj = raw if isinstance(raw, (dict, list)) else json.loads(raw)
            if validate is None or validate(obj):
                return obj
            last_err = ValueError(f"{label}: output failed validation")
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            last_err = e
        if attempt < max_retries:
            log.warning("%s parse failed (attempt %d/%d): %s, retrying", label, attempt + 1, max_retries + 1, last_err)
            time.sleep(base_delay * (2 ** attempt) + random.uniform(0, 0.2))
    raise last_err if last_err is not None else ValueError(f"{label}: parse failed")


def format_provider_error(exc: Exception) -> str:
    """A user-friendly string for known billing, auth and quota errors, or the raw ``str(exc)``."""
    text, kind = str(exc), type(exc).__name__
    if "ClientError" in kind and "403" in text and ("dunning" in text.lower() or "PERMISSION_DENIED" in text):
        return ("Google Gemini billing issue: your Google Cloud project has been blocked (overdue payment or spending limit). "
                "Fix it at console.cloud.google.com/billing, then retry, or use an API key from a project with active billing.")
    if "403" in text and "PERMISSION_DENIED" in text:
        return "Permission denied by the AI provider (403). Check your API key and billing status, then retry."
    if "429" in text or "quota" in text.lower() or "RateLimitError" in kind:
        return "Rate limit or quota exceeded. Wait a moment and try again, or switch to a model with higher quota."
    return text


def is_transient_error(exc: Exception) -> bool:
    """Whether ``exc`` is worth retrying: 503/429/overloaded from a vendor SDK, timeouts and transport errors, and a worker
    binary that is missing right now (an installer replacing it in place leaves the path empty for a few seconds; a path that is
    simply wrong still exhausts the retries and the final error names the file)."""
    text, kind = str(exc), type(exc).__name__
    module = getattr(type(exc), "__module__", "") or ""
    if ("ServerError" in kind or "RateLimitError" in kind) and ("503" in text or "429" in text or "overloaded" in text.lower()):
        return True
    if any(word in kind.lower() for word in ("timeout", "connectionerror", "httperror")):
        return True
    if module.startswith(("httpx", "httpcore")):
        return True
    if ("RateLimitError" in kind or "APIStatusError" in kind or "APIError" in kind) and ("429" in text or "503" in text):
        return True
    return isinstance(exc, FileNotFoundError)


def retry_transient(max_retries: int = 3, base_delay: float = 1.0) -> Callable:
    """Decorator: retry a provider method on transient errors with exponential backoff and jitter (``max_retries`` retries after
    the first try). A give-up records an outage (``outage.note``) so the caller can wait for the provider instead of failing."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as exc:
                    if not is_transient_error(exc):
                        raise
                    if attempt >= max_retries:
                        outage.note(exc)
                        log.error("%s failed after %d attempts: %s: %s", func.__name__, max_retries + 1, type(exc).__name__, exc)
                        raise
                    delay = base_delay * (2 ** attempt)
                    log.debug("%s attempt %d failed (%s); retrying", func.__name__, attempt + 1, type(exc).__name__)
                    time.sleep(delay + random.uniform(0, delay * 0.1))
        return wrapper
    return decorator
