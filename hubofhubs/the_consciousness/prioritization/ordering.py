"""Prioritization arms. Both take the candidates and what the person stated and return the answer of the seat: ``ordered`` (each item with its place,
reason and metric-ready priority), ``held`` (items the person's constraints keep back, with why), ``quality_weights`` and ``constraints``. Neither calls a model.

``stated_fields`` orders by the fields a candidate carries and what the person stated: the person's pins first and what they deferred last, what their
feedback implies next to those, then the kind in the order the person or consumer gave, a blocked item after the unblocked, the person's own rank (ranked
first, ascending, unranked after in the order given), the earlier deadline, the earlier ask, the more people waiting, and the longer since a nudge. Ties keep
the order given. ``as_given`` keeps the order given: the bound the first arm has to beat.
Standard library plus the hub and ``esoi``."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from esoi import implementation

from hubofhubs.the_consciousness.prioritization.types import Ranked, Stated

NEVER = datetime.max.replace(tzinfo=timezone.utc)


def moment(raw: Any) -> Optional[datetime]:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        found = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return None
    return found if found.tzinfo else found.replace(tzinfo=timezone.utc)


def metric_form(item: Mapping[str, Any], place: int, count: int) -> Dict[str, Any]:
    """The priority as Metric Translation and the Planner use it: what is to be done, its weight among the ordered items (the weights sum to 1, the first
    weighs most), by when, and the criterion that says it is done."""
    weight = round((count - place + 1) / (count * (count + 1) / 2), 4)
    return {"milestone": str(item.get("title") or item.get("id")), "weight": weight,
            "due": str(item.get("deadline") or ""), "criterion": "the item is done and the person can see it is"}


def ranked(items: Sequence[Mapping[str, Any]], reasons: Sequence[str]) -> List[Dict[str, Any]]:
    return [Ranked(id=str(i.get("id")), rank=n, kind=str(i.get("kind") or ""), reason=reasons[n - 1], metric=metric_form(i, n, len(items)),
                   request=str(i.get("request") or "")).as_mapping() for n, i in enumerate(items, 1)]


def answer(ordered: Sequence[Mapping[str, Any]], reasons: Sequence[str], held: Sequence[Mapping[str, Any]], stated: Stated) -> Dict[str, Any]:
    return {"ordered": ranked(ordered, reasons), "held": list(held), "quality_weights": dict(stated.quality_weights),
            "constraints": [{"kind": "only_kinds", "value": list(stated.only_kinds)}] if stated.only_kinds else []}


@implementation("prioritization", "as_given")
class AsGiven:
    """The order the candidates arrive in, with nothing read from them: the bound the field-reading arm has to beat."""
    REQUIRES = ()     # standard library

    def prioritize(self, person: str = "", request: str = "", implied: Optional[Mapping[str, Any]] = None, candidates: Sequence[Mapping[str, Any]] = (),
                   stated: Any = None, now: str = "") -> Mapping[str, Any]:
        said = Stated.of(stated)
        return answer(list(candidates), ["kept in the order given"] * len(candidates), [], said)


@implementation("prioritization", "stated_fields")
class StatedFields:
    """Orders by the stated and carried fields of each candidate, with a reason that names the rule that placed it."""
    REQUIRES = ()     # standard library

    def prioritize(self, person: str = "", request: str = "", implied: Optional[Mapping[str, Any]] = None, candidates: Sequence[Mapping[str, Any]] = (),
                   stated: Any = None, now: str = "") -> Mapping[str, Any]:
        said = Stated.of(stated if stated is not None else implied)
        at = moment(now) or datetime.now(timezone.utc)
        kinds = tuple(said.kind_order)
        held: List[Dict[str, Any]] = []
        kept: List[Tuple[Tuple, Mapping[str, Any], List[str]]] = []
        present = {str(c.get("id")) for c in candidates}
        feedback = {str(f.get("about")): str(f.get("direction")) for f in said.feedback}
        for index, item in enumerate(candidates):
            ident, kind = str(item.get("id")), str(item.get("kind") or "")
            if said.only_kinds and kind not in said.only_kinds:
                held.append({"id": ident, "reason": f"the person limited the work to {', '.join(said.only_kinds)}"})
                continue
            wait = moment(said.not_before.get(ident))
            if wait is not None and at < wait:
                held.append({"id": ident, "reason": f"the person said not before {said.not_before[ident]}"})
                continue
            key, why = self.key(item, index, person, said, kinds, present, feedback, at)
            kept.append((key, item, why))
        kept.sort(key=lambda row: row[0])
        return answer([row[1] for row in kept], ["; ".join(row[2]) or "no stated field applies, kept in the order given" for row in kept], held, said)

    def key(self, item: Mapping[str, Any], index: int, person: str, said: Stated, kinds: Sequence[str], present: set, feedback: Mapping[str, str],
            now: datetime) -> Tuple[Tuple, List[str]]:
        ident, kind = str(item.get("id")), str(item.get("kind") or "")
        why: List[str] = []
        if ident in said.order:
            stance, spot = 0, said.order.index(ident)
            why.append("the person ordered it")
        elif ident in said.deferred:
            stance, spot = 4, 0
            why.append("the person deferred it")
        else:
            spot = 0
            direction = feedback.get(ident) or feedback.get(kind) or ""
            stance = {"sooner": 1, "later": 3}.get(direction, 2)
            if stance != 2:
                why.append(f"the person's feedback implies {direction}")
        tier = kinds.index(kind) if kind in kinds else len(kinds)
        if kind in kinds:
            why.append(f"kind {kind} is {tier + 1} of {len(kinds)} in the order of kinds")
        blocked = any(str(b) in present for b in item.get("blocked_by") or ())
        if blocked:
            why.append("it waits for " + ", ".join(str(b) for b in item["blocked_by"] if str(b) in present))
        own = item.get("rank")
        rank_key = (0, int(own)) if isinstance(own, int) and not isinstance(own, bool) else (1, 0)
        if rank_key[0] == 0:
            why.append(f"ranked {own}")
        deadline = moment(item.get("deadline"))
        if deadline is not None:
            why.append(f"due {item['deadline']}" + (" and overdue" if deadline < now else ""))
        asked = moment(item.get("asked_at"))
        if asked is not None:
            why.append(f"asked {item['asked_at']}")
        waiting = len(item.get("waiting") or ())
        if waiting:
            why.append(f"{waiting} waiting")
        nudged = moment(item.get("last_nudged_at")) or datetime.min.replace(tzinfo=timezone.utc)
        return (stance, spot, tier, blocked, rank_key, deadline or NEVER, asked or NEVER, -waiting, nudged, index), why
