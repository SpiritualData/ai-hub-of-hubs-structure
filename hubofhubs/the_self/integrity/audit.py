"""config_share, PromptsAsData."""
from pathlib import Path
from typing import Any, List, Mapping, Sequence
from esoi import implementation
from hubofhubs.the_world.learning.research_freshness_reader import registry
from hubofhubs.the_self.integrity import scan
from hubofhubs.the_self.integrity.measure import metrics as connection_metrics
from hubofhubs.the_world.learning.interface import Staying


def config_share(area: str = "") -> float:
    """The share of an area's wired hub connections that need no code (the metric of Tools and of Hands; all areas when none is named)."""
    rows = [r for r in registry.read("hub_capabilities.csv") if r.get("wired", "yes") == "yes" and (not area or r["area"] == area)]
    return float(connection_metrics({}, rows)["config_share"])


@implementation("system-integrity", "prompts_as_data")
class PromptsAsData:
    """An audit of the hub for consumer wording: the vendor-name branches in its own code for the terms given, beside how stale its
    research is and how much of it connects by configuration."""
    REQUIRES = ()     # the seat it is handed

    def __init__(self, stay: Staying):
        self.stay = stay

    def audit(self, terms: Sequence[str]) -> Mapping[str, Any]:
        package = Path(__file__).resolve().parents[2]
        branches = scan.scan_core({"hub": list(terms)}, package, package.parent)["hub"] if terms else []
        return {"vendor_branches": branches, "stale_areas": list(self.stay.stale_areas()), "config_share": config_share()}

    def audit_run(self, run: Mapping[str, Any]) -> Sequence[str]:
        """What the run says about itself, checked against what it did (a finding per claim the record does not support): every step names a
        status, a pending or skipped step says why, and an answer exists only when the Response Writer ran. Integrity audits what the system says
        about itself and what it did; Response Quality judges answers to people."""
        found: List[str] = []

        def walk(rows: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
            flat: List[Mapping[str, Any]] = []
            for row in rows:
                flat.append(row)
                flat += walk(row.get("steps") or ())
            return flat

        every = walk(run.get("steps") or ())
        for row in every:
            if row.get("status") not in ("done", "pending", "skipped"):
                found.append(f"step {row.get('solution', '?')} has no status")
            elif row["status"] != "done" and not row.get("reason"):
                found.append(f"step {row.get('solution', '?')} is {row['status']} and does not say why")
        if run.get("answer") and not any(r.get("solution") == "response-writer" and r.get("status") == "done" for r in every):
            found.append("an answer was given but the Response Writer did not run")
        return found
