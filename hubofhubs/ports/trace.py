"""The work trace: a typed, reader-safe account of the work a run did, sent while it happens.

A solution (a web search, a paper lookup, a records read, a link check) describes one unit of work as a
``WorkTraceEvent`` and re-sends it as it changes; the latest event for a ``step_id`` replaces earlier ones, so a replayed
or repeated update is harmless. The event is built from STRUCTURAL results (counts, domains, titles), never from model
wording, and only through the allowlist below: ``project`` copies named fields and nothing else, so a field added to a
raw result later cannot leak by accident.

What never leaves (enforced here, in code, not by a prompt): the query text, page or paper content, snippets, model
reasoning or narration, tool arguments, file paths, full URLs (a domain only, no path, query string or token), and a
title the viewer may not see (``viewer_may_see_titles=False`` keeps ``records`` and ``action`` as counts only). Labels are trimmed to
``MAX_LABEL`` characters, lose newlines and em dashes, and an item list is capped at ``MAX_ITEMS``.

``WorkTrace`` is the small helper any solution can use to emit: it projects, remembers the latest event per step,
coalesces rapid running updates and always sends the final ``done`` or ``failed``. It knows no consumer. The wire shape
is documented in ``docs/reference/work-trace-event.schema.json``.
"""
from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional
from urllib.parse import urlsplit

from .deep import ProgressEvent
from .events import EVENT_WORK_TRACE

SCHEMA_VERSION = 1
#: The presentation families a consumer has a treatment for. An unknown (but well-formed) kind is kept, and a consumer
#: renders it as one generic row.
KINDS = ("sources", "papers", "records", "check", "action", "notice")
STATES = ("running", "done", "failed")
COUNT_KEYS = ("found", "read", "checked", "failed", "total")
ITEM_KEYS = ("ref", "label", "sub", "kind", "visible_to_all")
#: Kinds whose items are titles of the viewer's own things: kept as counts only for a viewer who may not see them.
PRIVATE_KINDS = ("records", "action")
MAX_ITEMS = 20
MAX_LABEL = 80
#: Running updates one step may send before only its final state goes out (a bound on stream size).
MAX_RUNNING_UPDATES = 30
#: Seconds between running updates of one step (about four a second).
MIN_INTERVAL = 0.25

IDENT = re.compile(r"^[A-Za-z0-9_.:\-]{1,64}$")
LABEL_KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_.\-]{0,79}$")
SLUG = re.compile(r"^[a-z][a-z0-9_]{0,23}$")
URL_IN_TEXT = re.compile(r"(?:https?://|www\.)[^\s<>()\[\]\"'`]+", re.IGNORECASE)
PATH_START = re.compile(r"^(?:/|~/|\./|\.\./|[A-Za-z]:[\\/])")


class WorkTraceError(ValueError):
    """A raw event that cannot be projected (a bad state, a missing id, a label key that is display text)."""


@dataclass
class WorkTraceEvent:
    """One unit of work, as the reader's screen may see it. Build one with ``project``, not by hand."""
    trace_id: str
    step_id: str
    solution_id: str
    kind: str
    label_key: str
    state: str
    started_at: str
    counts: Dict[str, int] = field(default_factory=dict)
    items: List[Dict[str, str]] = field(default_factory=list)
    affects_user: bool = False
    ended_at: Optional[str] = None
    v: int = SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "v": self.v, "trace_id": self.trace_id, "step_id": self.step_id, "solution_id": self.solution_id,
            "kind": self.kind, "label_key": self.label_key, "state": self.state,
            "counts": dict(self.counts), "items": [dict(i) for i in self.items],
            "affects_user": bool(self.affects_user), "started_at": self.started_at,
        }
        if self.ended_at:
            out["ended_at"] = self.ended_at
        return out


def utc_now() -> str:
    """The current time as ISO-8601 UTC with a trailing Z."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def iso_utc(value: Any, default: Optional[str] = None) -> Optional[str]:
    """A datetime or ISO string as ISO-8601 UTC with a Z; the default when it is neither."""
    if isinstance(value, datetime):
        moment = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    if isinstance(value, str) and value.strip():
        try:
            moment = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return default
        return iso_utc(moment)
    return default


def domain_of(url: Any) -> str:
    """The host of an address, lowercased, without ``www.``, port, credentials, path, query or fragment. Empty when none."""
    text = str(url or "").strip()
    if not text:
        return ""
    probe = text if "//" in text else "//" + text
    try:
        host = urlsplit(probe).hostname or ""
    except ValueError:
        return ""
    host = host.lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    return host if re.fullmatch(r"[a-z0-9.\-]+", host) and "." in host else ""


def clean_text(value: Any, limit: int = MAX_LABEL) -> str:
    """Text fit for a label: a URL inside it becomes its domain, newlines and em dashes go, and it is trimmed to ``limit``."""
    text = str(value or "")
    text = URL_IN_TEXT.sub(lambda m: domain_of(m.group(0)), text)
    text = re.sub(r"\s*—\s*", ", ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > limit:
        text = text[: limit - 3].rstrip() + "..."
    return text


def project_item(raw: Any, kind: str) -> Optional[Dict[str, str]]:
    """One item built from named fields only, or None when nothing safe is left.

    A ``sources`` item is its domain (from ``ref`` or ``url``), a title and whether the page was ``read`` or only ``found``; every other kind copies ``ref``, ``label``,
    ``sub`` and ``kind`` as clean text. An item whose ref or label is a filesystem path is dropped.
    """
    if not isinstance(raw, Mapping):
        return None
    if kind == "sources":
        ref = domain_of(raw.get("ref") or raw.get("url"))
        if not ref:
            return None
        label = clean_text(raw.get("label")) or ref
        out = {"ref": ref, "label": label}
        # ``read`` (the page was opened) or ``found`` (a search only listed it): a screen must not show a listed site as read.
        if str(raw.get("kind") or "") in ("read", "found"):
            out["kind"] = str(raw["kind"])
        return out
    ref = clean_text(raw.get("ref"))
    label = clean_text(raw.get("label"))
    for text in (str(raw.get("ref") or "").strip(), str(raw.get("label") or "").strip()):
        if PATH_START.match(text):
            return None
    if not label:
        return None
    out = {"ref": ref or label, "label": label}
    sub = clean_text(raw.get("sub"))
    if sub:
        out["sub"] = sub
    item_kind = str(raw.get("kind") or "")
    if SLUG.match(item_kind):
        out["kind"] = item_kind
    # Set by the consumer that knows who is in the thread, never by an emitter: the item may be shown to EVERY participant.
    if raw.get("visible_to_all") is True:
        out["visible_to_all"] = True
    return out


def project_counts(raw: Any) -> Dict[str, int]:
    """The allowed count keys with non-negative whole numbers; anything else is dropped."""
    out: Dict[str, int] = {}
    if isinstance(raw, Mapping):
        for key in COUNT_KEYS:
            value = raw.get(key)
            if isinstance(value, bool) or value is None:
                continue
            try:
                number = int(value)
            except (TypeError, ValueError):
                continue
            if number >= 0:
                out[key] = number
    return out


def project(raw: Mapping[str, Any], *, trace_id: Optional[str] = None, viewer_may_see_titles: bool = True) -> WorkTraceEvent:
    """Build the reader-safe event from a raw description, copying only the allowlisted fields.

    ``viewer_may_see_titles=False`` (a shared thread, or anyone but the record's owner) keeps ``records`` and ``action`` as counts only,
    except for items the consumer marked ``visible_to_all`` (visible to every participant of the thread): those keep their title. The
    other items are dropped and ``counts.found`` records how many there were. Raises ``WorkTraceError`` for a state outside
    ``STATES``, a missing or malformed id, or a ``label_key`` that is not a key.
    """
    if not isinstance(raw, Mapping):
        raise WorkTraceError("a work trace event is a mapping")
    state = str(raw.get("state") or "")
    if state not in STATES:
        raise WorkTraceError(f"state must be one of {STATES}, not {state!r}")
    ids: Dict[str, str] = {}
    for name, value in (("trace_id", trace_id or raw.get("trace_id")), ("step_id", raw.get("step_id")),
                        ("solution_id", raw.get("solution_id"))):
        if not IDENT.match(str(value or "")):
            raise WorkTraceError(f"{name} must be a short identifier")
        ids[name] = str(value)
    label_key = str(raw.get("label_key") or "")
    if not LABEL_KEY.match(label_key):
        raise WorkTraceError("label_key must be an i18n key, never display text")
    kind = str(raw.get("kind") or "")
    if not SLUG.match(kind):
        raise WorkTraceError("kind must be a lowercase slug")
    counts = project_counts(raw.get("counts"))
    raw_items = raw.get("items") if isinstance(raw.get("items"), (list, tuple)) else []
    items: List[Dict[str, str]] = []
    for entry in raw_items:
        if kind in PRIVATE_KINDS and not viewer_may_see_titles:
            # Only an item the consumer marked visible to every participant keeps its title; the rest are counted, never named.
            if not (isinstance(entry, Mapping) and entry.get("visible_to_all") is True):
                continue
        item = project_item(entry, kind)
        if item is not None:
            items.append(item)
        if len(items) >= MAX_ITEMS:
            break
    if kind in PRIVATE_KINDS and not viewer_may_see_titles:
        counts.setdefault("found", len(raw_items))
    started = iso_utc(raw.get("started_at"), utc_now()) or utc_now()
    ended = None
    if state != "running":
        ended = iso_utc(raw.get("ended_at"), utc_now())
    return WorkTraceEvent(trace_id=ids["trace_id"], step_id=ids["step_id"], solution_id=ids["solution_id"], kind=kind,
                          label_key=label_key, state=state, started_at=started, counts=counts, items=items,
                          affects_user=bool(raw.get("affects_user")), ended_at=ended)


def project_or_none(raw: Any, **kwargs: Any) -> Optional[WorkTraceEvent]:
    """``project``, with a malformed raw event giving None instead of raising (a trace never breaks a run)."""
    try:
        return project(raw, **kwargs)
    except (WorkTraceError, TypeError, ValueError):
        return None


def validate(event: Mapping[str, Any]) -> List[str]:
    """The problems with an already projected event dict, empty when it matches the contract."""
    problems: List[str] = []
    allowed = {"v", "trace_id", "step_id", "solution_id", "kind", "label_key", "state", "counts", "items",
               "affects_user", "started_at", "ended_at"}
    for key in event:
        if key not in allowed:
            problems.append(f"unknown field {key!r}")
    if event.get("v") != SCHEMA_VERSION:
        problems.append("v must be 1")
    if event.get("state") not in STATES:
        problems.append("state must be running, done or failed")
    for key in ("trace_id", "step_id", "solution_id"):
        if not IDENT.match(str(event.get(key) or "")):
            problems.append(f"{key} must be a short identifier")
    if not LABEL_KEY.match(str(event.get("label_key") or "")):
        problems.append("label_key must be an i18n key")
    if not SLUG.match(str(event.get("kind") or "")):
        problems.append("kind must be a lowercase slug")
    if not isinstance(event.get("affects_user"), bool):
        problems.append("affects_user must be a boolean")
    if not iso_utc(event.get("started_at")):
        problems.append("started_at must be ISO-8601")
    if event.get("state") in ("done", "failed") and not iso_utc(event.get("ended_at")):
        problems.append("ended_at is required when the step is done or failed")
    for key, value in (event.get("counts") or {}).items():
        if key not in COUNT_KEYS or isinstance(value, bool) or not isinstance(value, int) or value < 0:
            problems.append(f"counts.{key} is not an allowed non-negative whole number")
    items = event.get("items") or []
    if len(items) > MAX_ITEMS:
        problems.append(f"items has more than {MAX_ITEMS} entries")
    for item in items:
        if not isinstance(item, Mapping) or set(item) - set(ITEM_KEYS):
            problems.append("an item has fields outside ref, label, sub, kind, visible_to_all")
            continue
        for key, value in item.items():
            text = str(value)
            if len(text) > MAX_LABEL or "\n" in text or "—" in text:
                problems.append(f"item {key} is too long or has a newline or em dash")
            if URL_IN_TEXT.search(text):
                problems.append(f"item {key} holds a URL")
    return problems


def progress_event(event: WorkTraceEvent) -> ProgressEvent:
    """The run-progress event carrying a trace event. ``text`` changes with state and counts, so a consumer that dedupes
    progress by type, time and text still sees every update. It is a key for that, not wording for a reader."""
    digest = ",".join(f"{k}={v}" for k, v in sorted(event.counts.items()))
    return ProgressEvent(type=EVENT_WORK_TRACE, text=f"{event.step_id} {event.state} {digest}".strip(),
                         data=event.to_dict())


class WorkTrace:
    """Emit work trace events for one run (``trace_id``): project, coalesce and keep the latest event per step.

    ``emit`` receives a ``ProgressEvent`` of type ``EVENT_WORK_TRACE`` (hand it the run's emitter or sink). A failing
    ``emit`` never reaches the caller. Rapid running updates of one step are coalesced to one per ``min_interval``
    seconds and capped at ``max_running_updates``; the final ``done`` or ``failed`` always goes out. Safe to call from
    several threads.
    """

    def __init__(self, emit: Callable[[ProgressEvent], None], *, trace_id: str, viewer_may_see_titles: bool = True,
                 min_interval: float = MIN_INTERVAL, max_running_updates: int = MAX_RUNNING_UPDATES,
                 clock: Callable[[], float] = time.monotonic, now: Callable[[], str] = utc_now):
        self.trace_id = trace_id
        self.viewer_may_see_titles = viewer_may_see_titles
        self.emit = emit
        self.min_interval = min_interval
        self.max_running_updates = max_running_updates
        self.clock = clock
        self.now = now
        self.lock = threading.Lock()
        self.latest: Dict[str, WorkTraceEvent] = {}
        self.started: Dict[str, str] = {}
        self.last_sent: Dict[str, float] = {}
        self.running_sent: Dict[str, int] = {}

    def update(self, step_id: str, *, solution_id: str, kind: str, label_key: str, state: str = "running",
               counts: Optional[Mapping[str, Any]] = None, items: Optional[List[Mapping[str, Any]]] = None,
               affects_user: bool = False) -> Optional[WorkTraceEvent]:
        """Record this step's newest state and send it (unless coalesced). Returns the projected event, or None when the
        description could not be projected."""
        with self.lock:
            started = self.started.setdefault(step_id, self.now())
            raw: Dict[str, Any] = {"step_id": step_id, "solution_id": solution_id, "kind": kind, "label_key": label_key,
                                   "state": state, "counts": counts or {}, "items": items or [],
                                   "affects_user": affects_user, "started_at": started}
            if state != "running":
                raw["ended_at"] = self.now()
            event = project_or_none(raw, trace_id=self.trace_id, viewer_may_see_titles=self.viewer_may_see_titles)
            if event is None:
                return None
            self.latest[step_id] = event
            if event.state == "running":
                at = self.clock()
                sent = self.running_sent.get(step_id, 0)
                last = self.last_sent.get(step_id)
                if sent >= self.max_running_updates or (last is not None and at - last < self.min_interval):
                    return event
                self.last_sent[step_id] = at
                self.running_sent[step_id] = sent + 1
        try:
            self.emit(progress_event(event))
        except Exception:  # noqa: BLE001  a consumer's stream must never break the run
            pass
        return event

    def summary(self) -> List[Dict[str, Any]]:
        """The latest event of every finished step, in the order the steps began: what a consumer stores to show the
        same account after the run. A step still running is left out."""
        with self.lock:
            return [e.to_dict() for e in self.latest.values() if e.state != "running"]
