"""Structure in conversation: what structure a reply carries, decided by code from the move the turn calls for and the records the system holds.
Standard library plus ``esoi``.

The caller (a planner) names the move; this decides the rest, by code, from fields only:

* ``none``     the reply stays plain: no block, no offer.
* ``frame``    advice or a new idea: the problem it serves, the ideal, the solution, the alternatives, the metric and the next milestone.
* ``compare``  a choice between options: the solution, the alternatives and the metric that shows which works.
* ``review``   "is this working": the metric with the value the records hold (never one made up) and the next milestone.
* ``focus``    a person who is stuck: the one problem and the next milestone.

Records the system already holds are used first (a relevant solution, its alternatives, its metric, its milestones); only what is missing is proposed from the
caller's ``draft``, and at most one offer keeps the missing pieces as one batch of ensure-one additions. An existing record is never edited."""
import re
from typing import Any, Dict, List, Mapping, Optional

from esoi import implementation

MOVES = ("none", "frame", "compare", "review", "focus")
PARTS = {"frame": ("problem", "ideal", "solution", "alternatives", "metric", "milestone"),
         "compare": ("solution", "alternatives", "metric"),
         "review": ("solution", "metric", "milestone"),
         "focus": ("problem", "milestone")}
OFFERED = ("frame", "compare")
MAX_ALTERNATIVES = 5
READING = re.compile(r"^Current value:\s*(?P<value>.*?)\s*\(as of (?P<as_of>[^,)]*?)(?:,\s*from (?P<source>[^)]*))?\)\s*$", re.MULTILINE)


def normal(text: Any) -> str:
    """A name as compared for the same record: lower case, single spaces."""
    return " ".join(str(text or "").lower().split())


def rows(records: Mapping[str, Any], table: str) -> Mapping[str, Mapping[str, Any]]:
    return records.get(table) or {}


def ids_of(value: Any) -> List[str]:
    """The ids a link column holds, whether it is a list or a text separated by semicolons or commas."""
    parts = value if isinstance(value, (list, tuple)) else str(value or "").replace(",", ";").split(";")
    return [str(part).strip() for part in parts if str(part).strip()]


def missing(block: Optional[Mapping[str, Any]]) -> List[str]:
    """The pieces the reply to this turn may offer to keep, decided before it is written and in order: the solution, metric and milestone the block does not hold,
    and the alternatives always, because a reply of this move brings options of its own (keeping them is ensure-one by name, so a held one is never added twice)."""
    if not block or block.get("move") not in OFFERED:
        return []
    absent = {"solution": not block.get("solution"), "alternatives": "alternatives" in block, "metric": not block.get("metric"),
              "milestone": "milestone" in block and not block.get("milestone")}
    return [piece for piece in ("solution", "alternatives", "metric", "milestone") if piece in block and absent[piece]]


def reading_of(record_text: Any) -> Optional[Dict[str, str]]:
    """The value a metric record states on its leading ``Current value:`` line, with the day and source it names; None when it holds none."""
    found = READING.search(str(record_text or ""))
    if not found:
        return None
    return {"value": found.group("value"), "as_of": found.group("as_of").strip(), "source": (found.group("source") or "").strip()}


def pick_solution(records: Mapping[str, Any], relevant_ids: Any) -> str:
    """The first relevant solution the records hold, else ''. Nothing is guessed from a name."""
    solutions = rows(records, "solutions")
    for solution_id in relevant_ids or ():
        if solution_id in solutions:
            return str(solution_id)
    return ""


def next_milestone(row: Mapping[str, Any]) -> Optional[str]:
    """The first milestone of a solution not marked met: its structured entries when it has them, else the lines of its milestones text."""
    entries = row.get("milestone_entries")
    if entries:
        for entry in entries:
            if not entry.get("met"):
                return str(entry.get("sentence") or "")
        return None
    for line in str(row.get("milestones") or "").split("\n"):
        if line.strip():
            return re.sub(r"^\s*\d+[.)]\s*", "", line).strip()
    return None


def metric_of(records: Mapping[str, Any], solution_id: str) -> str:
    """The solution's metric: its authoritative one, else the first metric that names the solution."""
    if not solution_id:
        return ""
    metrics = rows(records, "metrics")
    authoritative = str(rows(records, "solutions").get(solution_id, {}).get("authoritative_metric_id") or "")
    if authoritative in metrics:
        return authoritative
    for metric_id, row in metrics.items():
        if solution_id in ids_of(row.get("solution_ids")):
            return str(metric_id)
    return ""


def linked(row: Mapping[str, Any], column: str, table: Mapping[str, Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    for record_id in ids_of(row.get(column)):
        if record_id in table:
            return {"id": record_id, "name": str(table[record_id].get("name") or table[record_id].get("problem") or ""), "existing": True}
    return None


def only(table: Mapping[str, Mapping[str, Any]], chosen: Any) -> Optional[Dict[str, Any]]:
    """The record the caller chose, else the table's one record when it holds exactly one; with several and no choice nothing is guessed."""
    key = str(chosen) if chosen in table else (next(iter(table)) if len(table) == 1 else "")
    return {"id": key, "name": str(table[key].get("name") or table[key].get("problem") or ""), "existing": True} if key else None


def build_block(move: str, records: Mapping[str, Any], solution_id: str, draft: Mapping[str, Any]) -> Dict[str, Any]:
    """The structure block of one reply: each part from the records when they hold it, else from the draft marked ``existing: false``; a part the move does not
    use is absent."""
    wanted = PARTS[move]
    draft = draft if move in OFFERED else {}     # only a move that may offer proposes pieces; a review or a focus shows what is held, nothing made up
    solution_row = rows(records, "solutions").get(solution_id, {}) if solution_id else {}
    block: Dict[str, Any] = {"move": move}
    problem = linked(solution_row, "problem_ids", rows(records, "problems")) or only(rows(records, "problems"), draft.get("problem_id"))
    if "problem" in wanted:
        block["problem"] = problem
    if "ideal" in wanted:
        block["ideal"] = linked(solution_row, "ideal_ids", rows(records, "ideals")) or only(rows(records, "ideals"), draft.get("ideal_id"))
    if "solution" in wanted:
        name = draft.get("solution_name")
        block["solution"] = ({"id": solution_id, "name": str(solution_row.get("name") or ""), "existing": True} if solution_id
                             else ({"id": None, "name": str(name), "existing": False} if name else None))
    if "alternatives" in wanted:
        held = [{"id": key, "name": str(row.get("name") or ""), "existing": True} for key, row in rows(records, "implementations").items()
                if solution_id and row.get("solution_id") == solution_id]
        known = {normal(item["name"]) for item in held}
        fresh = []
        for item in draft.get("alternatives") or ():
            name = str(item.get("name") or "").strip()
            if name and normal(name) not in known and len(held) + len(fresh) < MAX_ALTERNATIVES:
                known.add(normal(name))
                fresh.append({"id": None, "name": name, "existing": False})
        block["alternatives"] = held + fresh
    if "metric" in wanted:
        metric_id = metric_of(records, solution_id)
        if metric_id:
            row = rows(records, "metrics")[metric_id]
            block["metric"] = {"id": metric_id, "name": str(row.get("name") or ""), "existing": True, "reading": reading_of(row.get("record"))}
        elif draft.get("metric") and draft["metric"].get("name"):
            block["metric"] = {"id": None, "name": str(draft["metric"]["name"]), "existing": False, "reading": None}
        else:
            block["metric"] = None
    if "milestone" in wanted:
        held_milestone = next_milestone(solution_row) if solution_row else None
        if held_milestone:
            block["milestone"] = {"sentence": held_milestone, "existing": True}
        elif draft.get("milestone") and move != "focus" and move != "review":
            block["milestone"] = {"sentence": str(draft["milestone"]), "existing": False}
        else:
            block["milestone"] = None
    return block


def build_offer(move: str, records: Mapping[str, Any], solution_id: str, block: Mapping[str, Any], draft: Mapping[str, Any], held: Any, declined: Any) -> Optional[Dict[str, Any]]:
    """At most one offer: the missing pieces of the block as ordered ensure-one additions. Nothing existing is edited, a held solution gets no milestone, and an
    offer whose key was declined before is not made again."""
    if move not in OFFERED:
        return None
    edits: List[Dict[str, Any]] = []
    pieces: List[str] = []
    solution = block.get("solution")
    solution_key = normal(solution["name"]) if solution else ""
    if solution and not solution["existing"]:
        fields = {"name": solution["name"]}
        problem, ideal = block.get("problem"), block.get("ideal")
        if problem:
            fields["problem_ids"] = problem["id"]
        if ideal:
            fields["ideal_ids"] = ideal["id"]
        edits.append({"kind": "record_add", "table": "solutions", "key": solution["name"], "fields": fields})
        pieces.append("solution")
    if solution:
        target = {"solution_id": solution["id"]} if solution["existing"] else {"solution_key": solution["name"]}
        new_alternatives = [item for item in block.get("alternatives") or () if not item["existing"]]
        descriptions = {normal(item.get("name")): str(item.get("description") or "") for item in draft.get("alternatives") or ()}
        for item in new_alternatives:
            edits.append({"kind": "record_add", "table": "implementations", "key": item["name"],
                          "fields": dict(target, name=item["name"], description=descriptions.get(normal(item["name"]), ""))})
        if new_alternatives:
            pieces.append("alternatives")
        metric = block.get("metric")
        if metric and not metric["existing"]:
            link = {"solution_ids": solution["id"]} if solution["existing"] else {"solution_key": solution["name"]}     # a metric names its solutions in a column of its own
            edits.append({"kind": "record_add", "table": "metrics", "key": metric["name"],
                          "fields": dict(link, name=metric["name"], record=str(draft["metric"].get("record") or ""))})
            pieces.append("metric")
        milestone = block.get("milestone")
        if milestone and not milestone["existing"] and solution_id not in set(held or ()):
            edits.append({"kind": "milestone_add", "target": solution["id"] or solution["name"], "key": milestone["sentence"],
                          "fields": {"metric": (metric or {}).get("id") or (metric or {}).get("name") or ""}})
            pieces.append("milestone")
    if not edits:
        return None
    key = "structure:" + (solution_id or solution_key) + ":" + ",".join(pieces)
    if key in set(declined or ()):
        return None
    return {"key": key, "pieces": pieces, "edits": edits}


@implementation("structure-in-conversation", "none")
class NoStructure:
    """The baseline: a reply makes no structure move, whatever the turn, so it has no block and no offer."""
    REQUIRES = ()

    def decide(self, turn: Mapping[str, Any]) -> Dict[str, Any]:
        return {"move": "none", "block": None, "offer": None}


@implementation("structure-in-conversation", "structure_move")
class StructureMove:
    """Builds the block the move calls for from the records first and the draft for what is missing, and at most one offer that keeps the missing pieces; a move
    of ``none`` (or one it does not know) leaves the reply plain."""
    REQUIRES = ()

    def decide(self, turn: Mapping[str, Any]) -> Dict[str, Any]:
        move = str(turn.get("move") or "none")
        if move not in PARTS:
            return {"move": "none", "block": None, "offer": None}
        records, draft = turn.get("records") or {}, turn.get("draft") or {}
        solution_id = pick_solution(records, turn.get("relevant_solution_ids"))
        block = build_block(move, records, solution_id, draft)
        return {"move": move, "block": block, "offer": build_offer(move, records, solution_id, block, draft, turn.get("held"), turn.get("declined"))}
