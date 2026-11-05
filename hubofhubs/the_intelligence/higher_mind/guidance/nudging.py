"""Guidance arms. Each takes the request and the live objectives and returns the seat's answer: ``None`` when no nudge is due, else a mapping with
``nudge`` (one sentence for the Planner naming the next target and where it stands now), ``objective`` (the id it points at) and ``quality_criteria``
(criterion name to weight, only what the objective itself carries). Nothing is invented: the sentence uses the words and figures the objective holds.

An objective is a mapping with ``id``, ``name``, ``next_target`` and optionally ``reading`` (where it stands now), ``in_focus`` (the person is working on it),
``nudged_recently`` (it was raised lately, so it is left alone) and ``criteria`` (quality criteria that belong to it).

``rule_gate`` decides first whether to hold back (urgent matters, a person who is upset, a request to stop, a lookup or topic that has nothing to do with the
objectives, an objective raised lately) and otherwise points at the focused, else the most related, objective. ``overlap_only`` nudges only when the request
shares words with an objective: the retrieval alternative with no hold-back rules. ``always_nudge`` points at the first objective every time: the bound.
Standard library plus the hub and ``esoi``."""
import re
from typing import Any, Dict, Mapping, Optional, Sequence

from esoi import implementation

WORD = re.compile(r"[a-z0-9]+")
STOP_WORDS = frozenset("a an the and or of to in on for at by is are was were be i my me we our you your it its this that with from do did does what when where who how which can could should would will just".split())
HOLD_BACK_PHRASES = {
    "urgent": ("urgent", "emergency", "asap", "right now", "due today", "immediately", "injury", "injured", "outage", "is down", "safety"),
    "upset": ("upset", "worried", "discouraged", "frustrated", "anxious", "stressed", "hopeless", "overwhelmed", "i give up", "feel terrible"),
    "stop": ("stop reminding", "stop nudging", "don't remind", "do not remind", "no more reminders", "quit nagging"),
}
OPEN_PHRASES = ("thanks", "thank you", "goodbye", "bye", "that is all", "that's all", "i'm done", "i am done", "what next", "what's next", "what is next",
                "what else", "where do things stand", "where things stand", "free for", "nothing else", "anything else", "what should i do next", "do next", "work on next", "work on first", "good use of")


def words(text: str) -> frozenset:
    """The content words of ``text``, each without a plural s so that run and runs match."""
    return frozenset(w[:-1] if len(w) > 3 and w.endswith("s") else w for w in WORD.findall(str(text).lower()) if w not in STOP_WORDS)


def related(request: str, objective: Mapping[str, Any]) -> int:
    """How many content words the request shares with the objective's name and next target (a reading is a figure, not a topic)."""
    return len(words(request) & words(" ".join(str(objective.get(k) or "") for k in ("name", "next_target"))))


def holds_back_reason(request: str) -> str:
    low = request.lower()
    for reason, phrases in HOLD_BACK_PHRASES.items():
        if any(p in low for p in phrases):
            return reason
    return ""


def is_open_moment(request: str) -> bool:
    """A person who is finishing, idle, saying thanks or asking what comes next: a moment a pointer fits whatever they just did."""
    low = request.lower()
    return any(p in low for p in OPEN_PHRASES)


def pointers(objectives: Sequence[Mapping[str, Any]]) -> list:
    return [o for o in objectives if o.get("id") and o.get("next_target")]


def sentence(objective: Mapping[str, Any]) -> str:
    reading = str(objective.get("reading") or "").strip().rstrip(".")
    base = f"Next for {objective.get('name') or objective['id']}: {str(objective['next_target']).strip().rstrip('.')}"
    return f"{base} ({reading})." if reading else base + "."


def answer(objective: Mapping[str, Any]) -> Dict[str, Any]:
    criteria = objective.get("criteria")
    return {"nudge": sentence(objective), "objective": str(objective["id"]),
            "quality_criteria": dict(criteria) if isinstance(criteria, Mapping) else {}}


@implementation("guidance", "rule_gate")
class RuleGate:
    """Holds back when the moment calls for the answer alone; otherwise points at the focused or most related objective's next target and reading."""
    REQUIRES = ()     # pure functions

    def nudge(self, request: str, objectives: Sequence[Mapping[str, Any]] = ()) -> Optional[Mapping[str, Any]]:
        live = [o for o in pointers(objectives) if not o.get("nudged_recently")]
        if not live or holds_back_reason(request):
            return None
        relevant = [o for o in live if related(request, o)]
        if not relevant and not is_open_moment(request):
            return None      # nothing to do with the objectives, and not a moment a pointer fits
        pool = relevant or live
        return answer(max(pool, key=lambda o: (related(request, o), bool(o.get("in_focus")))))


@implementation("guidance", "overlap_only")
class OverlapOnly:
    """Points at the objective the request shares the most words with, and says nothing when it shares none: no hold-back rules."""
    REQUIRES = ()     # pure functions

    def nudge(self, request: str, objectives: Sequence[Mapping[str, Any]] = ()) -> Optional[Mapping[str, Any]]:
        live = pointers(objectives)
        best = max(live, key=lambda o: related(request, o), default=None)
        return answer(best) if best is not None and related(request, best) > 0 else None


@implementation("guidance", "always_nudge")
class AlwaysNudge:
    """Points at the first objective with a next target on every request: what a flow with no decision about when to speak implies. The bound the gate has to beat."""
    REQUIRES = ()     # nothing

    def nudge(self, request: str, objectives: Sequence[Mapping[str, Any]] = ()) -> Optional[Mapping[str, Any]]:
        live = pointers(objectives)
        return answer(live[0]) if live else None
