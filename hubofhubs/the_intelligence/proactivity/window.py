"""A window of days and time of day for recurring work: the typed part of a schedule that a calendar period cannot say.

A ``Window`` has ``days`` (the days of the week it keeps, ``mon`` to ``sun``), ``run_time`` (``HH:MM`` on the local clock), ``time_zone`` (an IANA zone
name; an unknown or empty one is the machine's own zone, never UTC) and ``grace_minutes`` (how long after ``run_time`` a start still counts). Each
chosen day has one occasion, which opens when that day's local clock reaches ``run_time`` and closes ``grace_minutes`` later; the window can reach past
midnight. A local time that does not exist (the clock jumped over it) opens when the clock passes it, and one that happens twice opens the first time.
Standard library only."""
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from typing import Any, Mapping, Optional, Tuple, Union
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def zone_of(name: str):
    try:
        return ZoneInfo(name) if name else datetime.now().astimezone().tzinfo
    except (ZoneInfoNotFoundError, ValueError):
        return datetime.now().astimezone().tzinfo      # the machine's own zone, never UTC


@dataclass(frozen=True)
class Window:
    days: Tuple[str, ...] = DAYS
    run_time: str = "09:00"
    time_zone: str = ""
    grace_minutes: int = 60

    def __post_init__(self):
        days = tuple(str(d).strip().lower()[:3] for d in self.days)
        if not days or any(d not in DAYS for d in days):
            raise ValueError(f"days must be some of {DAYS}, got {self.days!r}")
        object.__setattr__(self, "days", days)
        try:
            time.fromisoformat(self.run_time)
        except ValueError:
            raise ValueError(f"run_time must be HH:MM, got {self.run_time!r}") from None
        if int(self.grace_minutes) < 0:
            raise ValueError("grace_minutes cannot be negative")

    @classmethod
    def of(cls, raw: Union["Window", Mapping[str, Any]]) -> "Window":
        """A window from a mapping with the field names above, or the window itself."""
        if isinstance(raw, Window):
            return raw
        known = {k: raw[k] for k in ("days", "run_time", "time_zone", "grace_minutes") if k in raw}
        return cls(**known)

    def latest_start(self, now: datetime) -> Optional[datetime]:
        """The last moment at or before ``now`` when an occasion opened (in UTC), or None when none opened within the grace window and a day before."""
        zone = zone_of(self.time_zone)
        today = now.astimezone(zone).date()
        for back in range(0, int(self.grace_minutes) // 1440 + 2):
            day = today - timedelta(days=back)
            if DAYS[day.weekday()] not in self.days:
                continue
            opened = datetime.combine(day, time.fromisoformat(self.run_time), tzinfo=zone).astimezone(timezone.utc)
            if opened <= now:
                return opened
        return None

    def is_due(self, last_run: Optional[datetime], now: datetime) -> bool:
        """Due once in each occasion: the occasion is open (``run_time`` has arrived and the grace window has not ended) and the last run was before it opened."""
        opened = self.latest_start(now)
        if opened is None or now - opened > timedelta(minutes=int(self.grace_minutes)):
            return False
        return last_run is None or last_run < opened
