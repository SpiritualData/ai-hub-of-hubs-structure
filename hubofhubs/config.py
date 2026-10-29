"""Settings the hub reads. Config fields only: the hub reads no environment and no file outside its own package data."""
from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

FORBIDDEN_ENVIRON = ("ESOI_ROOT", "ESOI_SNAPSHOT")   # these would point esoi at records the hub did not ship
SELECT_PREFIX = "ESOI_SELECT_"


@dataclass(frozen=True)
class HubConfig:
    """What a consumer hands the hub, once, at startup.

    ``selection_environ`` is the only environment ``esoi`` ever sees (default empty): a consumer that wants an
    ``ESOI_SELECT_<SCOPE>_<SOLUTION_ID>`` choice puts it here, as data. ``names`` are explicit names per solution id,
    ``selections`` the consumer's own selections (they live on this object, never process-wide), ``options`` the non-seat
    constructor arguments per solution id, and ``seats`` the manifest of solution ids the consumer uses (empty: every seat
    that has a hub default or is provided).
    """
    seats: Tuple[str, ...] = ()
    names: Mapping[str, str] = field(default_factory=dict)
    selections: Mapping[str, str] = field(default_factory=dict)
    options: Mapping[str, Mapping[str, Any]] = field(default_factory=dict)
    selection_environ: Mapping[str, str] = field(default_factory=dict)
