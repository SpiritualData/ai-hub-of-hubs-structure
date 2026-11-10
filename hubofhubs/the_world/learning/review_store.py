"""Where Learning's reviews are kept and what is due: pure functions over the repository's CSV files (no model call, no network).

A review is stored in ``research.csv`` and ``research_items.csv`` (the columns of ``research_review``); a registry area's refresh is stored beside the registry
(``hubofhubs/registry``). ``due`` is the answer to "what learning is due": every open review past its revisit date, every experiment past its reevaluation date,
and every registry area whose research is older than the registry's bar or was never recorded as a review, each with the request to run, the most overdue first.
``finding_review`` finds the review that produced a registry finding: the finding's own ``research_id`` when it has one (``store`` writes it), else the area and the
day it was researched, which is how rows written before the column are still found.
"""
import csv
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import read_csv, split_ids

from hubofhubs.the_world.learning import research_review as rr
from hubofhubs.the_world.learning.research_freshness_reader import registry

ROOT = Path(__file__).resolve().parents[3]
SKIP = ("__pycache__", ".git", ".venv", "node_modules")
RESEARCH, ITEMS, EXPERIMENTS = "research.csv", "research_items.csv", "experiments.csv"
WEEKLY = "learning-weekly-refresh"


def day_of(today: Any = "") -> date:
    return today if isinstance(today, date) else date.fromisoformat(today) if today else date.today()


def stale_areas(freshness: Any, today: str = "") -> List[str]:
    """The registry areas whose last research is older than the registry's ninety day bar, or has no date."""
    day = date.fromisoformat(today) if today else None
    return [row["area"] for row in registry.read("hubs.csv")
            if (age := freshness.days_since(row["last_researched"], day)) is None or age > registry.STALENESS_DAYS]


def files(root: Any, name: str) -> List[Path]:
    base = Path(root or ROOT) / "hubofhubs"
    return sorted(p for p in base.rglob(name) if not any(s in p.parts for s in SKIP))


def rows(root: Any, name: str) -> List[Dict[str, str]]:
    return [r for p in files(root, name) for r in read_csv(p)]


def area_request(area: Mapping[str, str]) -> Dict[str, Any]:
    """The arguments of a registry area's refresh review: its question, the decision it informs and the solution it bears on. The weight is that of a registry
    area (it selects what a consumer connects), so the size is standard."""
    name = area["area"]
    return {"question": f"Which open-source hubs for {name.replace('_', ' ')} were released or changed since {area.get('last_researched') or 'the last review'}, "
                        "and are any adoptable?",
            "decision": f"adopt, adapt or keep the recommendation for {name}", "weight": {"selects": True},
            "links": [f"area:{name}"] + ([f"solution:{area['seat']}"] if area.get("seat") else []), "refresh_days": registry.STALENESS_DAYS,
            "candidates": split_ids(area.get("candidate_hubs", "").replace(";", ";"))}


def due(today: Any = "", root: Any = None, freshness: Any = None) -> List[Dict[str, Any]]:
    """What learning is due on ``today`` (ISO, default today): reviews past ``refresh_on``, experiments past ``reevaluate_time`` (the older name ``reevaluate_on`` is read too), and registry areas stale or
    never reviewed. Each is ``kind`` (review, experiment, registry-area), ``id``, ``question``, ``links``, ``due_on``, ``days_overdue`` and the ``request`` to run."""
    day = day_of(today)
    out: List[Dict[str, Any]] = []
    covered = set()
    for r in rows(root, RESEARCH):
        if (r.get("status") or "open") != "open" or not r.get("refresh_on"):
            continue
        due_on = date.fromisoformat(r["refresh_on"])
        for link in split_ids(r.get("links", "")):
            if link.startswith("area:") and due_on > day:
                covered.add(link[5:])
        if due_on <= day:
            out.append({"kind": "review", "id": r["research_id"], "question": r.get("question", ""), "links": split_ids(r.get("links", "")), "due_on": r["refresh_on"],
                        "days_overdue": (day - due_on).days, "request": f"Redo the review {r['research_id']} ({r.get('size', '')}): same question, new queries, then record it"})
    for e in rows(root, EXPERIMENTS):
        when = e.get("reevaluate_time") or e.get("reevaluate_on") or ""
        if (e.get("status") or "") == "running" and when and date.fromisoformat(when) <= day:
            due_on = date.fromisoformat(when)
            out.append({"kind": "experiment", "id": e["experiment_id"], "question": e.get("research_question") or e.get("focus", ""), "links": split_ids(e.get("links", "")),
                        "due_on": when, "days_overdue": (day - due_on).days,
                        "request": f"Reevaluate the experiment {e['experiment_id']}: what was learned, what it changed, continue, change or end"})
    for area in registry.read("hubs.csv"):
        last = (area.get("last_researched") or "").strip()
        age = (day - date.fromisoformat(last)).days if last else None
        if area["area"] in covered or (age is not None and age <= registry.STALENESS_DAYS):
            continue
        request = area_request(area)
        due_on = date.fromordinal(date.fromisoformat(last).toordinal() + registry.STALENESS_DAYS).isoformat() if last else ""
        out.append({"kind": "registry-area", "id": area["area"], "question": request["question"], "links": request["links"], "due_on": due_on,
                    "days_overdue": (age - registry.STALENESS_DAYS) if age is not None else 10 ** 4,
                    "request": f"Review the registry area {area['area']} (standard size), store the record beside the registry, and update hubs.csv and hub_findings.csv"})
    return sorted(out, key=lambda d: (-d["days_overdue"], d["kind"], d["id"]))


def standing_schedule(last_run: str = "") -> Dict[str, Any]:
    """The weekly refresh as a schedule Proactivity reads (``name``, ``request``, ``cadence``, ``last_run``): when it is due the autopilot asks ``due_reviews``."""
    return {"name": WEEKLY, "title": "Refresh what the hub has learned", "kind": "standing-work", "cadence": "weekly", "last_run": last_run,
            "request": "Ask the-learning for what learning is due (due_reviews) and run each item as a review, most overdue first"}


def write_table(path: Path, columns: Sequence[str], rows_: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows({c: r.get(c, "") for c in columns} for r in rows_)


def store(review: Mapping[str, Any], folder: Any = None) -> str:
    """Write a review's row and items into ``research.csv`` and ``research_items.csv`` of ``folder`` (default: beside the registry), replacing a review of the
    same id and marking any earlier open review of the same links superseded. Returns the review id."""
    folder = Path(folder or registry.DATA)
    row = review["research"]
    held = [r for r in read_csv(folder / RESEARCH) if r["research_id"] != row["research_id"]]
    for r in held:
        if r.get("links") == row.get("links") and r.get("question") == row.get("question") and (r.get("status") or "open") == "open":
            r["status"] = "superseded"
    items = [i for i in read_csv(folder / ITEMS) if i["research_id"] != row["research_id"]] + list(review["items"])
    write_table(folder / RESEARCH, rr.COLUMNS, held + [row])
    write_table(folder / ITEMS, rr.ITEM_COLUMNS, items)
    link_findings(row["research_id"], row, folder)
    return row["research_id"]


def link_findings(research_id: str, row: Mapping[str, str], folder: Any = None) -> int:
    """Write ``research_id`` on the rows of ``hub_findings.csv`` (beside the review) that this review produced: the rows of its areas (links ``area:<name>``) researched on
    the day it was done and not yet linked. The file is read and rewritten in one step with every column kept, and the column is added at the end if the file has none.
    Returns how many rows were linked; a folder with no findings file is left alone."""
    path = Path(folder or registry.DATA) / "hub_findings.csv"
    if not path.exists():
        return 0
    areas = {link[5:] for link in split_ids(row.get("links", "")) if link.startswith("area:")}
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        names, held = list(reader.fieldnames or []), list(reader)
    if not areas:
        return 0
    linked = 0
    for f in held:
        if f.get("area") in areas and f.get("date_researched") == row.get("done_on") and not (f.get("research_id") or "").strip():
            f["research_id"] = research_id
            linked += 1
    if linked or "research_id" not in names:
        write_table(path, names + (["research_id"] if "research_id" not in names else []), held)
    return linked


def finding_review(finding: Mapping[str, str], root: Any = None) -> str:
    """The id of the review that produced a registry finding: the finding's own ``research_id`` when it has one, else the review linked to its area and done on the
    day it was researched (rows written before the column). Empty when none."""
    if (finding.get("research_id") or "").strip():
        return finding["research_id"].strip()
    area = (finding.get("area") or "").strip()
    for r in rows(root, RESEARCH):
        if f"area:{area}" in split_ids(r.get("links", "")) and r.get("done_on") == finding.get("date_researched"):
            return r["research_id"]
    return ""
