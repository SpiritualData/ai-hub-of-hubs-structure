"""Metric Upkeep: a milestone's metrics are kept able to show progress, so a turn never has the excuse of waiting on a person.

The state of each metric is decided by code from the record's fields, never by reading its text for meaning: no value recorded and no source is
``no_source``; no value with a source is ``unmeasured``; a value whose ``measured_through`` day is older than its ``expiration`` allows is ``stale``; else
``fresh``. A stale or unmeasured metric with a reader for its source is read and the reading recorded through ESOI Application. A metric with no source
gets a ``propose_source`` action (proposing one is not built yet: it is reported pending, never guessed).

When the milestone's metric moves only through a person (``moved_by: person``, for example "videos published"), upkeep adds ONE intermediate metric record
the AI can move now ("scripts meeting the rubric: n of 6"): a child record with ``parent_metric_ids=[parent]``, a definition that is countable now and a
``cascading_conditionals`` line saying how the child feeds the parent. A cheap call proposes it; Decision Check then asks independent views whether the
child really tracks progress toward the parent's done test (and is not a count that can rise without that progress). Only an agreed ``tracks`` adds it,
through ESOI Application's ensure-one addition, so a repeat adds nothing; an existing child is reused, never a second. Standard library plus the hub and
``esoi``."""
import datetime
import json
import re
from typing import Any, Callable, Dict, List, Mapping, Optional

from esoi import Lazy, implementation

from hubofhubs.the_intelligence.critical_thinking.decision_check.interface import DecisionChecking
from hubofhubs.the_intelligence.critical_thinking.esoi_application.interface import EsoiApplying

FRESH, STALE, UNMEASURED, NO_SOURCE = "fresh", "stale", "unmeasured", "no_source"
NONE, READ, PROPOSE_SOURCE, DEFINE_INTERMEDIATE = "none", "read", "propose_source", "define_intermediate"
PERSON = "person"
TRACKS, DOES_NOT_TRACK = "tracks", "does_not_track"
PERIOD_DAYS = {"daily": 1, "day": 1, "weekly": 7, "week": 7, "monthly": 30, "month": 30, "quarterly": 91, "yearly": 365}
EM_DASH = "—"

PROPOSE_PROMPT = """A milestone's metric moves only when a person acts, so the AI needs one intermediate metric it can move by its own work now.

Milestone: {name}
Done when: {done_when}
Its metric: {parent_name}. Recorded: {parent_record}
{ai_work}
Propose ONE intermediate metric: a count of AI-made work that is a necessary step toward the done test (for example deliverables meeting a rubric, or
questions the decision needs answered with a cited source), countable now, with the total it is counted out of. When the AI's work is named above, count
units of exactly that work, and make the rubric exactly what that work says each unit must meet.
Reply with JSON only: {{"name": "<what is counted, short>", "definition": "<how to count it, one sentence>", "unit": "<what one unit is>",
"total": <a whole number, the count that means done>, "feeds_parent": "<one sentence: how reaching the total moves the parent metric>",
"rubric": ["<what one unit must meet to count>", ...]}}. Give 3 or 4 rubric items, each checkable by reading the unit's own text against the milestone's records
(never by what happens later, outside the text or after a person acts), and none asking the unit to state a figure, length or date the milestone does not give. Use only what the milestone above says; invent no figure. Do not use em dashes."""

TRACK_VIEWS = (
    ("done-test", "Does counting this intermediate metric measure real progress toward the parent's done test, so that reaching its total leaves less for the person to do?"),
    ("gaming", "Could this intermediate metric rise while nothing moves toward the parent's done test (a count of busywork, a restatement, or a figure the AI could raise "
               "without useful work)? Pick tracks only if it could not."),
)


def day_of(value: Any) -> Optional[datetime.date]:
    found = re.search(r"\d{4}-\d{2}-\d{2}", str(value or ""))
    try:
        return datetime.date.fromisoformat(found.group(0)) if found else None
    except ValueError:
        return None


def expiration_days(value: Any) -> Optional[int]:
    """Days a reading stays fresh, from the record's ``expiration``: a number of days, or a period word; None means it never expires."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if value > 0 else None
    text = str(value or "").strip().lower()
    digits = re.match(r"(\d+)", text)
    if digits:
        unit = 7 if "week" in text else 30 if "month" in text else 1
        return int(digits.group(1)) * unit
    return next((days for word, days in PERIOD_DAYS.items() if text.startswith(word)), None)


def has_value(metric: Mapping[str, Any]) -> bool:
    """A value is recorded: a ``value`` field, or a ``record`` text (the record's written reading)."""
    return metric.get("value") not in (None, "") or bool(str(metric.get("record") or "").strip())


def state_of(metric: Mapping[str, Any], today: Optional[datetime.date]) -> str:
    """The metric's state, from its fields alone."""
    source = str(metric.get("source") or "").strip()
    if not has_value(metric):
        return UNMEASURED if source else NO_SOURCE
    days = expiration_days(metric.get("expiration"))
    through = day_of(metric.get("measured_through"))
    if days is not None and today is not None and (through is None or (today - through).days > days):
        return STALE
    return FRESH


def metrics_of(metrics: Mapping[str, Mapping[str, Any]], solution_id: str) -> List[str]:
    """The ids of the metrics that measure the milestone and are not themselves intermediates of another of them."""
    own = [mid for mid, m in metrics.items() if solution_id in (m.get("solution_ids") or [])]
    return [mid for mid in own if not any(feeds(metrics[mid], other) for other in own if other != mid)]


def feeds(metric: Mapping[str, Any], parent: str) -> bool:
    """True when ``metric`` is an intermediate of ``parent``: its ``parent_metric_ids`` name it, or (at a records location that keeps no parent link) its
    ``cascading_conditionals`` line is the one this arm writes, ``feeds <parent>: ...``."""
    return parent in (metric.get("parent_metric_ids") or []) or str(metric.get("cascading_conditionals") or "").startswith(f"feeds {parent}:")


def child_of(metrics: Mapping[str, Mapping[str, Any]], parent: str) -> Optional[str]:
    """The intermediate metric already recorded for ``parent``, if any (at most one is ever added)."""
    return next((mid for mid, m in metrics.items() if mid != parent and feeds(m, parent)), None)


def parse_json(text: Any) -> Dict[str, Any]:
    raw = str(text or "")
    start, end = raw.find("{"), raw.rfind("}")
    try:
        data = json.loads(raw[start:end + 1]) if start >= 0 and end > start else {}
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def proposal_ok(data: Mapping[str, Any]) -> bool:
    """A proposal names what is counted, how, and a whole total above zero, with no em dash: anything else is no proposal."""
    total = data.get("total")
    words = [str(data.get(k) or "").strip() for k in ("name", "definition", "unit", "feeds_parent")]
    return (all(words) and isinstance(total, int) and not isinstance(total, bool) and total > 0
            and not any(EM_DASH in w for w in words))


@implementation("metric-upkeep", "record_fields")
class RecordFieldUpkeep:
    """Decides each metric's state from its record fields by code, reads a stale or unmeasured metric through the reader its source names, and adds one
    intermediate metric for a milestone whose metric moves only through a person, written through ESOI Application after Decision Check agrees the child
    tracks the parent's done test."""
    REQUIRES = ()     # the seats it is handed

    def __init__(self, esoi: Lazy[EsoiApplying], decision: Lazy[DecisionChecking]):
        self.esoi, self.decision = esoi, decision

    def upkeep(self, spec: Mapping[str, Any], metrics: Mapping[str, Mapping[str, Any]], readers: Optional[Mapping[str, Callable[[str], Mapping[str, Any]]]] = None,
               today: str = "", ask: Optional[Callable[[str], str]] = None) -> List[Mapping[str, Any]]:
        day = day_of(today) or datetime.date.today()
        solution_id = str(spec.get("solution_id") or "")
        out: List[Dict[str, Any]] = []
        for mid in metrics_of(metrics, solution_id):
            metric = metrics[mid]
            state = state_of(metric, day)
            action: Dict[str, Any] = {"metric_id": mid, "state": state, "action": NONE}
            source = str(metric.get("source") or "").strip()
            if state in (STALE, UNMEASURED) and source and readers and readers.get(source):
                action.update(self.read(mid, source, readers[source]))
            elif state == NO_SOURCE or (state == STALE and not source):
                action.update(action=PROPOSE_SOURCE, proposed_source=None, why="no arm yet proposes a source; the metric stays without one")
            if str(spec.get("moved_by") or "") == PERSON:
                action.update(self.intermediate(spec, mid, metric, metrics, ask))
            out.append(action)
        return out

    def read(self, mid: str, source: str, reader: Callable[[str], Mapping[str, Any]]) -> Dict[str, Any]:
        try:
            reading = dict(reader(mid) or {})
        except Exception as error:  # noqa: BLE001 -- a source that cannot be read is said, never guessed
            return {"action": READ, "reading": None, "why": f"the source {source!r} could not be read ({type(error).__name__}: {error})"}
        if reading.get("value") in (None, "") or not day_of(reading.get("as_of")):
            return {"action": READ, "reading": None, "why": f"the source {source!r} gave no dated value"}
        line = f"Current value: {reading['value']} (as of {day_of(reading['as_of']).isoformat()}, from {reading.get('source') or source})"
        applied = self.esoi.apply({"edit": {"kind": "metric_edit", "target": mid, "field": "record", "value": line}})
        return {"action": READ, "reading": reading, "recorded": applied}

    def intermediate(self, spec: Mapping[str, Any], parent: str, metric: Mapping[str, Any], metrics: Mapping[str, Mapping[str, Any]],
                     ask: Optional[Callable[[str], str]]) -> Dict[str, Any]:
        existing = child_of(metrics, parent)
        if existing:
            return {"action": DEFINE_INTERMEDIATE, "child_metric": dict(metrics[existing], id=existing, created=False)}
        if ask is None:
            return {"action": DEFINE_INTERMEDIATE, "child_metric": None, "why": "no model call was given to propose an intermediate metric"}
        proposal = parse_json(ask(PROPOSE_PROMPT.format(name=spec.get("name") or "", done_when=spec.get("done_when") or "",
                                                        parent_name=metric.get("name") or parent, parent_record=str(metric.get("record") or "not recorded")[:600],
                                                        ai_work=(f"The AI's work that leads to it: {spec['ai_work']}\n" if spec.get("ai_work") else ""))))
        if not proposal_ok(proposal):
            return {"action": DEFINE_INTERMEDIATE, "child_metric": None, "why": "the proposal was not a countable metric with a total"}
        checked = self.cross_check(spec, metric, proposal, ask)
        if checked.get("pick") != TRACKS:
            return {"action": DEFINE_INTERMEDIATE, "child_metric": None, "why": "the independent check did not agree the intermediate tracks the done test",
                    "check": {k: checked.get(k) for k in ("outcome", "pick", "agreement")}}
        key = str(proposal["name"]).strip()      # the record's name is its ensure-one key at every records location (a repeat finds it by name)
        rubric = [str(r) for r in proposal.get("rubric") or [] if str(r).strip()]
        fields = {"name": str(proposal["name"]), "purpose": str(proposal["definition"]), "record": f"Current value: 0 of {proposal['total']} {proposal['unit']}",
                  "unit": str(proposal["unit"]), "total": str(proposal["total"]), "parent_metric_ids": [parent],
                  "solution_ids": [str(spec.get("solution_id") or "")],
                  "cascading_conditionals": f"feeds {parent}: {proposal['feeds_parent']}"}
        if rubric:
            fields["rubric"] = rubric
        applied = self.esoi.apply({"edit": {"kind": "record_add", "table": "metrics", "key": key, "fields": fields}})
        return {"action": DEFINE_INTERMEDIATE, "child_metric": dict(fields, id=str(applied.get("target") or key), created=bool(applied.get("created")),
                                                                    proposed=bool(applied.get("proposed"))),
                "recorded": applied, "check": {k: checked.get(k) for k in ("outcome", "pick", "agreement")}}

    def cross_check(self, spec: Mapping[str, Any], metric: Mapping[str, Any], proposal: Mapping[str, Any], ask: Callable[[str], str]) -> Mapping[str, Any]:
        """Decision Check's independent views on whether the child tracks the parent's done test; the draft is ``tracks`` and must be agreed, not assumed."""
        evidence = (f"Parent milestone: {spec.get('name')}. Done when: {spec.get('done_when')}. Parent metric: {metric.get('name')}.\n"
                    f"Proposed intermediate metric: {proposal.get('name')}. Counted as: {proposal.get('definition')} Total: {proposal.get('total')} {proposal.get('unit')}. "
                    f"How it feeds the parent: {proposal.get('feeds_parent')}")
        binding = {"kind": "pick", "options": [{"id": TRACKS, "text": "it tracks real progress toward the parent's done test"},
                                               {"id": DOES_NOT_TRACK, "text": "it does not, or it could rise without that progress"}],
                   "views": [{"id": vid, "instruction": text, "evidence": evidence} for vid, text in TRACK_VIEWS], "max_calls": 4, "parallel": 2,
                   "draft_basis": str(proposal.get("feeds_parent") or "")}
        try:
            return dict(self.decision.check(TRACKS, binding, ask) or {})
        except Exception as error:  # noqa: BLE001 -- a check that could not run never adds a metric
            return {"outcome": "abstained", "pick": None, "why": f"{type(error).__name__}: {error}"}
