"""The Trail: what the AI read, as a live line, a one-line summary and the groups behind it.

Pure functions over work trace events (the wire dict of ``hubofhubs.ports.trace``, latest event per ``step_id``). The rules and the
words match the Quest app's ``src/utils/workTrace.ts`` (``liveText``, ``summaryText``, ``expandedGroups``) and its English pack, and
``tests/test_terminal_drift.py`` fails when they stop matching. Nothing here reads a model's wording: only typed fields.

Rules kept (each is a test): the latest event for a step replaces the earlier one; a bad event is dropped, never raised; counts are
honest (a kind with nothing read is omitted); a page a search only listed is never called read; a shared thread names only records
marked ``visible_to_all``; the live line is the newest page actually opened or nothing.
"""
from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Mapping, Optional

from .strings import say

MAX_ITEMS_PER_STEP = 20
MAX_LABEL_CHARS = 80
KIND_ORDER = ("records", "sources", "papers", "check", "notice")
KNOWN_KINDS = KIND_ORDER + ("action",)

Event = Dict[str, Any]


def clean_text(value: Any, limit: int = MAX_LABEL_CHARS) -> str:
    if not isinstance(value, str):
        return ""
    flat = re.sub(r"[\r\n\t]+", " ", value).strip()
    return flat[: limit - 1].rstrip() + "…" if len(flat) > limit else flat


def clean_count(value: Any) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(math.floor(value)) if math.isfinite(value) and value >= 0 else None


def clean_item(raw: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(raw, Mapping):
        return None
    label = clean_text(raw.get("label")) or clean_text(raw.get("ref"))
    if not label:
        return None
    out: Dict[str, Any] = {"ref": clean_text(raw.get("ref"), 200) or label, "label": label}
    for key, limit in (("sub", MAX_LABEL_CHARS), ("kind", 24)):
        text = clean_text(raw.get(key), limit)
        if text:
            out[key] = text
    if raw.get("visible_to_all") is True:
        out["visible_to_all"] = True
    return out


def sanitize_event(raw: Any) -> Optional[Event]:
    """One wire event in the shape the rules below read, or None for anything unusable."""
    if not isinstance(raw, Mapping):
        return None
    step_id = raw.get("step_id")
    state = raw.get("state")
    if not isinstance(step_id, str) or not step_id or state not in ("running", "done", "failed"):
        return None
    counts = raw.get("counts") if isinstance(raw.get("counts"), Mapping) else {}
    items = []
    for entry in raw.get("items") if isinstance(raw.get("items"), list) else []:
        item = clean_item(entry)
        if item:
            items.append(item)
        if len(items) >= MAX_ITEMS_PER_STEP:
            break
    kind = raw.get("kind")
    return {
        "step_id": step_id, "state": state,
        "kind": kind if isinstance(kind, str) and kind else "unknown",
        "label_key": raw.get("label_key") if isinstance(raw.get("label_key"), str) else "",
        "counts": {k: clean_count(counts.get(k)) for k in ("found", "read", "checked", "failed", "total")},
        "items": items, "affects_user": raw.get("affects_user") is True,
    }


def apply_event(steps: List[Event], raw: Any) -> List[Event]:
    """The steps after one more event: the latest event per ``step_id`` replaces the earlier one, keeping its place."""
    event = sanitize_event(raw)
    if event is None:
        return steps
    for i, step in enumerate(steps):
        if step["step_id"] == event["step_id"]:
            return steps[:i] + [event] + steps[i + 1:]
    return steps + [event]


# -- titles, domains, pages -------------------------------------------------------------------------------------------------------

def looks_like_file_path(text: str) -> bool:
    return bool(re.search(r"[\\/]", text) or re.search(r"\.[a-z0-9]{1,5}$", text, re.I))


def record_title_of(item: Mapping[str, Any]) -> str:
    """A record is shown by a human title only; card text, a conversation topic, a path or a cut-off line is not a title."""
    label = str(item.get("label") or "").strip()
    if not label:
        return ""
    if re.match(r"^(the )?conversation('s)?\b", label, re.I):
        return ""
    if re.match(r"^(conversation turn|past task|previous task|guidance|documentation)\b", label, re.I):
        return ""
    if looks_like_file_path(label) or label.endswith("…") or label.endswith("..."):
        return ""
    if len(label) > 70:
        return ""
    if re.search(r":\s+\S", label) and len(label.split()) > 8:
        return ""
    return label


def titled_records(items: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    return [i for i in items if record_title_of(i)]


def domain_only(ref: str) -> str:
    """Domain only: any scheme, path, query or credentials a producer left in a ref are cut away."""
    stripped = re.sub(r"^[a-z][a-z0-9+.-]*://", "", str(ref).strip(), flags=re.I)
    stripped = re.sub(r"^[^@/]*@", "", stripped)
    return re.sub(r"^www\.", "", re.split(r"[/?#]", stripped)[0], flags=re.I)


def page_title_of(item: Mapping[str, Any]) -> str:
    """A page's title, or empty when the label only restates the domain."""
    domain = domain_only(item.get("ref") or "").lower()
    label = str(item.get("label") or "").strip()
    flat = re.sub(r"^www\.", "", label.lower())
    bare_host = not re.search(r"\s", label) and re.match(r"^[a-z0-9-]+(\.[a-z0-9-]+)+$", flat, re.I) is not None
    if not label or flat == domain or domain in flat or bare_host:
        return ""
    return label


def read_items(items: List[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    """The pages actually opened: an item marked ``found`` was only listed by a search."""
    return [i for i in items if i.get("kind") != "found"]


# -- totals and clauses -----------------------------------------------------------------------------------------------------------

def redact_for_shared(steps: List[Event]) -> List[Event]:
    """Shared thread: a record keeps its title only when marked visible to every participant."""
    return [dict(s, items=[i for i in s["items"] if i.get("visible_to_all") is True]) if s["kind"] == "records" else s for s in steps]


def totals_by_kind(steps: List[Event]) -> List[Dict[str, Any]]:
    by_kind: Dict[str, Dict[str, Any]] = {}
    for step in steps:
        kind = step["kind"]
        if kind not in KNOWN_KINDS or kind == "action":
            continue
        cur = by_kind.setdefault(kind, {"kind": kind, "read": 0, "found": 0, "failed": 0, "items": [], "running": False})
        read = step["counts"]["read"] if step["counts"]["read"] is not None else (0 if kind == "papers" else len(step["items"]))
        found = step["counts"]["found"] if step["counts"]["found"] is not None else read
        cur["read"] += read
        cur["found"] += max(found, read)
        cur["failed"] += step["counts"]["failed"] or 0
        cur["items"] = cur["items"] + step["items"]
        cur["running"] = cur["running"] or step["state"] == "running"
    return [by_kind[k] for k in KIND_ORDER if k in by_kind]


def summary_clauses(steps: List[Event]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for t in totals_by_kind(steps):
        if t["kind"] == "records" and t["read"] > 0:
            out.append({"key": "records", "count": t["read"]})
        elif t["kind"] == "sources":
            if t["read"] > 0:
                out.append({"key": "sources", "count": t["read"]})
            elif t["found"] > 0:
                out.append({"key": "sourcesSearched", "count": t["found"]})
        elif t["kind"] == "papers":
            if t["read"] > 0:
                out.append({"key": "papersRead", "count": t["read"]})
            elif t["found"] > 0:
                out.append({"key": "papersFound", "count": t["found"]})
    return out[:3]


def visible_titles(total: Mapping[str, Any], shared: bool) -> List[Mapping[str, Any]]:
    items = [i for i in total["items"] if i.get("visible_to_all") is True] if shared else total["items"]
    return titled_records(items)


def summary_names_all_records(total: Mapping[str, Any], shared: bool) -> bool:
    titled = len(visible_titles(total, shared))
    return titled > 0 and titled == total["read"] and total["read"] <= 2


def notice_steps(steps: List[Event]) -> List[Event]:
    return [s for s in steps if s["kind"] == "notice" and s["affects_user"]]


def removed_link_domains(steps: List[Event]) -> List[str]:
    out = [domain_only(i["ref"]) for s in steps if s["kind"] == "check" for i in s["items"]]
    return [d for d in out if d]


def removed_link_count(steps: List[Event]) -> int:
    return sum(s["counts"]["failed"] or 0 for s in steps if s["kind"] == "check")


def has_expandable_detail(steps: List[Event], shared: bool = False) -> bool:
    """True when opening the line shows something the line does not already say: derived from ``expanded_groups``."""
    return len(expanded_groups(steps, shared)) > 0


def has_visible_work(steps: List[Event], shared: bool = False) -> bool:
    # A records count speaks for every viewer: counts-only, title-free.
    if summary_clauses(steps):
        return True
    return bool(notice_steps(steps)) or removed_link_count(steps) > 0


# -- the words ----------------------------------------------------------------------------------------------------------------------

NS = "workTrace."


def _items_of(steps: List[Event], kind: str) -> List[Mapping[str, Any]]:
    return next((k["items"] for k in totals_by_kind(steps) if k["kind"] == kind), [])


def _records_sentence(steps: List[Event], shared: bool, ov) -> str:
    tot = next((k for k in totals_by_kind(steps) if k["kind"] == "records"), None)
    if not tot or tot["read"] <= 0:
        return ""
    titles = [record_title_of(i) for i in visible_titles(tot, shared)]
    if shared:
        if not titles:
            return say(NS + "summary.records", ov, count=tot["read"])
        if tot["read"] <= 2 and len(titles) == tot["read"]:
            return say(NS + "summary.recordsTeamOne", ov, a=titles[0]) if len(titles) == 1 else say(NS + "summary.recordsTeamTwo", ov, a=titles[0], b=titles[1])
        return say(NS + "summary.recordsTeamMore", ov, a=titles[0], count=max(1, tot["read"] - 1))
    if not titles:
        return say(NS + "summary.records", ov, count=tot["read"])
    if tot["read"] <= 2 and len(titles) == tot["read"]:
        return say(NS + "summary.recordsOne", ov, a=titles[0]) if len(titles) == 1 else say(NS + "summary.recordsTwo", ov, a=titles[0], b=titles[1])
    return say(NS + "summary.recordsMore", ov, a=titles[0], count=max(1, tot["read"] - 1))


def _site_names(steps: List[Event]) -> List[str]:
    seen: List[str] = []
    for item in read_items(_items_of(steps, "sources")):
        d = domain_only(item["ref"])
        if d and d not in seen:
            seen.append(d)
    return seen


def _paper_names(steps: List[Event]) -> List[str]:
    items = _items_of(steps, "papers")
    return [i["sub"] for i in items] if items and all(i.get("sub") for i in items) else []


def said_names(names: List[str], total: int) -> List[str]:
    """The names the summary sentence actually says, in order: empty when it is a bare count."""
    if not names or len(names) > total:
        return []
    if total == 1 or (total == 2 and len(names) == 2):
        return names[:1] if len(names) == 1 else names[:2]
    return names[:1]


def _named(base: str, names: List[str], total: int, ov) -> str:
    said = said_names(names, total)
    if not said:
        return say(f"{NS}summary.{base}", ov, count=total)
    if total == 1 or (total == 2 and len(names) == 2):
        return say(f"{NS}summary.{base}One", ov, a=said[0]) if len(said) == 1 else say(f"{NS}summary.{base}Two", ov, a=said[0], b=said[1])
    return say(f"{NS}summary.{base}More", ov, a=said[0], count=max(1, total - 1))


def _removed_links(removed: int, domains: List[str], ov) -> str:
    if len(domains) != removed:
        return say(NS + "removedLinks", ov, count=removed)
    unique = [d for i, d in enumerate(domains) if domains.index(d) == i]
    if removed == 1:
        return say(NS + "removedLinksOne", ov, a=unique[0])
    if len(unique) == 1:
        return say(NS + "removedLinksSame", ov, a=unique[0], count=removed)
    if removed == 2:
        return say(NS + "removedLinksTwo", ov, a=unique[0], b=unique[1])
    return say(NS + "removedLinksMore", ov, a=unique[0], count=removed - domains.count(unique[0]))


def notice_text(step: Event, ov=None) -> str:
    key = step["label_key"]
    return say(key, ov) if key and _has(key) else say(NS + "notice.generic", ov)


def _has(key: str) -> bool:
    from .strings import has
    return has(key)


def summary_sentences(steps: List[Event], shared: bool = False, overrides=None) -> List[str]:
    ov = overrides
    out: List[str] = []
    records = _records_sentence(steps, shared, ov)
    if records:
        out.append(records)
    clauses = summary_clauses(steps)
    find = lambda key: next((c for c in clauses if c["key"] == key), None)  # noqa: E731
    sites, papers, searched, found = find("sources"), find("papersRead"), find("sourcesSearched"), find("papersFound")
    if sites:
        out.append(_named("sites", _site_names(steps), sites["count"], ov))
    if papers:
        out.append(_named("papers", _paper_names(steps), papers["count"], ov))
    if searched:
        out.append(say(NS + "summarySearched", ov, count=searched["count"]))
    if found:
        out.append(say(NS + "summaryFoundPapers", ov, count=found["count"]))
    removed = removed_link_count(steps)
    if removed > 0:
        out.append(_removed_links(removed, removed_link_domains(steps), ov))
    out.extend(notice_text(n, ov) for n in notice_steps(steps))
    return out


def summary_text(steps: List[Event], shared: bool = False, overrides=None) -> str:
    """The settled one-line summary, or empty when there is nothing to say."""
    return ". ".join(summary_sentences(steps, shared, overrides))


def live_line_speaks(steps: List[Event]) -> bool:
    """True when the live line has words to show: some step is running (not an action) and a page has been opened or records are being looked through."""
    return any(x["state"] == "running" and x["kind"] != "action" for x in steps) and live_text(steps) is not None


def live_text(steps: List[Event], overrides=None) -> Optional[str]:
    """The ONE live line: the newest page actually opened ("Opened blog.rust-lang.org"), or None. A count alone is not a line."""
    for step in reversed(steps):
        if step["state"] != "running" or step["kind"] != "sources":
            continue
        opened = read_items(step["items"]) if (step["counts"]["read"] or 0) > 0 else []
        if opened:
            return say(NS + "newestSite", overrides, value=domain_only(opened[-1]["ref"]))
    # Records being looked through: title-free and number-free, for every viewer.
    if any(step["state"] == "running" and step["kind"] == "records" for step in steps):
        return say(NS + "lookingRecords", overrides)
    return None


def expanded_groups(steps: List[Event], shared: bool = False, overrides=None) -> List[Dict[str, Any]]:
    """The groups behind the summary: only rows the summary does not already say. Each is ``{id, title, rows, notes}``."""
    ov = overrides
    groups: List[Dict[str, Any]] = []
    for tot in totals_by_kind(steps):
        if tot["kind"] == "records" and tot["read"] > 0 and not summary_names_all_records(tot, shared):
            # The line names the first record; the rows are the records it did not name.
            titled = visible_titles(tot, shared)[1:]
            if not titled:
                continue
            rows = []
            for i in titled:
                kind_word = say(f"{NS}recordKind.{i['kind']}", ov) if i.get("kind") and _has(f"{NS}recordKind.{i['kind']}") else ""
                rows.append(f"{record_title_of(i)}  {kind_word}".rstrip() if kind_word else record_title_of(i))
            untitled = tot["read"] - len(titled) - 1
            notes = [say(NS + "recordsUntitled", ov, count=untitled)] if (not shared and tot["read"] > len(titled) + 1) else []
            groups.append({"id": "records", "title": say(NS + ("group.recordsShared" if shared else "group.records"), ov), "rows": rows, "notes": notes})
        elif tot["kind"] == "sources" and tot["read"] > 0:
            # A page the line names shows only its title; a page the line did not name shows its domain and title.
            said = said_names(_site_names(steps), tot["read"])
            rows = []
            for i in read_items(tot["items"]):
                domain, title = domain_only(i["ref"]), page_title_of(i)
                row = title if domain in said else domain + (f"  {title}" if title else "")
                if row:
                    rows.append(row)
            if not rows:
                continue
            notes = [say(NS + "couldNotOpen", ov, count=tot["failed"])] if tot["failed"] > 0 else []
            groups.append({"id": "sources", "title": say(NS + "group.sources", ov), "rows": rows, "notes": notes})
        elif tot["kind"] == "papers" and tot["items"]:
            # A paper the line names shows only its title; one the line did not name shows both.
            clause = next((c for c in summary_clauses(steps) if c["key"] == "papersRead"), None)
            said = len(said_names(_paper_names(steps), clause["count"])) if clause else 0
            rows = [f"{i['label']} ({i['sub']})" if (i.get("sub") and idx >= said) else i["label"] for idx, i in enumerate(tot["items"])]
            groups.append({"id": "papers", "title": say(NS + "group.papers", ov), "rows": rows, "notes": []})
    return groups
