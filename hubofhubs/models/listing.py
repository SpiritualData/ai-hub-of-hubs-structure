"""A time-boxed cache of one provider's live model list."""
import logging
import time
from typing import Callable, List, Optional, Sequence

log = logging.getLogger("hubofhubs.models.listing")


class ModelListCache:
    def __init__(self, seconds: float = 3600.0):
        self.seconds = seconds
        self.models: Optional[List[str]] = None
        self.at = 0.0

    def get(self, fetch: Callable[[], List[str]], fallback: Sequence[str] = ()) -> List[str]:
        """The cached list while fresh, else ``fetch()``; when that raises, the ``fallback`` (cached too, so a vendor outage is not
        asked again on every call)."""
        now = time.monotonic()
        if self.models is not None and now - self.at < self.seconds:
            return self.models
        try:
            self.models = fetch()
        except Exception:  # noqa: BLE001 - a listing hiccup must never break resolution
            log.warning("listing models failed; using the fallback list", exc_info=True)
            self.models = list(fallback)
        self.at = now
        return self.models
