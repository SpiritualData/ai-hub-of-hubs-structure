"""A second consumer: a tiny notes app ("acme") with none of the first consumer's content.

It registers a part under a name it owns, selects it on its own config, assembles its system and prints why each part was
chosen. It is also the leak detector's subject: if the hub ever needs something from the first consumer to run this, or
contains this consumer's names, a test fails.
"""
from typing import Any, Mapping, Sequence

import hubofhubs

SEAT = "choose-a-model-tier"


class AcmeFlatTiers:
    """Always the first arm listed for each tier: the simplest thing that satisfies the seat."""

    def select(self, tiers: Mapping[str, Sequence[Mapping[str, Any]]], prices: Sequence[Mapping[str, str]],
               credits: Sequence[Mapping[str, str]] = (), defaults: Any = None, **bars: Any) -> Mapping[str, Any]:
        return {tier: {"arm": (arms[0]["provider"], arms[0]["model"]), "reason": "acme: first listed"}
                for tier, arms in tiers.items() if arms}


def build_system(use_own: bool = True) -> "hubofhubs.Assembly":
    hubofhubs.register(SEAT, "acme-flat", AcmeFlatTiers)
    selections = {SEAT: "acme-flat"} if use_own else {}
    return hubofhubs.assemble(hubofhubs.AssemblyConfig(solutions=(SEAT,), selections=selections))


if __name__ == "__main__":
    for line in build_system().reasons:
        print(line)
