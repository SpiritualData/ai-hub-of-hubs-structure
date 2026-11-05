"""Objectives arms. Both take the person's recorded objectives (the system's own data, mapped to ``id``, ``title``, ``parent``, ``done_when`` and ``met``) and
answer the two calls of the seat. Neither calls a model.

``rolled_up`` reads the hierarchy: an objective's progress is the share of its units that are met, where its units are its own criteria (each met or not) and its
children (each counting its own progress), so a goal rolls up to its parent; it is met only when every unit is, and one with no criteria and no children is met only
when it says so. ``place`` puts a request under the live (not met) objective whose own words (title and criteria) it shares the most meaningful words with, the
deeper one on a tie, and returns the path from the top; with no shared word it names no objective. ``flat_list`` is the bound: no roll-up, only the top level, the
first listed one that shares a word. Standard library plus the hub and ``esoi``."""
import re
from typing import Any, Dict, List, Mapping, Sequence, Set, Tuple

from esoi import implementation

STOP = frozenset("the and for with that this what when where which who how can could should would will our your their about into from have has are was were "
                 "been being than then them they you any all but not out use get got let make made please need needs want".split())


def singular(word: str) -> str:
    if word.endswith("oes") and len(word) > 4:
        return word[:-2]
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def words(text: Any) -> Set[str]:
    """The meaningful words of a text: lower case, three letters or more, no common word, a plural folded to its singular."""
    return {singular(w) for w in re.findall(r"[a-z0-9]+", str(text or "").lower()) if len(w) >= 3 and w not in STOP}


def criteria_of(objective: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    return [c for c in objective.get("done_when") or () if isinstance(c, Mapping)]


def own_progress(objective: Mapping[str, Any]) -> float:
    """The share of the objective's own criteria that are met; with none, 1 when it says it is met and 0 otherwise."""
    criteria = criteria_of(objective)
    if not criteria:
        return 1.0 if objective.get("met") else 0.0
    return sum(bool(c.get("met")) for c in criteria) / len(criteria)


def state_of(progress: float) -> str:
    return "met" if progress >= 1 else "not started" if progress <= 0 else "in progress"


def children_of(objectives: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    ids = {str(o.get("id")) for o in objectives}
    by_parent: Dict[str, List[Mapping[str, Any]]] = {}
    for o in objectives:
        parent = str(o.get("parent") or "")
        by_parent.setdefault(parent if parent in ids and parent != str(o.get("id")) else "", []).append(o)
    return by_parent


def rolled_up(objectives: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_parent = children_of(objectives)
    out: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    def visit(o: Mapping[str, Any], depth: int) -> float:
        ident = str(o.get("id"))
        seen.add(ident)
        kids = [k for k in by_parent.get(ident, ()) if str(k.get("id")) not in seen]
        row = {"id": ident, "title": str(o.get("title") or ""), "parent": str(o.get("parent") or ""), "depth": depth, "state": "", "progress": 0.0}
        out.append(row)
        criteria = criteria_of(o)
        total = len(criteria) + len(kids)
        gained = float(sum(bool(c.get("met")) for c in criteria)) + sum(visit(k, depth + 1) for k in kids)
        progress = gained / total if total else own_progress(o)
        row["progress"], row["state"] = round(progress, 4), state_of(progress)
        return progress

    for root in list(by_parent.get("", ())) + list(objectives):     # a member of a cycle has no root above it: listed from the first one reached
        if str(root.get("id")) not in seen:
            visit(root, 0)
    return out


def path_to(ident: str, objectives: Sequence[Mapping[str, Any]]) -> List[str]:
    by_id = {str(o.get("id")): o for o in objectives}
    path: List[str] = []
    while ident in by_id and ident not in path:
        path.append(ident)
        ident = str(by_id[ident].get("parent") or "")
    return path[::-1]


def own_words(objective: Mapping[str, Any]) -> Set[str]:
    return words(objective.get("title")).union(*(words(c.get("text")) for c in criteria_of(objective)))


def placed(chosen: str, score: int, why: str, objectives: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {"objective": chosen, "path": path_to(chosen, objectives) if chosen else [], "score": score, "reason": why}


@implementation("live-objectives", "rolled_up")
class RolledUp:
    """The hierarchy with each goal rolled up to its parent, and a request placed under the live objective that shares the most of its words."""
    REQUIRES = ()     # standard library

    def current(self, person: str = "", objectives: Sequence[Mapping[str, Any]] = ()) -> Sequence[Mapping[str, Any]]:
        return rolled_up(objectives)

    def place(self, request: str, person: str = "", objectives: Sequence[Mapping[str, Any]] = ()) -> Mapping[str, Any]:
        state = {row["id"]: row for row in rolled_up(objectives)}
        asked, best = words(request), ("", 0, -1)
        for o in objectives:
            row = state.get(str(o.get("id")))
            if row is None or row["state"] == "met":
                continue
            score = len(asked & own_words(o))
            if score and (score, row["depth"]) > (best[1], best[2]):
                best = (str(o.get("id")), score, row["depth"])
        if not best[0]:
            return placed("", 0, "the request shares no word with a live objective", objectives)
        return placed(best[0], best[1], f"it shares {best[1]} word(s) with the objective's title and criteria", objectives)


@implementation("live-objectives", "flat_list")
class FlatList:
    """The objectives as listed, with no roll-up and only the top level placed: the bound the hierarchy-reading arm has to beat."""
    REQUIRES = ()     # standard library

    def current(self, person: str = "", objectives: Sequence[Mapping[str, Any]] = ()) -> Sequence[Mapping[str, Any]]:
        return [{"id": str(o.get("id")), "title": str(o.get("title") or ""), "parent": str(o.get("parent") or ""), "depth": 0,
                 "state": state_of(own_progress(o)), "progress": round(own_progress(o), 4)} for o in objectives]

    def place(self, request: str, person: str = "", objectives: Sequence[Mapping[str, Any]] = ()) -> Mapping[str, Any]:
        asked = words(request)
        for o in objectives:
            if not o.get("parent") and asked & own_words(o):
                return placed(str(o.get("id")), len(asked & own_words(o)), "the first top-level objective that shares a word", objectives)
        return placed("", 0, "no top-level objective shares a word", objectives)
