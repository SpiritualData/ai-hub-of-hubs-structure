"""Scoring for a case-driven evaluation: a case expects ``holds`` true (an ideal) and a consumer's implementation answers from the
registry and its code. ``aggregate`` prints the numbers: coverage, integration by configuration, reinvented integrations,
research freshness, code structure and the combined score."""
from . import registry

REASONS = {
    "registered": lambda o: f"status {o.get('status')} or no recorded finding",
    "by_config": lambda o: f"{o.get('by_config')} of {o.get('capabilities')} wired hub connections by configuration",
    "fresh": lambda o: f"researched {o.get('days')} days ago",
    "seam": lambda o: "no declared implementation behind the seat's solutions",
    "selectable": lambda o: "the seat's solutions have no authoritative metric or fewer than two implementations",
    "no_reinvented": lambda o: f"hand-wired where a hub covers it: {', '.join(o.get('reinvented') or [])}",
}


def score_case(fn, case):
    try:
        out = fn(case["kind"], case["args"])
    except Exception as exc:  # an implementation that raises fails the case
        if type(exc).__name__ == "BudgetExceeded":
            raise
        return dict(ok=False, got=case["kind"], note=f"raised {type(exc).__name__}: {exc}", out={})
    ok = out.get("holds") is True
    kind = case["kind"]
    note = out.get("note") or (out.get("first") if kind == "core_clean" else "") or (REASONS[kind](out) if kind in REASONS else "")
    return dict(ok=ok, got=kind, out=out, area=case["args"].get("area") or case["args"].get("seat"), note="ok" if ok else note)


def aggregate(rows, facts, connections):
    from .measure import metrics
    m = metrics(facts, connections)
    stale = sorted(a for a, f in facts.items() if not f["fresh"])
    kinds = {}
    for r in rows:
        done, total = kinds.get(r.get("got"), (0, 0))
        kinds[r.get("got")] = (done + bool(r.get("ok")), total + 1)
    per_kind = ", ".join(f"{k} {d}/{t}" for k, (d, t) in sorted(kinds.items()))
    return (f"checks passed {sum(1 for r in rows if r.get('ok'))}/{len(rows)} ({per_kind}); registry reading "
            f"(the same for every implementation): score {m['score']:.3f} = mean(coverage {m['coverage']:.2f}, "
            f"integration-by-config {m['config_share']:.2f}, no reinvented integration {m['reinvented_free_share']:.2f}, "
            f"freshness {m['fresh_share']:.2f}, code structure {m['code']:.2f}); research age max {m['days_max']} mean "
            f"{m['days_mean']:.1f} days (bar {registry.STALENESS_DAYS}), stale areas {stale or 'none'}; code: one seam "
            f"{m['seam_share']:.2f} and selectable by metric {m['selectable_share']:.2f} (both over the {m.get('seats_to_connect', m['to_connect'])} {'seats with an adopt or coexist area' if 'seats_to_connect' in m else 'areas whose call is adopt or coexist'}; {len(m.get('arm_gaps') or [])} adopt or coexist areas have no arm yet), core free of vendor branches "
            f"{m['clean_share']:.2f} ({m['vendor_branches']} branches); hand-wired integrations a hub covers "
            f"{m['reinvented']} ({m['waived']} more waived with a reason)")
