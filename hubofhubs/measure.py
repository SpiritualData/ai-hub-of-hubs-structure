"""Reads the registry together with one consumer's code (a ``Binding``) and answers, per area, whether the hub-of-hubs idea
holds. ``evaluate`` returns the per-area facts and the combined numbers; ``check`` answers one case."""
import csv
from pathlib import Path

from esoi import implementation

from . import registry, scan
from .binding import Binding

KINDS = ("registered", "by_config", "fresh", "seam", "selectable", "core_clean", "fake_hub", "no_reinvented")
# registry.AREA_KINDS are checked once per area, registry.SEAT_KINDS once per seat (the fact passed to ``check`` is the matching one).


def solution_facts(records_dir, solution_id):
    """(authoritative metric id, implementation count, known) for a solution, from the consumer's ESOI records."""
    with open(Path(records_dir) / "solutions.csv", newline="", encoding="utf-8") as handle:
        solutions = {r["solution_id"]: r for r in csv.DictReader(handle)}
    with open(Path(records_dir) / "implementations.csv", newline="", encoding="utf-8") as handle:
        count = sum(1 for r in csv.DictReader(handle) if r["solution_id"] == solution_id)
    row = solutions.get(solution_id)
    return (row or {}).get("authoritative_metric_id", ""), count, row is not None


class AreaFacts(dict):
    """The per-area facts ({area: facts}); ``seats`` holds the per-seat facts the numbers are read from."""
    seats = None


def declared(binding, solution_id):
    try:
        return binding.names_of(solution_id)
    except ValueError:
        return []


def bound_seats(binding, area_seat):
    """{seat: {solutions, terms, paths, areas}} from the consumer's rows, one entry per hub seat it uses. A row names a ``seat``
    and the ``areas`` its arms cover; a row that names only an ``area`` binds that area's seat (the earlier per-area form). Rows
    of one seat merge. An area listed under a seat that does not own it is an error: the registry's ``seat`` column decides."""
    out = {}
    for row in binding.seats:
        area = (row.get("area") or "").strip()
        seat = (row.get("seat") or area_seat.get(area, "")).strip()
        if seat not in area_seat.values():
            raise ValueError(f"binding row names no known hub seat: {row}")
        mine = out.setdefault(seat, dict(solutions=[], terms=[], paths=[], areas=[]))
        covered = registry.split(row.get("areas", "")) + ([area] if area else [])
        for name in covered:
            if area_seat.get(name) != seat:
                raise ValueError(f"area {name} belongs to seat {area_seat.get(name)}, not {seat}")
        for key, cell in (("solutions", row.get("seam_solution_id", "")), ("terms", row.get("vendor_terms", "")),
                          ("paths", row.get("code_paths", ""))):
            mine[key] += [v for v in registry.split(cell) if v not in mine[key]]
        mine["areas"] += [v for v in covered if v not in mine["areas"]]
    return out


def seat_probe(binding, seat, areas):
    """The fake-hub proof of a seat: the probes registered under the seat id or under any area its arms cover, all of which must
    hold. None when there is no probe at all (unprobed is not proven)."""
    fns = [binding.probes[k] for k in [seat, *areas] if k in binding.probes]
    if not fns:
        return None

    def run():
        got = [fn() for fn in fns]
        return all(ok for ok, _ in got), "; ".join(how for _, how in got)
    return run


def evaluate_seats(binding: Binding, folder=None, today=None):
    """(per-area facts, per-seat facts, wired connections of this consumer, numbers). The seam, selectable, by-configuration,
    vendor-branch and fake-hub readings are made once per SEAT; an area counts as an arm under its seat (``covered`` when the
    consumer's row for the seat names it), and an adopt or coexist area no arm covers is an arm gap. The per-area facts keep the
    area-level reading (seam and selectable of the seat, if the area is covered) for anyone who wants it."""
    hubs = registry.read("hubs.csv", folder)
    findings = registry.read("hub_findings.csv", folder)
    connections = registry.read("hub_capabilities.csv", folder)
    integrations = registry.read("hub_integrations.csv", folder)
    area_seat = {r["area"]: r["seat"] for r in hubs}
    bound = bound_seats(binding, area_seat)
    branches = scan.scan_core({seat: b["terms"] for seat, b in bound.items()}, binding.core_dir, binding.root)
    seat_facts = {}
    for seat in registry.seat_ids(hubs):
        b = bound.get(seat, dict(solutions=[], terms=[], paths=[], areas=[]))
        mine = [r for r in hubs if r["seat"] == seat]
        names = {r["area"] for r in mine}
        wired = [c for c in connections if c["area"] in names and c["consumer"] == binding.consumer and c.get("wired", "yes") == "yes"]
        config = [c for c in wired if c["connect"] == "config"]
        records = [solution_facts(binding.records_dir, sid) for sid in b["solutions"]]
        wanted = [r["area"] for r in mine if registry.should_connect(r)]
        seat_facts[seat] = dict(
            seat=seat, areas=sorted(names), expected=bool(wanted), to_connect=sorted(wanted), covered=sorted(b["areas"]),
            arm_gaps=sorted(a for a in wanted if a not in b["areas"]), bound=seat in bound, solutions=b["solutions"],
            capabilities=len(wired), by_config=len(config), config_ok=bool(wired) and len(config) / len(wired) >= registry.CONFIG_SHARE_BAR,
            seam=bool([n for sid in b["solutions"] for n in declared(binding, sid)]),
            selectable=any(m and c >= 2 and k for m, c, k in records), vendor_branches=branches.get(seat, []),
            probe=seat_probe(binding, seat, b["areas"]), code_paths=b["paths"], cites=[c["evidence_path"] for c in wired],
            days=None, status="", reinvented=[], waived=0)
    facts = AreaFacts()
    facts.seats = seat_facts
    for row in hubs:
        area, sf = row["area"], seat_facts[row["seat"]]
        days = registry.days_since(row["last_researched"], today)
        wired = registry.connections_of(area, connections, binding.consumer)
        config = [c for c in wired if c["connect"] == "config"]
        mine = [i for i in integrations if i["area"] == area and i["consumer"] == binding.consumer]
        covered = area in sf["covered"]
        facts[area] = dict(
            area=area, seat=row["seat"], call=(row.get("call") or "").strip().lower(), expected=registry.should_connect(row), days=days, status=row["status"], capabilities=len(wired), by_config=len(config),
            registered=row["status"] in registry.REGISTERED and bool(registry.findings_of(row, findings)),
            fresh=days is not None and days <= registry.STALENESS_DAYS,
            config_ok=bool(wired) and len(config) / len(wired) >= registry.CONFIG_SHARE_BAR,
            covered=covered, seam=covered and sf["seam"], selectable=covered and sf["selectable"],
            vendor_branches=sf["vendor_branches"] if covered else [],
            reinvented=[i["integration"] for i in registry.reinvented_of(area, integrations, binding.consumer)],
            waived=sum(1 for i in mine if i["status"] == "waived"),
            probe=binding.probes.get(area),
            code_paths=sf["code_paths"] if covered else [], cites=[c["evidence_path"] for c in wired])
    wired_all = [c for c in connections if c["consumer"] == binding.consumer and c.get("wired", "yes") == "yes"]
    return facts, seat_facts, wired_all, registry.combine(list(facts.values()), wired_all, list(seat_facts.values()))


def evaluate(binding: Binding, folder=None, today=None):
    """({area: facts}, wired connections of this consumer, numbers). ``today`` (a date) defaults to the system clock. The numbers
    read the code once per seat; ``evaluate_seats`` also returns the per-seat facts."""
    facts, _seat_facts, wired_all, numbers = evaluate_seats(binding, folder, today)
    return facts, wired_all, numbers


def probe(fact):
    if fact["probe"] is None:
        return {"holds": False, "note": "no probe yet: a fake hub has not been registered for this area or seat"}
    try:
        ok, how = fact["probe"]()
    except Exception as exc:  # a probe that raises means the hub could not be added by configuration
        return {"holds": False, "note": f"{type(exc).__name__}: {exc}"}
    return {"holds": bool(ok), "note": how if ok else "not accepted: " + how}


def check(fact, kind):
    """One case: ``{holds, ...detail}`` for one area (an AREA kind) or one seat (a SEAT kind) fact."""
    if kind == "fake_hub":
        return probe(fact)
    holds = {"registered": lambda: fact["registered"], "by_config": lambda: fact["config_ok"], "fresh": lambda: fact["fresh"],
             "seam": lambda: fact["seam"], "selectable": lambda: fact["selectable"], "core_clean": lambda: not fact["vendor_branches"],
             "no_reinvented": lambda: not fact.get("reinvented")}[kind]()
    return {"holds": holds, "days": fact.get("days"), "status": fact.get("status", ""), "capabilities": fact["capabilities"],
            "by_config": fact["by_config"], "vendor_branches": len(fact["vendor_branches"]),
            "first": (fact["vendor_branches"] or [""])[0], "reinvented": fact.get("reinvented", []), "waived": fact.get("waived", 0),
            "arm_gaps": fact.get("arm_gaps", [])}


def metrics(facts, connections, seat_facts=None):
    seat_facts = seat_facts if seat_facts is not None else getattr(facts, "seats", None)
    return registry.combine(list(facts.values()), connections, None if seat_facts is None else list(seat_facts.values()))


@implementation("connect-any-integration", "hub_of_hubs_scorer")
class HubScorer:
    """The hub-of-hubs scorer as one registered implementation of the connect-any-integration seat."""
    evaluate = staticmethod(evaluate)
    evaluate_seats = staticmethod(evaluate_seats)
    check = staticmethod(check)
    metrics = staticmethod(metrics)
