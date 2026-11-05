"""Request Intake (Consciousness): takes in the requests people make to the system, from every source Body declares, and attaches each to
the person who made it so the rest of the flow can ask for that person's Representative. It measures effective human interaction and
awareness: nothing a person asked is lost or answered twice, and the system knows what is waiting. Where requests come from is Body's
(Intake Sources); what to do with a request is the flow's. Standard library plus the hub and ``esoi``."""
from typing import Any, Dict, List, Mapping, Sequence

from esoi import implementation

from ..seats import IntakeSourcing


@implementation("request-intake", "every_declared_source")
class EveryDeclaredSource:
    """Pulls from each declared source (or only the sources named), drops a request with no text and a request already taken, and keeps the
    order requests arrived in."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, sources: IntakeSourcing):
        self.intake = sources

    def receive(self, person: str = "", sources: Sequence[str] = ()) -> Sequence[Mapping[str, Any]]:
        named = [s["kind"] for s in self.intake.sources()]
        wanted = [s for s in (sources or named)]
        taken: List[Dict[str, Any]] = []
        seen = set()
        for kind in wanted:
            for row in self.intake.pull(kind):
                key = (row.get("person", ""), row["text"])
                if key in seen or (person and row.get("person") and row["person"] != person):
                    continue
                seen.add(key)
                taken.append({**row, "source": row.get("source") or kind})
        return taken
