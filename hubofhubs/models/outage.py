"""Model-provider outages: recognise one from a failed call's wording, remember the latest, and attribute it to a run.

A provider that is overloaded, throttling or briefly down is an environment failure, not a fault in the work, so a consumer can
hold the work and retry instead of reporting it failed. ``is_outage`` reads status codes and provider wording, never a bare
"timeout" (that also means a slow backend); ``note`` is called by ``retry.retry_transient`` when it gives up; ``seen_since``
reports an outage recorded during one run, so a concurrent run's outage is never blamed on this one.
"""
import logging
import threading
import time
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("hubofhubs.models.outage")

OUTAGE_MARKERS = (
    "503", "529", "502", "504", "429", "overloaded", "service unavailable", "temporarily unavailable", "bad gateway",
    "gateway timeout", "internal server error", "resource_exhausted", "resource exhausted", "rate limit", "ratelimit",
)


@dataclass(frozen=True)
class ProviderOutage:
    message: str
    at: float  # time.time() when it was recorded


_lock = threading.Lock()
_last: Optional[ProviderOutage] = None


def is_outage(exc: BaseException) -> bool:
    """True when a failed model call says the provider is unavailable right now."""
    text = f"{type(exc).__name__} {exc}".lower()
    return any(marker in text for marker in OUTAGE_MARKERS)


def from_exception(exc: BaseException) -> Optional[ProviderOutage]:
    """The outage an exception stands for (itself or anything it was raised from), else None."""
    seen, current = set(), exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if is_outage(current):
            detail = str(current).strip()[:300]
            return ProviderOutage(message=f"{type(current).__name__}: {detail}" if detail else type(current).__name__, at=time.time())
        current = current.__cause__ or current.__context__
    return None


def note(exc: BaseException) -> None:
    """Remember ``exc`` as the latest provider outage, if it is one. Never raises."""
    global _last
    outage = from_exception(exc)
    if outage is None:
        return
    with _lock:
        _last = outage
    log.warning("model provider unavailable: %s", outage.message)


def seen_since(moment: float) -> Optional[ProviderOutage]:
    """The latest outage recorded at or after ``moment`` (a ``time.time()`` value), else None."""
    with _lock:
        last = _last
    return last if last is not None and last.at >= moment else None


def reset_for_tests() -> None:
    global _last
    with _lock:
        _last = None
