"""BodyComposition."""
from typing import Any, Mapping
from esoi import implementation
from esoi import Lazy
from hubofhubs.the_body.internal_context.interface import InternalContexting
from hubofhubs.the_body.intake_sources.interface import IntakeSourcing
from hubofhubs.the_body.hands.interface import Connecting
from hubofhubs.the_self.steps import listing, take
from hubofhubs.the_self.steps import done


@implementation("the-body", "composition")
class BodyComposition:
    """Describes the form of the system: where its data lives (Internal Context), where its requests come from (Intake Sources) and which
    enduring integrations the AI may use (Hands), and keeps the run record the flow writes. Every part is specified to be adapted to a particular
    system; Body also owns the configuration, environment variables, secrets and stored authentication the tools need."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, internal: Lazy[InternalContexting], intake: Lazy[IntakeSourcing], hands: Lazy[Connecting]):
        self.internal, self.intake, self.hands = internal, intake, hands

    def describe(self, person: str = "") -> Mapping[str, Any]:
        found = [take(self.internal, "internal-context", method="declared"), take(self.intake, "intake-sources", method="sources"),
                 take(self.hands, "the-hands", system=person)]
        return {"sources": done(found[0]) or [], "intake": done(found[1]) or [], "integrations": done(found[2]) or [], "steps": listing(found)}

    def record_run(self, run: Mapping[str, Any]) -> str:
        return str(done(take(self.internal, "internal-context", method="record", run=run)) or "")
