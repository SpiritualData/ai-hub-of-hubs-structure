"""Where Learning's investigations are kept and what is due: pure functions over the repository's CSV files (no model call, no network).

An investigation (Learning does reviews) is stored in ``investigations.csv`` and ``investigation_items.csv`` (the columns of ``investigation_record``); a registry
area's refresh is stored beside the registry (``hubofhubs/registry``). ``due`` is the answer to "what learning is due": every open investigation past its revisit
date, every experiment past its reevaluation date, and every registry area whose research is older than the registry's bar or was never recorded as an investigation,
each with the request to run, the most overdue first. ``finding_investigation`` finds the investigation that produced a registry finding: the finding's own
``investigation_id`` when it has one (``store`` writes it), else the area and the day it was researched, which is how rows written before the column are still found.

Files and columns named before the rename (``research.csv``, ``research_items.csv``, ``research_id``) are still read, in ``read_records`` and ``renamed`` only;
everything is written under the new names.
"""
import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from esoi import read_csv, split_ids

from hubofhubs.the_world.learning import investigation_record as inv
from hubofhubs.the_world.learning.research_freshness_reader import registry

ROOT = Path(__file__).resolve().parents[3]
SKIP = ("__pycache__", ".git", ".venv", "node_modules")
INVESTIGATIONS, ITEMS, EXPERIMENTS = "investigations.csv", "investigation_items.csv", "experiments.csv"
OLDER_FILES = {INVESTIGATIONS: "research.csv", ITEMS: "research_items.csv"}
OLDER_ID = "research_id"
WEEKLY = "learning-weekly-refresh"


def day_of(today: Any = "") -> date:
    return today if isinstance(today, date) else date.fromisoformat(today) if today else date.today()


def renamed(row: Mapping[str, str]) -> Dict[str, str]:
    """The row with an older ``research_id`` cell read as ``investigation_id`` (the one mapping for records written before the rename)."""
    out = dict(row)
    if OLDER_ID in out and "investigation_id" not in out:
        out["investigation_id"] = out.pop(OLDER_ID)
    return out


def read_records(folder: Path, name: str) -> List[Dict[str, str]]:
    """The rows of ``name`` in a folder, or of its older file name when only that exists, with the older id column read as the new one."""
    older = folder / OLDER_FILES.get(name, name)
    return [renamed(r) for r in read_csv(folder / name if (folder / name).exists() else older)]


def stale_areas(freshness: Any, today: str = "") -> List[str]:
    """The registry areas whose last research is older than the registry's ninety day bar, or has no date."""
    day = date.fromisoformat(today) if today else None
    return [row["area"] for row in registry.read("hubs.csv")
            if (age := freshness.days_since(row["last_researched"], day)) is None or age > registry.STALENESS_DAYS]


def files(root: Any, name: str) -> List[Path]:
    base = Path(root or ROOT) / "hubofhubs"
    return sorted(p for p in base.rglob(name) if not any(s in p.parts for s in SKIP))


def rows(root: Any, name: str) -> List[Dict[str, str]]:
    """Every row of the files called ``name`` (or, in a folder with only the older name, of that file) under the repository."""
    folders = sorted({p.parent for n in {name, OLDER_FILES.get(name, name)} for p in files(root, n)})
    return [r for folder in folders for r in read_records(folder, name)]


TOP_SOLUTION = "the-self"      # the hub's overall solution: the whole that acts on one request, where an investigation no narrower solution holds is filed


def solution_dir(solution_id: str) -> Optional[Path]:
    """The folder whose ``solutions.csv`` holds ``solution_id`` (the hub's own records, wherever the caller's store is)."""
    for path in files(None, "solutions.csv"):
        if any(r.get("solution_id") == solution_id for r in read_csv(path)):
            return path.parent
    return None


def parent_solution(solution_id: str) -> str:
    """The solution above ``solution_id``: the one the nearest ``intent.csv`` at or above its folder implements (empty at the top)."""
    folder = solution_dir(solution_id)
    base = ROOT / "hubofhubs"
    while folder is not None and base in (folder, *folder.parents):
        intent = folder / "intent.csv"
        refs = split_ids(next(iter(read_csv(intent)), {}).get("implements", "")) if intent.exists() else []
        parents = [ref.split(":", 1)[0] for ref in refs if ref.split(":", 1)[0] != solution_id]
        if parents:
            return parents[0]
        folder = folder.parent
    return ""


def ancestors(solution_id: str) -> List[str]:
    """The solutions above ``solution_id``, nearest first (``the-learning`` gives ``the-world``)."""
    out: List[str] = []
    current = parent_solution(solution_id)
    while current and current not in out:
        out.append(current)
        current = parent_solution(current)
    return out


def with_solution(links: Sequence[str], solution_id: str = "") -> Tuple[List[str], Dict[str, Any]]:
    """The links with at least one ``solution:<id>``: the caller's own, else the request's solution (``solution_id``, what the flow passes), else the top solution
    (``TOP_SOLUTION``). Returns the links and ``{"solution", "source" (links, request or top), "fallback"}``; the fallback is recorded in the investigation's limitations."""
    given = [link for link in links if link.startswith("solution:")]
    if given:
        return list(links), {"solution": given[0][9:], "source": "links", "fallback": False}
    if solution_id:
        return list(links) + [f"solution:{solution_id}"], {"solution": solution_id, "source": "request", "fallback": False}
    return list(links) + [f"solution:{TOP_SOLUTION}"], {"solution": TOP_SOLUTION, "source": "top", "fallback": True}


def norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def investigations_for(solution_id: str, include_ancestors: bool = True, today: Any = "", root: Any = None) -> List[Dict[str, str]]:
    """What was already looked into for a solution: the stored investigations (not superseded) linked to ``solution:<solution_id>`` and, with ``include_ancestors``,
    to the solutions above it up to the top, newest first. Each row also carries ``linked_to`` (the solution it matched) and ``fresh`` (``yes`` before its
    ``refresh_on`` date, else ``no``). A row with no solution link (written before links were required) matches no solution."""
    day = day_of(today)
    wanted = [solution_id] + (ancestors(solution_id) if include_ancestors else [])
    out = []
    for r in rows(root, INVESTIGATIONS):
        if (r.get("status") or "open") == "superseded":
            continue
        linked = [link[9:] for link in split_ids(r.get("links", "")) if link.startswith("solution:")]
        hit = next((s for s in wanted if s in linked), "")
        if hit:
            due_on = r.get("refresh_on") or ""
            out.append(dict(r, linked_to=hit, fresh="yes" if due_on and date.fromisoformat(due_on) > day else "no"))
    return sorted(out, key=lambda r: (r.get("done_on") or ""), reverse=True)


def earlier_for(question: str, size: str, links: Sequence[str], today: Any = "", root: Any = None) -> Optional[Dict[str, str]]:
    """The newest earlier investigation of the same question linked to these solutions or their ancestors, with ``state``: ``fresh`` (before its revisit date and
    of at least this size: answers the question), ``stale`` (past its revisit date) or ``partial`` (a smaller size than asked). None when there is none."""
    seen, found = set(), []
    for link in links:
        if link.startswith("solution:"):
            for r in investigations_for(link[9:], True, today, root):
                if r["investigation_id"] not in seen and norm(r.get("question", "")) == norm(question):
                    seen.add(r["investigation_id"])
                    found.append(r)
    if not found:
        return None
    best = sorted(found, key=lambda r: (r.get("done_on") or ""), reverse=True)[0]
    smaller = best.get("size") in inv.SIZES and inv.SIZES.index(best["size"]) < inv.SIZES.index(size)
    return dict(best, state="partial" if smaller else "fresh" if best["fresh"] == "yes" else "stale")


def record_of(row: Mapping[str, str], root: Any = None) -> Dict[str, Any]:
    """The stored investigation ``row`` as the record a new investigation returns (its items read from the store), marked reused."""
    columns = {c: row.get(c, "") for c in inv.COLUMNS}
    items = [{c: i.get(c, "") for c in inv.ITEM_COLUMNS} for i in rows(root, ITEMS) if i.get("investigation_id") == row["investigation_id"]]
    log = [dict(zip(("source", "query", "date", "hits"), [p.strip() for p in q.split("|")])) for q in inv.parts(columns["queries"])]
    reasons = {e.split(" ", 1)[1]: int(e.split(" ", 1)[0]) for e in inv.parts(columns["screened_out"]) if e.split(" ", 1)[0].isdigit() and " " in e}
    return {"investigation": columns, "items": items, "applied": [{"item": i["item_id"], "applied": i["applied"]} for i in items],
            "protocol": {"protocol_date": columns["protocol_date"], "question": columns["question"], "size": columns["size"], "criteria": columns["criteria"]},
            "queries": log, "screened_out": reasons, "gaps": inv.gaps(columns, items), "reused": True, "extends": ""}


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
    """What learning is due on ``today`` (ISO, default today): investigations past ``refresh_on``, experiments past ``reevaluate_time`` (the older name
    ``reevaluate_on`` is read too), and registry areas stale or never investigated. Each is ``kind`` (investigation, experiment, registry-area), ``id``, ``question``,
    ``links``, ``due_on``, ``days_overdue`` and the ``request`` to run."""
    day = day_of(today)
    out: List[Dict[str, Any]] = []
    covered = set()
    for r in rows(root, INVESTIGATIONS):
        if (r.get("status") or "open") != "open" or not r.get("refresh_on"):
            continue
        due_on = date.fromisoformat(r["refresh_on"])
        for link in split_ids(r.get("links", "")):
            if link.startswith("area:") and due_on > day:
                covered.add(link[5:])
        if due_on <= day:
            out.append({"kind": "investigation", "id": r["investigation_id"], "question": r.get("question", ""), "links": split_ids(r.get("links", "")),
                        "due_on": r["refresh_on"], "days_overdue": (day - due_on).days,
                        "request": f"Redo the investigation {r['investigation_id']} ({r.get('size', '')}): same question, new queries, then record it"})
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
                    "request": f"Investigate the registry area {area['area']} (a standard size review), store the record beside the registry, and update hubs.csv and hub_findings.csv"})
    return sorted(out, key=lambda d: (-d["days_overdue"], d["kind"], d["id"]))


def standing_schedule(last_run: str = "") -> Dict[str, Any]:
    """The weekly refresh as a schedule Proactivity reads (``name``, ``request``, ``cadence``, ``last_run``): when it is due the autopilot asks ``due_investigations``."""
    return {"name": WEEKLY, "title": "Refresh what the hub has learned", "kind": "standing-work", "cadence": "weekly", "last_run": last_run,
            "request": "Ask the-learning for what learning is due (due_investigations) and carry out each item as an investigation, most overdue first"}


def write_table(path: Path, columns: Sequence[str], rows_: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), lineterminator="\n")
        writer.writeheader()
        writer.writerows({c: r.get(c, "") for c in columns} for r in rows_)


def store(investigation: Mapping[str, Any], folder: Any = None) -> str:
    """Write an investigation's row and items into ``investigations.csv`` and ``investigation_items.csv`` of ``folder`` (default: beside the registry), replacing
    one of the same id and marking any earlier open investigation of the same links superseded. Records held under the older file names are carried over under
    the new ones. Returns the investigation id."""
    folder = Path(folder or registry.DATA)
    row = investigation["investigation"]
    held = [r for r in read_records(folder, INVESTIGATIONS) if r["investigation_id"] != row["investigation_id"]]
    for r in held:
        if r.get("links") == row.get("links") and r.get("question") == row.get("question") and (r.get("status") or "open") == "open":
            r["status"] = "superseded"
    items = [i for i in read_records(folder, ITEMS) if i["investigation_id"] != row["investigation_id"]] + list(investigation["items"])
    write_table(folder / INVESTIGATIONS, inv.COLUMNS, held + [row])
    write_table(folder / ITEMS, inv.ITEM_COLUMNS, items)
    link_findings(row["investigation_id"], row, folder)
    return row["investigation_id"]


def link_findings(investigation_id: str, row: Mapping[str, str], folder: Any = None) -> int:
    """Write ``investigation_id`` on the rows of ``hub_findings.csv`` (beside the investigation) that it produced: the rows of its areas (links ``area:<name>``)
    researched on the day it was done and not yet linked. The file is read and rewritten in one step with every column kept (an older ``research_id`` column is
    renamed), and the column is added at the end if the file has none. Returns how many rows were linked; a folder with no findings file is left alone."""
    path = Path(folder or registry.DATA) / "hub_findings.csv"
    if not path.exists():
        return 0
    areas = {link[5:] for link in split_ids(row.get("links", "")) if link.startswith("area:")}
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        names, held = [("investigation_id" if n == OLDER_ID else n) for n in (reader.fieldnames or [])], [renamed(r) for r in reader]
    if not areas:
        return 0
    linked = 0
    for f in held:
        if f.get("area") in areas and f.get("date_researched") == row.get("done_on") and not (f.get("investigation_id") or "").strip():
            f["investigation_id"] = investigation_id
            linked += 1
    if linked or "investigation_id" not in names:
        write_table(path, names + (["investigation_id"] if "investigation_id" not in names else []), held)
    return linked


def slug_id(day: str, question: str) -> str:
    """The id of an investigation written by hand: ``inv-<day>-<the first words of the question>``."""
    words = "-".join("".join(c if c.isalnum() else " " for c in question.lower()).split())[:40].strip("-")
    return f"inv-{day}-{words or 'investigation'}"


def record_investigation(spec: Any, folder: Any = None, today: str = "", allow_gaps: bool = False) -> Dict[str, Any]:
    """The one documented way to write an investigation without editing the CSV files. ``spec`` is a mapping (or the path of a JSON file holding one) with
    ``investigation`` (the cells of ``investigations.csv``; any left out are filled: ``kind`` review, ``status`` open, ``done_on`` today, ``protocol_date`` the
    same day, ``refresh_on`` from the size, ``investigation_id`` from the day and the question, ``links`` filed under the top solution when none names one) and
    ``items`` (one mapping per kept item, with the cells of ``investigation_items.csv``; ``item_id`` is numbered and ``investigation_id`` set). The record is
    checked against the standard first (``investigation_record.gaps``) and each kept item must name a ``source``; with gaps nothing is written and a
    ``ValueError`` lists them, unless ``allow_gaps`` is true. The row and items are then written by ``store`` (beside the registry unless ``folder`` is given).
    Returns ``{"investigation_id", "folder", "gaps"}``."""
    if not isinstance(spec, Mapping):
        with open(spec, encoding="utf-8") as handle:
            spec = json.load(handle)
    day = day_of(today).isoformat()
    row = {c: str(v) for c, v in dict(spec.get("investigation") or {}).items() if c in inv.COLUMNS}
    done = row.get("done_on") or day
    row.update(kind=row.get("kind") or "review", done_on=done, protocol_date=row.get("protocol_date") or done, status=row.get("status") or "open")
    row["size"] = row.get("size") or inv.choose_size(spec.get("weight"))
    links, _ = with_solution(split_ids(row.get("links", "")), "")
    row["links"] = inv.SEP.join(links)
    row["refresh_on"] = row.get("refresh_on") or inv.refresh_on(done, row["size"])
    row["investigation_id"] = row.get("investigation_id") or slug_id(done, row.get("question", ""))
    row["kept"] = row.get("kept") or str(len(spec.get("items") or ()))
    items = []
    for n, raw in enumerate(spec.get("items") or (), 1):
        item = {c: str(raw.get(c, "")) for c in inv.ITEM_COLUMNS}
        item.update(investigation_id=row["investigation_id"], item_id=item["item_id"] or f"i{n}")
        items.append(item)
    problems = inv.gaps(row, items) + [f"item {i['item_id']} names no source" for i in items if not i["source"].strip()]
    if problems and not allow_gaps:
        raise ValueError("investigation " + row["investigation_id"] + " not written: " + "; ".join(problems))
    where = Path(folder or registry.DATA)
    store({"investigation": row, "items": items}, where)
    return {"investigation_id": row["investigation_id"], "folder": str(where), "gaps": problems}


def finding_investigation(finding: Mapping[str, str], root: Any = None) -> str:
    """The id of the investigation that produced a registry finding: the finding's own ``investigation_id`` (or older ``research_id``) when it has one, else the
    investigation linked to its area and done on the day it was researched (rows written before the column). Empty when none."""
    own = renamed(finding).get("investigation_id") or ""
    if own.strip():
        return own.strip()
    area = (finding.get("area") or "").strip()
    for r in rows(root, INVESTIGATIONS):
        if f"area:{area}" in split_ids(r.get("links", "")) and r.get("done_on") == finding.get("date_researched"):
            return r["investigation_id"]
    return ""
