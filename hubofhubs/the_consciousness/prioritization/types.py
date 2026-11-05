"""The types Prioritization takes and returns. Standard library only; a consumer builds these from its own rows (tasks, asks, standing work)
and the seat also accepts the same fields as plain mappings, so ``hubofhubs.run("prioritization", {...})`` needs no import.

A candidate is anything that competes for attention: ``id`` and ``kind`` (any kind the consumer names, such as ``ask`` or ``standing-work``) and the fields
the consumer's own data carries (``FIELDS``). Prioritization never invents a field: one a candidate does not carry is skipped, not guessed.

``Stated`` is what the Representative knows about the person: an explicit ordering, what must go first or wait, what the person's feedback implies, and the weights
of the quality profile. ``Ranked`` is one item of the answer: its place, the reason in words and the priority in the form Metric Translation and the Planner use."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Sequence

#: The fields a candidate may carry.
FIELDS: Mapping[str, str] = {
    "rank": "the person's own rank for the item, 0 is highest, absent is unranked",
    "deadline": "ISO time the item is due by",
    "blocked_by": "ids of items that must be done first",
    "waiting": "people who are waiting on this item",
    "asked_at": "ISO time the person asked for it, oldest first (an open ask)",
    "last_nudged_at": "ISO time the person was last reminded about it",
    "request": "what to run for it when it is chosen",
    "title": "what it is, for the reason and the milestone",
}


@dataclass(frozen=True)
class Stated:
    """What the person said or implied. Every field is optional."""
    order: Sequence[str] = ()                       # ids the person explicitly ordered, first is first
    deferred: Sequence[str] = ()                    # ids that must wait
    not_before: Mapping[str, str] = field(default_factory=dict)      # id -> ISO time before which it waits
    only_kinds: Sequence[str] = ()                  # when set, other kinds are held back
    kind_order: Sequence[str] = ()                  # kinds in the order they come, first first; a kind not listed comes after
    feedback: Sequence[Mapping[str, Any]] = ()      # {"about": id or kind, "direction": "sooner" or "later"}: what the person's reactions imply
    quality_weights: Mapping[str, float] = field(default_factory=dict)

    @staticmethod
    def of(raw: Any) -> "Stated":
        if isinstance(raw, Stated):
            return raw
        raw = raw or {}
        return Stated(order=tuple(map(str, raw.get("order") or ())), deferred=tuple(map(str, raw.get("deferred") or ())),
                      not_before={str(k): str(v) for k, v in (raw.get("not_before") or {}).items()},
                      only_kinds=tuple(map(str, raw.get("only_kinds") or ())), kind_order=tuple(map(str, raw.get("kind_order") or ())),
                      feedback=tuple(dict(f) for f in (raw.get("feedback") or ())), quality_weights=dict(raw.get("quality_weights") or {}))


@dataclass(frozen=True)
class Ranked:
    """One item of the ordered answer."""
    id: str
    rank: int                                       # 1 is first
    kind: str
    reason: str
    metric: Mapping[str, Any]                       # milestone, weight, due and criterion: the priority as Metric Translation and the Planner use it
    request: str = ""

    def as_mapping(self) -> Dict[str, Any]:
        return {"id": self.id, "rank": self.rank, "kind": self.kind, "reason": self.reason, "metric": dict(self.metric), "request": self.request}


def ids_of(ordered: Sequence[Mapping[str, Any]]) -> List[str]:
    """The ids of an ordered answer, first to last."""
    return [str(item["id"]) for item in ordered]
