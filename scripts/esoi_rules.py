"""The hub's own esoi rule, named in ``esoi.toml`` as a plugin (``esoi rules`` lists it with esoi's own).

L1: research that informs the hub is recorded as an investigation. A registry finding (a row of ``hubofhubs/registry/hub_findings.csv``) researched on or after
``[rules.L1] since`` names an investigation that exists (its own ``investigation_id``, or the one linked to its area and day), and every kept item of every
investigation carries a source. Before ``[rules.L1] fail_from`` the findings are advisory (shown by ``esoi check``, never a failure); on and after it they fail.
Waive as the finding id or the investigation id. Metric revisions are not covered yet: a metric record has no date or investigation column, so there is nothing
to read (a column needs the owner's approval of the record template).
"""
from datetime import date
from typing import List

from esoi import RuleGroup
from esoi import RuleContext as Context

FINDINGS = "hub_findings.csv"


def read_findings(root) -> List[dict]:
    import csv
    path = root / "hubofhubs" / "registry" / FINDINGS
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle))


def problems(ctx: Context) -> List[str]:
    """The L1 findings, each as a line opening with ``L1``."""
    from hubofhubs.the_world.learning import investigation_store as store
    root = ctx.root
    since = str(ctx.config.option("L1", "since", "")) or "9999-12-31"
    known = {r["investigation_id"] for r in store.rows(root, store.INVESTIGATIONS)}
    out: List[str] = []
    for f in read_findings(root):
        if (f.get("date_researched") or "") < since or ctx.waived("L1", f["finding_id"]):
            continue
        found = store.finding_investigation(f, root)
        if not found:
            out.append(f"L1 {f['finding_id']}: researched {f['date_researched']} (on or after {since}) and names no investigation; record one with `ahohs investigation record FILE` and set investigation_id")
        elif found not in known:
            out.append(f"L1 {f['finding_id']}: names the investigation {found}, which is not in investigations.csv")
    for item in store.rows(root, store.ITEMS):
        key = f"{item.get('investigation_id')}:{item.get('item_id')}"
        if not (item.get("source") or "").strip() and not ctx.waived("L1", key):
            out.append(f"L1 {key}: a kept item has no source")
    return out


def research_recorded(ctx: Context) -> List[str]:
    """Advisory before ``fail_from`` (to ``ctx.advisory``), failing from it."""
    found = problems(ctx)
    fail_from = str(ctx.config.option("L1", "fail_from", ""))
    if fail_from and date.today().isoformat() >= fail_from:
        return found
    ctx.advisory.extend(found)
    return []


RULES = [RuleGroup({"L1": "Research that informs a registry finding is recorded as an investigation: a finding researched on or after `[rules.L1] since` names an investigation "
                          "that exists, and every kept item has a source (advisory until `fail_from`)."}, research_recorded)]
