"""ResearchLog: what was researched for one solution, when, and what is due. Pure functions over the repo's CSV files: no model
call, no network.

Sources and how each links to a solution (a link is made only when the file states it; nothing is guessed):
- ``knowledge.csv`` (any folder): rows whose ``solution_ids`` name the solution; dated ``recorded``, expiring ``expiration``.
- ``public_priors.csv``: the solution is the one whose ``solutions.csv`` sits in the same folder; dated ``date_checked``, expiring ``expires``.
- public evidence: ``registry/hub_evidence.csv`` rows whose ``seat`` is the solution id (the seat column holds solution ids), plus the
  evidence ids the solution's priors cite in ``basis_evidence_ids``, found in ``registry/hub_evidence.csv`` or ``esoi/evidence.csv``.
  ``date_checked`` is the date; there is no expiry column, so the default applies.
- registry research: ``registry/hubs.csv`` rows whose ``seat`` is the solution id; dated ``last_researched``.
Not linkable: a row of ``esoi/evidence.csv`` that no prior cites and that is not in ``hub_evidence.csv`` (it has no solution column).
An entry with no expiry of its own expires ``STALENESS_DAYS`` after its date.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

from esoi import read_csv, split_ids

from hubofhubs.the_world.learning.research_freshness_reader.registry import STALENESS_DAYS

ROOT = Path(__file__).resolve().parents[3]
CLIP = 160
SKIP = ("__pycache__", ".git", ".venv", "node_modules")


def _iso(text):
    try:
        return date.fromisoformat((text or "").strip()).isoformat()
    except ValueError:
        return ""


def _clip(text):
    text = " ".join((text or "").split())
    return text if len(text) <= CLIP else text[:CLIP - 3].rstrip() + "..."


def _files(root, name):
    return sorted(p for p in (root / "hubofhubs").rglob(name) if not any(s in p.parts for s in SKIP))


def _rel(path, root):
    return path.relative_to(root).as_posix()


def _entry(root, day, kind, what, path, row_id, expires):
    when = _iso(day)
    if not when:
        return None
    end = _iso(expires) or (date.fromisoformat(when) + timedelta(days=STALENESS_DAYS)).isoformat()
    return dict(date=when, kind=kind, what=_clip(what), source=f"{_rel(path, root)} {row_id}", expires=_iso(expires), end=end)


def _solution_folders(root):
    """Every solution id with the folder of the solutions.csv that declares it."""
    return [(r["solution_id"], p.parent) for p in _files(root, "solutions.csv") for r in read_csv(p) if r.get("solution_id")]


def research_log(solution_id, root=None, today=None):
    """Everything researched for ``solution_id``, newest first, with what is due. ``root`` is the repo root (default: this repo),
    ``today`` an ISO date or date (default: the system date). ``expires`` is the entry's own expiry or ``""``; ``due`` and
    ``overdue`` use the expiry or, when blank, the date plus ``STALENESS_DAYS``; ``next_due`` is the earliest of those."""
    root = Path(root or ROOT)
    day = today if isinstance(today, date) else date.fromisoformat(today) if today else date.today()
    found = []
    for path in _files(root, "knowledge.csv"):
        for r in read_csv(path):
            if solution_id in split_ids(r.get("solution_ids", "")):
                found.append(_entry(root, r.get("recorded"), "knowledge", r.get("claim"), path, r.get("knowledge_id", ""), r.get("expiration")))
    cited = set()
    for sid, folder in _solution_folders(root):
        if sid != solution_id:
            continue
        path = folder / "public_priors.csv"
        for r in read_csv(path):
            cited.update(split_ids(r.get("basis_evidence_ids", "")))
            what = f"{r.get('arm_id', '')}: grade {r.get('grade', '')}, prior {r.get('prior', '')}. {r.get('reason', '')}"
            found.append(_entry(root, r.get("date_checked"), "prior", what, path, r.get("arm_id", ""), r.get("expires")))
    seen = set()
    for path in (root / "hubofhubs" / "registry" / "hub_evidence.csv", root / "esoi" / "evidence.csv"):
        for r in read_csv(path):
            eid = r.get("evidence_id", "")
            if eid in seen or not (eid in cited or r.get("seat") == solution_id):
                continue
            seen.add(eid)
            what = f"{r.get('candidate', '')}, {r.get('dimension', '')}: {r.get('measure', '')} = {r.get('value', '')} {r.get('unit', '')}"
            found.append(_entry(root, r.get("date_checked") or r.get("date_published"), "evidence", what, path, eid, ""))
    hubs = root / "hubofhubs" / "registry" / "hubs.csv"
    for r in read_csv(hubs):
        if r.get("seat") == solution_id:
            found.append(_entry(root, r.get("last_researched"), "registry", f"{r.get('area', '')}: {r.get('recommendation', '')}",
                                hubs, r.get("area", ""), ""))
    items = sorted((e for e in found if e), key=lambda e: (e["date"], e["source"]), reverse=True)
    for e in items:
        e["due"] = e.pop("end") < day.isoformat()
    ends = sorted(_iso(e["expires"]) or (date.fromisoformat(e["date"]) + timedelta(days=STALENESS_DAYS)).isoformat() for e in items)
    return dict(solution=solution_id, entries=items, last=items[0]["date"] if items else "", next_due=ends[0] if ends else "",
                overdue=[e for e in items if e["due"]], never=not items)


def due_solutions(root=None, today=None):
    """Every solution with overdue or no research, overdue first (earliest ``next_due`` first), then the never researched."""
    root = Path(root or ROOT)
    logs = [research_log(sid, root, today) for sid in dict.fromkeys(s for s, _f in _solution_folders(root))]
    late = sorted((g for g in logs if g["overdue"]), key=lambda g: g["next_due"])
    return late + [g for g in logs if g["never"]]


def render(log):
    """The plain-text table and summary line of one log."""
    lines = [f"{e['date']}  {e['kind']:<9}  {e['expires'] or '-':<10}  {e['what']}" + ("  [overdue]" if e["due"] else "") for e in log["entries"]]
    lines.append("never researched" if log["never"] else f"last researched {log['last']}; next due {log['next_due']}")
    return "\n".join(lines)


def main(argv):
    if argv[:1] != ["research"] or len(argv) != 2:
        print("usage: python -m hubofhubs.the_world.learning.research_log research <solution_id> | --due")
        return 2
    if argv[1] == "--due":
        for g in due_solutions():
            print(f"{g['solution']}  never researched" if g["never"]
                  else f"{g['solution']}  {len(g['overdue'])} overdue of {len(g['entries'])}; next due {g['next_due']}")
        return 0
    print(render(research_log(argv[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
