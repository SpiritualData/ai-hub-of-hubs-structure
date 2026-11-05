"""Intuition arm: what was taken for similar requests before, fading with age, added to what is close in wording."""
from typing import Any, Mapping, Sequence

from esoi import implementation

from hubofhubs.the_body.internal_context.interface import InternalContexting
from hubofhubs.the_intelligence.subconscious.intuition import similarity
from hubofhubs.the_intelligence.subconscious.intuition.nearest_cards import FLOOR

#: Days after which a past take counts half as much.
HALF_LIFE_DAYS = 14.0
#: The least similarity a past request needs with this one for its takes to count at all.
SIMILAR_REQUEST = 0.2
#: How much one fully similar, fresh take adds to an item's score (the item's own closeness to the request is added at weight 1).
TAKEN_WEIGHT = 1.0


@implementation("the-intuition", "co_taken")
class CoTaken:
    """Items the Mind kept for similar past requests come to mind again, a recent keep more than an old one, and so do items close in wording to this
    request. ``history`` is a list of mappings the consumer builds from its own record of what the Mind took: ``request`` (text), ``taken`` (item ids)
    and ``age_days`` (how long ago, default 0). With no history the arm offers what is close in wording."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, internal: InternalContexting, history: Sequence[Mapping[str, Any]] = ()):
        self.internal = internal
        self.history = list(history)

    def offer(self, request: str, limit: int = 5) -> Sequence[Mapping[str, Any]]:
        texts = dict(self.internal.corpus())
        scores = dict(similarity.closeness(request, texts))
        why = {key: "similar" for key in scores}
        past = {str(n): str(h.get("request", "")) for n, h in enumerate(self.history)}
        near = similarity.closeness(request, past) if past else {}
        for n, h in enumerate(self.history):
            sim = near.get(str(n), 0.0)
            if sim < SIMILAR_REQUEST:
                continue
            fade = 0.5 ** (max(float(h.get("age_days", 0.0)), 0.0) / HALF_LIFE_DAYS)
            for item in h.get("taken", ()):
                if item in texts:
                    scores[item] = scores.get(item, 0.0) + TAKEN_WEIGHT * sim * fade
                    why[item] = "taken before" if why.get(item) != "similar" else "similar and taken before"
        return similarity.offered({k: v for k, v in scores.items() if v >= FLOOR}, texts, limit, why)
