"""The evaluation cases for the areas of the registry: every area gets the checks that apply to it, each expecting ``holds`` true.
The research facts (registered, fresh, nothing hand-wired) are checked once per area. The facts about a consumer's code (one seam,
selectable, by configuration, a fake hub, no vendor branch in core) are checked once per SEAT (``hubs.csv`` ``seat``): an area is an
arm or tool inside its seat, so a consumer binds the seat, not each area. The connection checks (``registry.CONNECTION_KINDS``) apply
only to seats with at least one area whose ``call`` is adopt, coexist or blank; a seat of only KEEP, WATCH or AVOID areas is no gap."""
import json
import sys

from . import registry
from .measure import KINDS


def cases(folder=None):
    """Area checks once per area, seat checks once per seat (a seat is an arm-holding part of the mind; an area is an arm or tool
    inside it), so a consumer binds one row per seat it uses and not one per research area."""
    out = []
    hubs = registry.read("hubs.csv", folder)

    def add(subject, key, kind):
        out.append(dict(id=f"HUB-{len(out) + 1:03d}", **({"area": subject} if key == "area" else {"seat": subject}), kind=kind,
                        description=f"{subject}: {kind}", args={key: subject}, expect={"eq": {"holds": True}}))
    for row in hubs:
        for kind in registry.AREA_KINDS:
            add(row["area"], "area", kind)
    for seat in registry.seat_ids(hubs):
        for kind in registry.SEAT_KINDS:
            if kind in registry.CONNECTION_KINDS and not registry.seat_should_connect(hubs, seat):
                continue
            add(seat, "seat", kind)
    return out


if __name__ == "__main__":
    json.dump(cases(), sys.stdout, indent=1)
    sys.stdout.write("\n")
