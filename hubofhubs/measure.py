"""Reads the registry together with one consumer's code (a ``Binding``) and answers, per area, whether the hub-of-hubs idea
holds. ``evaluate`` returns the per-area facts and the combined numbers; ``check`` answers one case."""
import csv
from pathlib import Path

from esoi import implementation

from . import registry, scan
from .binding import Binding

KINDS = ("registered", "by_config", "fresh", "seam", "selectable", "core_clean", "fake_hub", "no_reinvented")


def solution_facts(records_dir, solution_id):
    """(authoritative metric id, implementation count, known) for a solution, from the consumer's ESOI records."""
    with open(Path(records_dir) / "solutions.csv", newline="", encoding="utf-8") as handle:
        solutions = {r["solution_id"]: r for r in csv.DictReader(handle)}
    with open(Path(records_dir) / "implementations.csv", newline="", encoding="utf-8") as handle:
        count = sum(1 for r in csv.DictReader(handle) if r["solution_id"] == solution_id)
    row = solutions.get(solution_id)
    return (row or {}).get("authoritative_metric_id", ""), count, row is not None


def declared(binding, solution_id):
    try:
        return binding.names_of(solution_id)
    except ValueError:
        return []


def evaluate(binding: Binding, folder=None, today=None):
    """({area: facts}, wired connections of this consumer, numbers). ``today`` (a date) defaults to the system clock."""
    hubs = registry.read("hubs.csv", folder)
    findings = registry.read("hub_findings.csv", folder)
    connections = registry.read("hub_capabilities.csv", folder)
    integrations = registry.read("hub_integrations.csv", folder)
    seats = {s["area"]: s for s in binding.seats}
    branches = scan.scan_core({a: registry.split(s["vendor_terms"]) for a, s in seats.items()}, binding.core_dir, binding.root)
    facts = {}
    for row in hubs:
        area = row["area"]
        seat = seats.get(area, {"seam_solution_id": "", "vendor_terms": "", "code_paths": ""})
        days = registry.days_since(row["last_researched"], today)
        wired = registry.connections_of(area, connections, binding.consumer)
        config = [c for c in wired if c["connect"] == "config"]
        seams = registry.split(seat["seam_solution_id"])      # an area may have several seats: it holds if any seat does
        records = [solution_facts(binding.records_dir, sid) for sid in seams]
        mine = [i for i in integrations if i["area"] == area and i["consumer"] == binding.consumer]
        facts[area] = dict(
            area=area, seat=row["seat"], call=(row.get("call") or "").strip().lower(), expected=registry.should_connect(row), days=days, status=row["status"], capabilities=len(wired), by_config=len(config),
            registered=row["status"] in registry.REGISTERED and bool(registry.findings_of(row, findings)),
            fresh=days is not None and days <= registry.STALENESS_DAYS,
            config_ok=bool(wired) and len(config) / len(wired) >= registry.CONFIG_SHARE_BAR,
            seam=bool([n for sid in seams for n in declared(binding, sid)]),
            selectable=any(m and c >= 2 and k for m, c, k in records),
            vendor_branches=branches.get(area, []),
            reinvented=[i["integration"] for i in registry.reinvented_of(area, integrations, binding.consumer)],
            waived=sum(1 for i in mine if i["status"] == "waived"),
            probe=binding.probes.get(area),
            code_paths=registry.split(seat["code_paths"]), cites=[c["evidence_path"] for c in wired])
    wired_all = [c for c in connections if c["consumer"] == binding.consumer and c.get("wired", "yes") == "yes"]
    return facts, wired_all, registry.combine(list(facts.values()), wired_all)


def probe(fact):
    if fact["probe"] is None:
        return {"holds": False, "note": "no probe yet: a fake hub has not been registered for this area"}
    try:
        ok, how = fact["probe"]()
    except Exception as exc:  # a probe that raises means the hub could not be added by configuration
        return {"holds": False, "note": f"{type(exc).__name__}: {exc}"}
    return {"holds": bool(ok), "note": how if ok else "not accepted: " + how}


def check(fact, kind):
    """One case: ``{holds, ...detail}`` for one area and one kind."""
    if kind == "fake_hub":
        return probe(fact)
    holds = {"registered": fact["registered"], "by_config": fact["config_ok"], "fresh": fact["fresh"],
             "seam": fact["seam"], "selectable": fact["selectable"], "core_clean": not fact["vendor_branches"],
             "no_reinvented": not fact["reinvented"]}[kind]
    return {"holds": holds, "days": fact["days"], "status": fact["status"], "capabilities": fact["capabilities"],
            "by_config": fact["by_config"], "vendor_branches": len(fact["vendor_branches"]),
            "first": (fact["vendor_branches"] or [""])[0], "reinvented": fact["reinvented"], "waived": fact["waived"]}


def metrics(facts, connections):
    return registry.combine(list(facts.values()), connections)


@implementation("connect-any-integration", "hub_of_hubs_scorer")
class HubScorer:
    """The hub-of-hubs scorer as one registered implementation of the connect-any-integration seat."""
    evaluate = staticmethod(evaluate)
    check = staticmethod(check)
    metrics = staticmethod(metrics)
