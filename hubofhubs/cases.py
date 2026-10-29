"""The evaluation cases for the areas of the registry: every area gets every check, each expecting ``holds`` true."""
import json
import sys

from . import registry
from .measure import KINDS


def cases(folder=None):
    out = []
    for row in registry.read("hubs.csv", folder):
        for kind in KINDS:
            out.append(dict(id=f"HUB-{len(out) + 1:03d}", area=row["area"], kind=kind, description=f"{row['area']}: {kind}",
                            args={"area": row["area"]}, expect={"eq": {"holds": True}}))
    return out


if __name__ == "__main__":
    json.dump(cases(), sys.stdout, indent=1)
    sys.stdout.write("\n")
