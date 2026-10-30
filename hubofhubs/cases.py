"""The evaluation cases for the areas of the registry: every area gets the checks that apply to it, each expecting ``holds`` true.
The registry facts (registered, fresh, no vendor branch, nothing hand-wired) apply to every area. The checks that can only hold once a
consumer has connected an area (``registry.CONNECTION_KINDS``: by configuration, one seam, selectable, a fake hub) apply only to the
areas whose ``call`` says a consumer should be connected (adopt, coexist or blank): a KEEP, WATCH or AVOID area is not a gap."""
import json
import sys

from . import registry
from .measure import KINDS


def cases(folder=None):
    out = []
    for row in registry.read("hubs.csv", folder):
        for kind in KINDS:
            if kind in registry.CONNECTION_KINDS and not registry.should_connect(row):
                continue
            out.append(dict(id=f"HUB-{len(out) + 1:03d}", area=row["area"], kind=kind, description=f"{row['area']}: {kind}",
                            args={"area": row["area"]}, expect={"eq": {"holds": True}}))
    return out


if __name__ == "__main__":
    json.dump(cases(), sys.stdout, indent=1)
    sys.stdout.write("\n")
