"""The registry files and the arithmetic over them. Pure functions: no model call, no network."""
import csv
from datetime import date
from pathlib import Path

from esoi import implementation

DATA = Path(__file__).resolve().parent / "registry"
STALENESS_DAYS = 90          # research older than this is stale (a quarter)
REGISTERED = ("builds_on", "compared", "no_hub_exists")
CONFIG_SHARE_BAR = 0.5       # an area is "by configuration" when at least this share of its wired hub connections need no code


def read(name, folder=None):
    with open(Path(folder or DATA) / name, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def today(clock=None):
    """``clock`` (a date) when given, else today from the system clock. The hub reads no environment: a test ages the
    registry by passing a date."""
    return clock if clock is not None else date.today()


def days_since(iso, clock=None):
    try:
        return (today(clock) - date.fromisoformat(iso)).days
    except (TypeError, ValueError):
        return None


def split(cell):
    return [x.strip() for x in (cell or "").split(";") if x.strip()]


def parse_hubs(cell):
    """``name|url|license`` entries joined by semicolons -> list of (name, url, license)."""
    out = []
    for entry in (cell or "").split(";"):
        if entry.strip():
            parts = (entry.split("|") + ["", ""])[:3]
            out.append(tuple(p.strip() for p in parts))
    return out


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
    seam_share = sum(1 for f in facts if f["seam"]) / n
    selectable_share = sum(1 for f in facts if f["selectable"]) / n
    clean_share = sum(1 for f in facts if not f["vendor_branches"]) / n
    reinvented_free_share = sum(1 for f in facts if not f.get("reinvented")) / n
    code = (seam_share + selectable_share + clean_share) / 3
    out = dict(coverage=coverage, config_share=config_share, fresh_share=fresh_share,
               days_max=max(days) if days else None, days_mean=(sum(days) / len(days)) if days else None,
               seam_share=seam_share, selectable_share=selectable_share, clean_share=clean_share,
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
