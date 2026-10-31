"""The registry files and the arithmetic over them. Pure functions: no model call, no network."""
import re
from datetime import date
from pathlib import Path

from esoi import implementation
from esoi.tables import ids, read_csv
from . import arm_needs as needs

DATA = Path(__file__).resolve().parent / "registry"
STALENESS_DAYS = 90          # research older than this is stale (a quarter)
REGISTERED = ("builds_on", "compared", "no_hub_exists")
CALLS = ("adopt", "coexist", "keep", "watch", "avoid")   # the machine-readable call of an area's recommendation (hubs.csv ``call``)
CONNECT_CALLS = ("adopt", "coexist", "")                  # areas a consumer SHOULD be connected to; a blank call counts as coexist
CONNECTION_KINDS = ("by_config", "seam", "selectable", "fake_hub")   # checks that can only hold once a consumer has connected the area
AREA_KINDS = ("registered", "fresh", "no_reinvented")                              # facts of the research itself: checked once per area
SEAT_KINDS = ("by_config", "seam", "selectable", "core_clean", "fake_hub")           # facts of a consumer's code: checked once per seat
CONFIG_SHARE_BAR = 0.5       # an area is "by configuration" when at least this share of its wired hub connections need no code

# Public evidence (hub_evidence.csv): numbers other people measured, never our own result rows. See docs/explanation/public-evidence.md.
EVIDENCE_DIMENSIONS = ("quality", "token_efficiency", "speed", "cost", "reliability", "safety", "maintenance")
EVIDENCE_BETTER = ("higher", "lower")
EVIDENCE_SOURCE_KINDS = ("independent_benchmark", "replication", "peer_reviewed", "vendor_reported", "maintainer_reported",
                         "community_report", "own_run")
EVIDENCE_INDEPENDENT = ("yes", "no", "unknown")
EVIDENCE_METHOD = ("yes", "partial", "no")
EVIDENCE_STATUS = ("live", "saturated", "archived", "contamination_risk", "unknown")


def read(name, folder=None):
    return read_csv(Path(folder or DATA) / name)


def today(clock=None):
    """``clock`` (a date) when given, else today from the system clock. The hub reads no environment: a test ages the
    registry by passing a date."""
    return clock if clock is not None else date.today()


def days_since(iso, clock=None):
    try:
        return (today(clock) - date.fromisoformat(iso)).days
    except (TypeError, ValueError):
        return None


split = ids


def parse_hubs(cell):
    """``name|url|license`` entries joined by semicolons -> list of (name, url, license)."""
    out = []
    for entry in (cell or "").split(";"):
        if entry.strip():
            parts = (entry.split("|") + ["", ""])[:3]
            out.append(tuple(p.strip() for p in parts))
    return out


def should_connect(row):
    """Whether the area's call says a consumer should be connected to it: ADOPT, or COEXIST (a blank call is read as coexist, so an
    area nobody classified is never excused). KEEP, WATCH and AVOID are decisions not to connect, so a consumer without a seam
    there is not behind. Pure data: the same for every consumer."""
    return (row.get("call") or "").strip().lower() in CONNECT_CALLS


def seat_ids(hubs):
    """The seats that own at least one area, in order of first appearance in ``hubs.csv`` (the ``seat`` column is the mapping
    from each area to the hub seat that owns it; an area is an arm or tool inside its seat)."""
    return list(dict.fromkeys(r["seat"] for r in hubs))


def seat_should_connect(hubs, seat):
    """A seat should be connected when at least one of its areas should be (adopt, coexist or blank)."""
    return any(should_connect(r) for r in hubs if r["seat"] == seat)


def findings_of(row, findings):
    """The researched candidates of one area. ``hubs.csv`` holds the area's id prefix in ``finding_id``; each row of
    ``hub_findings.csv`` carries ``<prefix>-<n>``, so every finding id is unique and the join stays one value per area."""
    own = re.compile(re.escape(row["finding_id"]) + r"-\d+")
    return [f for f in findings if own.fullmatch(f["finding_id"])]


def evidence_of(area, evidence, candidate=None):
    """The public evidence rows of one area (and of one candidate when given): the data the esoi evidence grader reads."""
    return [e for e in evidence if e["area"] == area and (candidate is None or e["candidate"] == candidate)]


def connections_of(area, connections, consumer):
    """The wired hub CONNECTIONS of an area: one row is one class of things gained through one hub (every tool an MCP server
    exposes, every engine SearXNG federates), never one row per single service. A prepared connection (``wired`` no) does not
    count: what could merely be added later is not a capability."""
    return [c for c in connections if c["area"] == area and c["consumer"] == consumer and c.get("wired", "yes") == "yes"]


def reinvented_of(area, integrations, consumer):
    """Single-service integrations a consumer hand-wires where a registered hub already covers them and no waiver gives a reason."""
    return [i for i in integrations if i["area"] == area and i["consumer"] == consumer
            and i["covered_by"].strip() and i["status"] != "waived"]


def combine(facts, connections, seats=None):
    """Coverage, integration by configuration, freshness, code structure, reinvented integrations, and the score.

    ``facts`` are per area. With ``seats`` (per-seat facts) the code-structure terms are read once per seat: the seam and
    selectable shares are over the seats that should be connected (a seat with an adopt or coexist area), the vendor-branch share
    is over all seats, and an adopt or coexist area that no arm of the consumer covers is an ARM GAP (``arm_gaps``), not a
    missing binding. Without ``seats`` they are read per area, as before."""
    n = len(facts) or 1
    days = [f["days"] for f in facts if f["days"] is not None]
    coverage = sum(1 for f in facts if f["registered"]) / n
    config_share = (sum(1 for c in connections if c["connect"] == "config") / len(connections)) if connections else 0.0
    fresh_share = sum(1 for f in facts if f["fresh"]) / n
    # seam and selectable are read over the areas that SHOULD be connected (call adopt or coexist): an area called KEEP, WATCH or
    # AVOID has no seam to miss. The weights and the 1/3 split of ``code`` are unchanged. With none to connect the shares are 1.
    wanted = [f for f in facts if f.get("expected", True)]
    seam_share = sum(1 for f in wanted if f["seam"]) / len(wanted) if wanted else 1.0
    selectable_share = sum(1 for f in wanted if f["selectable"]) / len(wanted) if wanted else 1.0
    clean_share = sum(1 for f in facts if not f["vendor_branches"]) / n
    out_seats = {}
    if seats is not None:
        wanted_seats = [f for f in seats if f.get("expected", True)]
        seam_share = sum(1 for f in wanted_seats if f["seam"]) / len(wanted_seats) if wanted_seats else 1.0
        selectable_share = sum(1 for f in wanted_seats if f["selectable"]) / len(wanted_seats) if wanted_seats else 1.0
        clean_share = sum(1 for f in seats if not f["vendor_branches"]) / len(seats) if seats else 1.0
        out_seats = dict(seats_to_connect=len(wanted_seats), unconnected_seats=sorted(f["seat"] for f in wanted_seats if not f["seam"]),
                         arm_gaps=sorted(f.get("area", "") for f in wanted if not f.get("covered")))
    reinvented_free_share = sum(1 for f in facts if not f.get("reinvented")) / n
    code = (seam_share + selectable_share + clean_share) / 3
    out = dict(coverage=coverage, config_share=config_share, fresh_share=fresh_share,
               days_max=max(days) if days else None, days_mean=(sum(days) / len(days)) if days else None,
               seam_share=seam_share, selectable_share=selectable_share, clean_share=clean_share, to_connect=len(wanted),
               unconnected=sorted(f.get("area", "") for f in wanted if not f["seam"]),
               vendor_branches=sum(len(f["vendor_branches"]) for f in (seats if seats is not None else facts)), code=code,
               reinvented=sum(len(f.get("reinvented", [])) for f in facts), waived=sum(f.get("waived", 0) for f in facts),
               reinvented_free_share=reinvented_free_share)
    out.update(out_seats)
    out["score"] = (coverage + config_share + fresh_share + code + reinvented_free_share) / 5
    return out


@implementation("read-registry-freshness", "registry_scan")
class RegistryScan:
    """The registry freshness reading as one registered implementation of the read-registry-freshness solution."""
    REQUIRES = ()     # pure functions over the registry files
    days_since = staticmethod(days_since)
    combine = staticmethod(combine)
