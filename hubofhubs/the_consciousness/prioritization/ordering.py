"""Prioritization arms. Both take the candidates and what the person stated and return the answer of the seat: ``ordered`` (each item with its place,
reason and metric-ready priority), ``held`` (items the person's constraints keep back, with why), ``quality_weights`` and ``constraints``. Neither calls a model.

``stated_fields`` orders by the fields a candidate carries and what the person stated: the person's pins first and what they deferred last, what their
feedback implies next to those, then the kind in the order the person or consumer gave, a blocked item after the unblocked, the person's own rank (ranked
first, ascending, unranked after in the order given), the earlier deadline, the earlier ask, the more people waiting, and the longer since a nudge. Ties keep
the order given. ``as_given`` keeps the order given: the bound the first arm has to beat.

A call names its ``subject`` (``work``, ``asks`` or ``goals``, see ``types.SUBJECTS``). The person's stated order, deferrals, feedback and kind order come first for
every subject; then ``work`` reads the fields above, ``asks`` reads what answering each one unblocks (the most first), the person's own rank, the earlier deadline, the
shorter effort, the older ask and the longer since the person was last asked, and ``goals`` (the solution milestones of the person's intents) holds back a milestone that
is met or whose end condition has passed, lets what the person said about a milestone's solution or intent count for it, and reads the person's rank, the milestone that
others depend on or that unblocks more before those that wait, and the earlier target time. A ``batch_limit`` puts only that many in the answer; the rest are held with
their place and the reason (the person is shown that many at once).
Standard library plus the hub and ``esoi``."""
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from esoi import implementation

from hubofhubs.the_consciousness.prioritization.signals import unblocks_of
from hubofhubs.the_consciousness.prioritization.types import SUBJECTS, Ranked, Stated

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


def checked_subject(subject: str) -> str:
    if subject not in SUBJECTS:
        raise ValueError(f"subject must be one of {', '.join(SUBJECTS)}, not {subject!r}")
    return subject


def answer(ordered: Sequence[Mapping[str, Any]], reasons: Sequence[str], held: Sequence[Mapping[str, Any]], stated: Stated, subject: str = "work",
           batch_limit: int = 0) -> Dict[str, Any]:
    """The seat's answer. With a ``batch_limit`` above zero only that many come back in ``ordered``; the rest join ``held`` with their place and the reason."""
    held = list(held)
    if batch_limit > 0 and len(ordered) > batch_limit:
        held += [{"id": str(i.get("id")), "rank": n, "reason": f"held for a later batch: {batch_limit} are put in front of the person at once and this one is place {n}"}
                 for n, i in enumerate(ordered[batch_limit:], batch_limit + 1)]
        ordered, reasons = ordered[:batch_limit], reasons[:batch_limit]
    out = {"subject": subject, "ordered": ranked(ordered, reasons), "held": held, "quality_weights": dict(stated.quality_weights),
           "constraints": [{"kind": "only_kinds", "value": list(stated.only_kinds)}] if stated.only_kinds else []}
    return out


@implementation("prioritization", "as_given")
class AsGiven:
    """The order the candidates arrive in, with nothing read from them: the bound the field-reading arm has to beat."""
    REQUIRES = ()     # standard library

    def prioritize(self, person: str = "", request: str = "", implied: Optional[Mapping[str, Any]] = None, candidates: Sequence[Mapping[str, Any]] = (),
                   stated: Any = None, now: str = "", subject: str = "work", batch_limit: int = 0) -> Mapping[str, Any]:
        said = Stated.of(stated)
        return answer(list(candidates), ["kept in the order given"] * len(candidates), [], said, checked_subject(subject), batch_limit)


@implementation("prioritization", "stated_fields")
class StatedFields:
    """Orders by the stated and carried fields of each candidate, with a reason that names the rule that placed it."""
    REQUIRES = ()     # standard library

    def prioritize(self, person: str = "", request: str = "", implied: Optional[Mapping[str, Any]] = None, candidates: Sequence[Mapping[str, Any]] = (),
                   stated: Any = None, now: str = "", subject: str = "work", batch_limit: int = 0) -> Mapping[str, Any]:
        checked_subject(subject)
        said = Stated.of(stated if stated is not None else implied)
        held: List[Dict[str, Any]] = []
        if subject == "goals":
            candidates = self.live_milestones(candidates, held, moment(now) or datetime.now(timezone.utc))
        at = moment(now) or datetime.now(timezone.utc)
        kinds = tuple(said.kind_order)
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
            key, why = self.key(item, index, person, said, kinds, present, feedback, at, subject, candidates)
            kept.append((key, item, why))
        kept.sort(key=lambda row: row[0])
        return answer([row[1] for row in kept], ["; ".join(row[2]) or "no stated field applies, kept in the order given" for row in kept], held, said, subject, batch_limit)

    def live_milestones(self, candidates: Sequence[Mapping[str, Any]], held: List[Dict[str, Any]], now: datetime) -> List[Mapping[str, Any]]:
        """The milestones still a priority: a met one, or one whose end condition has passed, is held back with the reason."""
        live = []
        for item in candidates:
            ends = moment(item.get("ends_at"))
            if item.get("met"):
                held.append({"id": str(item.get("id")), "reason": "the milestone is met, so it is no longer a priority"})
            elif ends is not None and ends <= now:
                held.append({"id": str(item.get("id")), "reason": f"its end condition passed at {item['ends_at']}"})
            else:
                live.append(item)
        return live

    def key(self, item: Mapping[str, Any], index: int, person: str, said: Stated, kinds: Sequence[str], present: set, feedback: Mapping[str, str],
            now: datetime, subject: str = "work", candidates: Sequence[Mapping[str, Any]] = ()) -> Tuple[Tuple, List[str]]:
        ident, kind = str(item.get("id")), str(item.get("kind") or "")
        why: List[str] = []
        names = [ident] + [str(item[f]) for f in ("solution", "intent") if subject == "goals" and item.get(f)]      # what the person said about a milestone's solution or intent counts for it
        ordered = [said.order.index(n) for n in names if n in said.order]
        if ordered:
            stance, spot = 0, min(ordered)
            why.append("the person ordered it" if ident in said.order else "the person ordered its solution or intent")
        elif any(n in said.deferred for n in names):
            stance, spot = 4, 0
            why.append("the person deferred it")
        else:
            spot = 0
            direction = next((feedback[n] for n in names if n in feedback), "") or feedback.get(kind) or ""
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
        if subject == "asks":
            freed = unblocks_of(item, candidates)
            if freed:
                why.append(f"answering it frees {freed} waiting item{'s' if freed != 1 else ''}")
            effort = item.get("effort")
            minutes = effort if isinstance(effort, (int, float)) and not isinstance(effort, bool) else float("inf")
            if minutes != float("inf"):
                why.append(f"takes about {effort} minutes")
            return (stance, spot, tier, blocked, rank_key, -freed, deadline or NEVER, -waiting, minutes, asked or NEVER, nudged, index), why
        if subject == "goals":
            freed = unblocks_of(item, candidates)
            if freed:
                why.append(f"reaching it frees {freed} other milestone{'s' if freed != 1 else ''}")
            if item.get("solution"):
                why.append(f"a milestone of {item['solution']}")
            return (stance, spot, tier, blocked, rank_key, -freed, deadline or NEVER, index), why
        return (stance, spot, tier, blocked, rank_key, deadline or NEVER, asked or NEVER, -waiting, nudged, index), why
