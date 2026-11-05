"""A ``TierResolving`` over the model-tier-chooser seat: a tier name becomes the model the chooser measured best for it."""
from hubofhubs.the_world.model_plumbing.model_tier_chooser.interface import TierSelection

#: the names a runner uses for a tier, and the chooser's tier each one means
TIER_OF = {"fast": "cheap", "cheap": "cheap", "balanced": "mid", "mid": "mid", "quality": "strong", "best": "strong", "strong": "strong"}


class TierRegistry:
    """``resolve_tier(tier)``: the model of the arm the tier chooser picked for that tier."""

    def __init__(self, chooser: TierSelection):
        self.chooser = chooser

    def resolve_tier(self, tier: str) -> str:
        chosen = self.chooser.choose().get(TIER_OF.get(tier, tier)) or {}
        if not chosen.get("arm"):
            raise KeyError(f"no model is chosen for the tier {tier!r}")
        return chosen["arm"][1]
