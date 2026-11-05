"""Intuition arm: the items of the system's own context closest in wording to the request, by TF-IDF cosine over everything Internal Context can read."""
from typing import Any, Mapping, Sequence

from esoi import implementation

from hubofhubs.the_body.internal_context.interface import InternalContexting
from hubofhubs.the_intelligence.subconscious.intuition import similarity

#: An item whose cosine with the request is below this is noise and is never offered.
FLOOR = 0.1


@implementation("the-intuition", "nearest_cards")
class NearestCards:
    """What is closest in wording comes to mind. Reads only through Internal Context's ``corpus`` and remembers nothing between requests."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, internal: InternalContexting):
        self.internal = internal

    def offer(self, request: str, limit: int = 5) -> Sequence[Mapping[str, Any]]:
        texts = dict(self.internal.corpus())
        scores = {key: score for key, score in similarity.closeness(request, texts).items() if score >= FLOOR}
        return similarity.offered(scores, texts, limit, {})
