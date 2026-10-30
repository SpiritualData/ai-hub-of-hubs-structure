"""The registry files and the arithmetic over them. Pure functions: no model call, no network."""
import re
from datetime import date
from pathlib import Path

from esoi import implementation
from esoi.tables import ids, read_csv

DATA = Path(__file__).resolve().parent / "registry"
STALENESS_DAYS = 90          # research older than this is stale (a quarter)
REGISTERED = ("builds_on", "compared", "no_hub_exists")
CALLS = ("adopt", "coexist", "keep", "watch", "avoid")   # the machine-readable call of an area's recommendation (hubs.csv ``call``)
CONNECT_CALLS = ("adopt", "coexist", "")                  # areas a consumer SHOULD be connected to; a blank call counts as coexist
CONNECTION_KINDS = ("by_config", "seam", "selectable", "fake_hub")   # checks that can only hold once a consumer has connected the area
CONFIG_SHARE_BAR = 0.5       # an area is "by configuration" when at least this share of its wired hub connections need no code


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


def findings_of(row, findings):
    """The researched candidates of one area. ``hubs.csv`` holds the area's id prefix in ``finding_id``; each row of
    ``hub_findings.csv`` carries ``<prefix>-<n>``, so every finding id is unique and the join stays one value per area."""
    own = re.compile(re.escape(row["finding_id"]) + r"-\d+")
    return [f for f in findings if own.fullmatch(f["finding_id"])]


def connections_of(area, connections, consumer):
    """The wired hub CONNECTIONS of an area: one row is one class of things gained through one hub (every tool an MCP server
    exposes, every engine SearXNG federates), never one row per single service. A prepared connection (``wired`` no) does not
    count: what could merely be added later is not a capability."""
    return [c for c in connections if c["area"] == area and c["consumer"] == consumer and c.get("wired", "yes") == "yes"]


def reinvented_of(area, integrations, consumer):
    """Single-service integrations a consumer hand-wires where a registered hub already covers them and no waiver gives a reason."""
    return [i for i in integrations if i["area"] == area and i["consumer"] == consumer
            and i["covered_by"].strip() and i["status"] != "waived"]


def combine(facts, connections):
    """Coverage, integration by configuration, freshness, code structure, reinvented integrations, and the score."""
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
    reinvented_free_share = sum(1 for f in facts if not f.get("reinvented")) / n
    code = (seam_share + selectable_share + clean_share) / 3
    out = dict(coverage=coverage, config_share=config_share, fresh_share=fresh_share,
               days_max=max(days) if days else None, days_mean=(sum(days) / len(days)) if days else None,
               seam_share=seam_share, selectable_share=selectable_share, clean_share=clean_share, to_connect=len(wanted),
               unconnected=sorted(f.get("area", "") for f in wanted if not f["seam"]),
               vendor_branches=sum(len(f["vendor_branches"]) for f in facts), code=code,
               reinvented=sum(len(f.get("reinvented", [])) for f in facts), waived=sum(f.get("waived", 0) for f in facts),
               reinvented_free_share=reinvented_free_share)
    out["score"] = (coverage + config_share + fresh_share + code + reinvented_free_share) / 5
    return out


@implementation("stay-current", "registry_scan")
class RegistryScan:
    """The registry freshness reading as one registered implementation of the stay-current seat."""
    days_since = staticmethod(days_since)
    combine = staticmethod(combine)
