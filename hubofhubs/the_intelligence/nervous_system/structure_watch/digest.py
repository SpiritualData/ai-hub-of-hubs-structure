"""The digest of a structure watch, built in code and never by a model: what changed in the records since the last watch, what the recent runs did, what is planned
next, and the findings computed from the records by rule. ``structure`` is plain data: ``tables`` (``solutions``, ``implementations``, ``metrics``, ``experiments``,
``investigations``, ``milestones`` as lists of rows), ``results`` (rows with ``date`` and ``component``), ``runs`` (``at``, ``summary``, ``solutions``) and ``now``. Hard
caps: ``INPUT_TOKENS`` for the whole prompt and at most ``MAX_FINDINGS`` findings, each line one line. Standard library plus ``esoi``."""
import datetime
import hashlib
import re
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from esoi.understanding.solution_consideration.experiments import as_date, commitments, parts

INPUT_TOKENS = 3000          # the whole prompt, instruction included
CHARS_PER_TOKEN = 4          # a safe average for English: a cap in characters is a cap in tokens
INSTRUCTION_TOKENS = 450     # room kept for the instruction that wraps the digest
MAX_FINDINGS = 8
SEVERITIES = ("low", "medium", "high")
DATE = re.compile(r"\b(?:by|before|due|target)\s+(\d{4}-\d{2}-\d{2})", re.I)
WORD = re.compile(r"[a-z]{4,}")


def one(text: Any, limit: int = 140) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= limit else flat[: limit - 3].rstrip() + "..."


def rows_of(structure: Mapping[str, Any], table: str) -> List[Mapping[str, str]]:
    return list((structure.get("tables") or {}).get(table) or ())


def key_of(table: str, row: Mapping[str, str]) -> str:
    for column in (table.rstrip("s") + "_id", "id", "solution_id"):
        if row.get(column):
            return f"{table}:{row[column]}"
    return f"{table}:{one(row.get('name'), 40)}"


def snapshot(structure: Mapping[str, Any]) -> Dict[str, str]:
    """``{table:id: short hash}`` of every record, so the next watch can say what changed."""
    out = {}
    for table in ("solutions", "implementations", "metrics", "experiments", "investigations"):
        for row in rows_of(structure, table):
            out[key_of(table, row)] = hashlib.sha256(repr(sorted(row.items())).encode()).hexdigest()[:8]
    return out


def changes_since(structure: Mapping[str, Any], before: Mapping[str, str]) -> List[Dict[str, str]]:
    """The records added, changed or removed since ``before`` (the last watch's snapshot); none when there was no earlier watch."""
    if not before:
        return []
    now = snapshot(structure)
    out = [{"key": k, "what": "added" if k not in before else "changed"} for k, h in now.items() if before.get(k) != h]
    return out + [{"key": k, "what": "removed"} for k in before if k not in now]


def solution_of(structure: Mapping[str, Any], key: str) -> str:
    table, _, ident = key.partition(":")
    if table == "solutions":
        return ident
    for row in rows_of(structure, table):
        if key_of(table, row) == key:
            return str(row.get("solution_id") or row.get("solution_ids") or "").split(";")[0].strip()
    return ""


def words(row: Mapping[str, str]) -> set:
    return set(WORD.findall(f"{row.get('name', '')} {row.get('purpose', '')}".lower()))


def overlap(a: Mapping[str, str], b: Mapping[str, str]) -> float:
    x, y = words(a), words(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def milestones_of(structure: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    """The milestones in priority order: the ``milestones`` table when given, else the numbered milestones of each solution's text (a date written after by, before, due or target is its target)."""
    given = rows_of(structure, "milestones")
    if given:
        return given
    from esoi.structure.intent_registry.fields import parse_milestones
    out = []
    for row in rows_of(structure, "solutions"):
        for number, found in enumerate(parse_milestones(row.get("milestones"), True), 1):
            target = DATE.search(str(found["text"]))
            out.append({"id": f"{row.get('solution_id')}#{number}", "solution": row.get("solution_id", ""), "text": found["text"], "met": found["met"],
                        "target": target.group(1) if target else "", "blocked_by": ""})
    return out


def last_results(structure: Mapping[str, Any]) -> Dict[str, str]:
    """``{solution id: date of its latest recorded result}``. A result names the component that was measured; it belongs to a solution when the component is the solution's id or is run by one of its
    metrics (``esoi run <component>`` in the metric's ``command``), so a component named differently from its solution still counts."""
    runs_of: Dict[str, set] = {}
    for row in rows_of(structure, "metrics"):
        for component in re.findall(r"esoi run (\w+)", str(row.get("command") or "")):
            runs_of.setdefault(component, set()).update(x.strip() for x in str(row.get("solution_ids") or "").split(";") if x.strip())
    latest: Dict[str, str] = {}
    for r in structure.get("results") or ():
        component, date = str(r.get("component", "")), str(r.get("date", ""))
        for sid in runs_of.get(component, set()) | {component.replace("_", "-")}:
            latest[sid] = max(latest.get(sid, ""), date)
    return latest


def finding(kind: str, subject: str, severity: str, detail: str, step: str, affects: Sequence[str] = ()) -> Dict[str, Any]:
    return {"kind": kind, "subject": subject, "severity": severity, "detail": one(detail), "step": step, "affects": sorted(set(a for a in affects if a))}


def findings_of(structure: Mapping[str, Any], changes: Sequence[Mapping[str, str]]) -> List[Dict[str, Any]]:
    """The findings by rule, most severe first: an experiment past its reevaluation, a solution with no metric or implementations and no selection, a duplicate or missed reuse (R1, R2)
    added by recent work, a milestone past its target that open work depends on, an investigation past refresh that work relies on, and records changed without their metric rerun (R3)."""
    today = as_date(structure.get("now") or "") or datetime.date.today()
    solutions = {str(r.get("solution_id")): r for r in rows_of(structure, "solutions")}
    touched = {s for run in structure.get("runs") or () for s in run.get("solutions") or ()} | {solution_of(structure, c["key"]) for c in changes if c["what"] != "removed"}
    touched.discard("")
    out: List[Dict[str, Any]] = []
    for row in rows_of(structure, "experiments"):
        due = as_date(row.get("reevaluate_time", ""))
        if (row.get("status") or "").strip() == "running" and due and due <= today:
            fixed = set(commitments(row)) | set(commitments(row).values())
            linked = {e.partition(":")[2].strip() for e in parts(row.get("links", ""))} | {s for s in solutions if s.lower() in fixed}
            piled = sorted(linked & touched)
            out.append(finding("experiment_overdue", f"experiments:{row.get('experiment_id')}", "high" if piled else "medium",
                               f"reevaluation was due {row.get('reevaluate_time')}" + (f"; new work touches what it holds fixed: {', '.join(piled)}" if piled else ""), "reevaluate", piled))
    impls: Dict[str, int] = {}
    for row in rows_of(structure, "implementations"):
        impls[str(row.get("solution_id"))] = impls.get(str(row.get("solution_id")), 0) + 1
    for sid, row in solutions.items():
        count = impls.get(sid, 0)
        if not (row.get("authoritative_metric_id") or row.get("metric_ids") or "").strip():
            out.append(finding("no_metric", f"solutions:{sid}", "high" if count >= 3 or sid in touched else "medium",
                               f"has {count} implementation(s) and no metric" + ("; work is piling on it" if sid in touched else ""), "add-metric", [sid]))
        elif count >= 2 and not (row.get("selected") or "").strip() and sid in touched:
            out.append(finding("no_selection", f"solutions:{sid}", "medium", f"has {count} implementations, none selected, and work is going on", "select-implementation", [sid]))
    for change in changes:
        if change["what"] == "added" and change["key"].startswith("solutions:"):
            sid = change["key"].partition(":")[2]
            rivals = sorted(((overlap(solutions[sid], r), o) for o, r in solutions.items() if o != sid and sid in solutions), reverse=True)
            if rivals and rivals[0][0] >= 0.5:
                out.append(finding("duplicate_solution", change["key"], "high", f"added by recent work and overlaps {rivals[0][1]} ({rivals[0][0]:.2f} of its words)", "merge", [sid, rivals[0][1]]))
            elif rivals and rivals[0][0] >= 0.3:
                out.append(finding("missed_reuse", change["key"], "medium", f"added by recent work and partly overlaps {rivals[0][1]}", "merge", [sid, rivals[0][1]]))
    open_ms = [m for m in milestones_of(structure) if not m.get("met")]
    for m in open_ms:
        target = as_date(m.get("target", ""))
        waiting = [o["id"] for o in open_ms if str(m["id"]) in parts(o.get("blocked_by", ""))]
        if target and target < today:
            out.append(finding("milestone_overdue", f"milestones:{m['id']}", "high" if waiting else "medium", f"target {m['target']} has passed" + (f"; {', '.join(waiting)} wait on it" if waiting else ""), "restrategize", [m.get("solution", "")]))
    planned = {m.get("solution") for m in open_ms[:5]} | touched
    for row in rows_of(structure, "investigations"):
        due = as_date(row.get("refresh_on", ""))
        linked = {e.partition(":")[2].strip() for e in parts(row.get("links", "")) if e.startswith("solution:")}
        if (row.get("status") or "open").strip() == "open" and due and due <= today and linked & planned:
            out.append(finding("investigation_stale", f"investigations:{row.get('investigation_id')}", "medium", f"refresh was due {row.get('refresh_on')} and planned work relies on it", "investigate", sorted(linked & planned)))
    latest = last_results(structure)
    since = str(structure.get("changed_at") or "")
    for change in changes:
        sid = solution_of(structure, change["key"])
        if change["what"] == "changed" and sid and sid in latest and since and latest[sid] < since:
            dependents = [o for o, r in solutions.items() if sid in (r.get("delegates_to") or "").split(";")]
            out.append(finding("changed_without_rerun", change["key"], "medium", f"changed since its metric last ran ({latest[sid]})" + (f"; {len(dependents)} solution(s) delegate to it" if dependents else ""), "rerun-metric", [sid] + dependents[:3]))
    started = min((str(r.get("at") or "")[:10] for r in structure.get("runs") or () if r.get("at")), default="")
    for sid in sorted(touched & set(solutions)):
        count = impls.get(sid, 0)
        if sid in latest and started and latest[sid] < started and count:
            out.append(finding("result_older_than_recent_work", f"solutions:{sid}", "medium", f"recent work touched it after its metric last ran ({latest[sid]})", "rerun-metric", [sid]))
        elif sid not in latest and count >= 2 and (solutions[sid].get("authoritative_metric_id") or solutions[sid].get("metric_ids") or "").strip():
            out.append(finding("touched_without_result", f"solutions:{sid}", "low", f"recent work touched it, it has {count} implementations and no recorded result", "rerun-metric", [sid]))
    rank = {s: i for i, s in enumerate(SEVERITIES)}
    return sorted(out, key=lambda f: (-rank[f["severity"]], not (set(f["affects"]) & touched), f["kind"], f["subject"]))     # most severe first, then what recent work touched


def gaps_of(structure: Mapping[str, Any]) -> str:
    """One line of what the records lack as a whole (counts by rule, so the model sees the size of the structure without its rows)."""
    solutions = rows_of(structure, "solutions")
    impls: Dict[str, int] = {}
    for row in rows_of(structure, "implementations"):
        impls[str(row.get("solution_id"))] = impls.get(str(row.get("solution_id")), 0) + 1
    measured = set(last_results(structure))
    no_metric = sum(1 for r in solutions if not (r.get("authoritative_metric_id") or r.get("metric_ids") or "").strip())
    no_select = sum(1 for r in solutions if impls.get(str(r.get("solution_id")), 0) >= 2 and not (r.get("selected") or "").strip())
    no_result = sum(1 for r in solutions if impls.get(str(r.get("solution_id")), 0) and str(r.get("solution_id")) not in measured)
    return (f"{len(solutions)} solutions, {sum(impls.values())} implementations, {len(rows_of(structure, 'metrics'))} metrics; "
            f"{no_metric} solutions without a metric, {no_select} with several implementations and none selected, {no_result} with implementations and no recorded result")


def digest_of(structure: Mapping[str, Any], before: Mapping[str, str]) -> Tuple[str, str, List[Dict[str, Any]], List[Dict[str, str]]]:
    """``(text, hash, findings, changes)``. The text fits ``INPUT_TOKENS`` less the instruction; whole lowest-severity findings, then changes and runs, are dropped to fit. The hash is of the text."""
    changes = changes_since(structure, before)
    found = findings_of(structure, changes)[:MAX_FINDINGS]
    budget = (INPUT_TOKENS - INSTRUCTION_TOKENS) * CHARS_PER_TOKEN
    ms = [m for m in milestones_of(structure) if not m.get("met")][:5]
    exps = [r for r in rows_of(structure, "experiments") if (r.get("status") or "").strip() in ("running", "reevaluating")][:3]
    plan = [f"milestone {m['id']}" + (f" (target {m['target']})" if m.get("target") else "") + f": {one(m.get('text'), 90)}" for m in ms]
    plan += [f"experiment {r.get('experiment_id')} reevaluate {r.get('reevaluate_time') or r.get('reevaluate_condition')}; holds fixed: {one(r.get('held_fixed'), 90)}" for r in exps]
    runs = [f"{one(r.get('at'), 20)} {one(r.get('summary'), 100)} (solutions: {', '.join(r.get('solutions') or ())})" for r in (structure.get("runs") or ())[-6:]]
    chg = [f"{c['what']} {c['key']}" for c in changes[:8]] + ([f"... and {len(changes) - 8} more"] if len(changes) > 8 else [])
    while True:
        text = "\n".join(["INTENT: " + one(structure.get("intent"), 80), "RECORDS: " + gaps_of(structure), "CHANGED SINCE LAST WATCH:"] + [" - " + c for c in chg or ["nothing recorded"]]
                         + ["RECENT RUNS:"] + [" - " + r for r in runs or ["none"]] + ["PLANNED NEXT:"] + [" - " + p for p in plan or ["none"]]
                         + ["FINDINGS BY RULE (subject | severity | step | detail):"] + [f" - {f['subject']} | {f['severity']} | {f['step']} | {f['detail']}" for f in found or []])
        if len(text) <= budget or not (found or chg or runs):
            break
        if found:
            found = found[:-1]
        elif chg:
            chg = chg[:-1]
        else:
            runs = runs[:-1]
    return text[:budget], hashlib.sha256(text.encode()).hexdigest()[:16], found, changes
