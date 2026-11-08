"""The learning loop of Decision Check: found mistakes become short known-mistake lines that a check's prompt carries, and a line stays only while the check's metric says it pays.

1. ``Mistake`` is one structured record: the check or view that failed (``check_id``), the input slice it saw, the wrong output, the right output and where it came from (``source``: an eval
   failure, a person's correction, or an adjudication that overruled a view, see ``overruled_mistakes``). ``MistakeLog`` appends them to a JSON lines file the consumer owns.
2. ``distill`` is the offline step (cheap tier, in batches, never per request): one call per batch groups the records of one check into short lines with one neutral example each; code keeps a line
   only when the records it names exist and are at least ``min_support``, and counts the frequency from them.
3. ``LineBook.lines_for`` gives a check its adopted lines, most frequent first, cut to a token cap; the arm ``agreement_with_known_mistakes`` injects them and adds a twin view.
4. ``adopt`` takes a candidate line only when the score of the check on held-out cases strictly improves with it, ``retire`` drops an adopted line whose removal does not lower that score,
   and every change is a numbered version in the book with the scores that decided it. The score function and the cases are the consumer's; held-out cases that a record came from are never used.

The hub holds the mechanism only: a consumer's records, lines and book are its own data (per user or team where they are private). Standard library only; no environment read."""
import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from hubofhubs.the_intelligence.critical_thinking.decision_check.checks import parse_json

EVAL_FAILURE, CORRECTION, OVERRULED = "eval_failure", "correction", "overruled"
CONFIRMED_FAILURE = "confirmed_failure"     # a reply span most independent confirmations found failing, which a repair removed instead of rewriting
SOURCES = (EVAL_FAILURE, CORRECTION, OVERRULED, CONFIRMED_FAILURE)
ADOPTED, RETIRED = "adopted", "retired"


@dataclass(frozen=True)
class Mistake:
    """One found mistake. ``case_id`` names the evaluation case it came from, when it did, so a held-out set never contains the case a line was learned from."""
    id: str
    check_id: str
    input_slice: str
    wrong: str
    right: str
    source: str
    case_id: str = ""
    at: str = ""


def new_mistake(check_id: str, input_slice: str, wrong: str, right: str, source: str, case_id: str = "", at: str = "") -> Mistake:
    """A mistake with an id made from what it says, so the same mistake recorded twice is one record."""
    if source not in SOURCES:
        raise ValueError(f"source {source!r} is not one of {SOURCES}")
    digest = hashlib.sha1(json.dumps([check_id, input_slice, wrong, right], sort_keys=True).encode()).hexdigest()[:12]
    return Mistake("m-" + digest, check_id, input_slice, wrong, right, source, case_id, at)


def overruled_mistakes(decision: Mapping[str, Any], binding: Any, at: str = "") -> List[Mistake]:
    """The mistakes an adjudication found: each view that picked something other than the adjudicated pick, with the evidence slice it saw."""
    if decision.get("outcome") != "adjudicated":
        return []
    slices = {v["id"] if isinstance(v, Mapping) else v.id: (v["evidence"] if isinstance(v, Mapping) else v.evidence) for v in getattr(binding, "views", None) or binding.get("views", ())}
    wrong_by = {row["id"]: row["pick"] for row in decision.get("views", ()) if row.get("pick")}
    return [new_mistake(view_id, slices.get(view_id, ""), wrong_by.get(view_id, ""), str(decision.get("pick")), OVERRULED, at=at)
            for view_id in decision.get("overruled", ()) if view_id in slices]


class MistakeLog:
    """An append-only JSON lines file of mistakes. The same mistake is stored once."""

    def __init__(self, path: Any):
        self.path = Path(path)

    def read(self, check_id: Optional[str] = None) -> List[Mistake]:
        if not self.path.exists():
            return []
        rows = [Mistake(**json.loads(line)) for line in self.path.read_text().splitlines() if line.strip()]
        return [m for m in rows if check_id is None or m.check_id == check_id]

    def add(self, mistake: Mistake) -> bool:
        """Stores ``mistake``; false when it was already there."""
        if any(m.id == mistake.id for m in self.read()):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as handle:
            handle.write(json.dumps(asdict(mistake), sort_keys=True) + "\n")
        return True


@dataclass
class Line:
    """A distilled known-mistake line: one rule, one neutral ``example`` (input, wrong, right), how many records it rests on and which."""
    id: str
    check_id: str
    text: str
    example: Mapping[str, str]
    frequency: int
    source_ids: Sequence[str]
    case_ids: Sequence[str] = ()
    status: str = "candidate"
    adopted_in: int = 0
    retired_in: int = 0


@dataclass
class LineBook:
    """The lines of every check and the numbered versions that changed them."""
    lines: List[Line] = field(default_factory=list)
    versions: List[Dict[str, Any]] = field(default_factory=list)

    def lines_for(self, check_id: str, token_cap: int = 300) -> List[str]:
        """The adopted lines of a check, most frequent first, as many as fit in ``token_cap`` tokens."""
        out, spent = [], 0
        for line in sorted((l for l in self.lines if l.check_id == check_id and l.status == ADOPTED), key=lambda l: (-l.frequency, l.id)):
            cost = (len(line.text) + 3) // 4 + 1
            if spent + cost > token_cap:
                break
            out.append(line.text)
            spent += cost
        return out

    def adopted(self, check_id: str) -> List[Line]:
        return [l for l in self.lines if l.check_id == check_id and l.status == ADOPTED]

    def record(self, check_id: str, change: str, before: float, after: float, line_ids: Sequence[str], at: str) -> int:
        number = len(self.versions) + 1
        self.versions.append({"version": number, "at": at, "check_id": check_id, "change": change, "score_before": before, "score_after": after, "line_ids": list(line_ids)})
        return number

    def to_dict(self) -> Dict[str, Any]:
        return {"lines": [asdict(l) for l in self.lines], "versions": self.versions}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "LineBook":
        return cls([Line(**l) for l in data.get("lines", ())], list(data.get("versions", ())))

    def save(self, path: Any) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(json.dumps(self.to_dict(), indent=1, sort_keys=True) + "\n")

    @classmethod
    def load(cls, path: Any) -> "LineBook":
        return cls.from_dict(json.loads(Path(path).read_text())) if Path(path).exists() else cls()


DISTILL_PROMPT = """Below are mistakes one small check made. Each has the input slice it saw, the wrong output and the right output. Group the mistakes that share a cause. For each group of at least {min_support} mistakes write:
- one short rule, one sentence, written as an instruction to the check, with no names, ids or private details, that would have prevented them;
- one neutral invented example (input, wrong, right) that shows the mistake without using any real content;
- the ids of the mistakes in the group.

Mistakes:
{listing}

Reply with JSON only: {{"lines": [{{"line": "<the rule>", "example": {{"input": "...", "wrong": "...", "right": "..."}}, "records": ["<mistake id>"]}}]}}. Use at most {max_lines} lines. Do not use em dashes."""


def distill(records: Sequence[Mistake], ask: Callable[[str], str], max_lines: int = 5, min_support: int = 2, batch: int = 40) -> List[Line]:
    """Candidate lines for the checks in ``records``, offline: one call per batch of up to ``batch`` records of one check. A line stands only on records that exist and are at least ``min_support``;
    a line the same rule in two batches merges by its text. Most frequent first."""
    by_id = {m.id: m for m in records}
    found: Dict[tuple, Line] = {}
    for check_id in sorted({m.check_id for m in records}):
        mine = [m for m in records if m.check_id == check_id]
        for start in range(0, len(mine), batch):
            chunk = mine[start:start + batch]
            listing = "\n".join(f"[{m.id}] input: {m.input_slice[:400]!r} | wrong: {m.wrong[:200]!r} | right: {m.right[:200]!r}" for m in chunk)
            rows = parse_json(ask(DISTILL_PROMPT.format(min_support=min_support, listing=listing, max_lines=max_lines))).get("lines")
            for row in rows if isinstance(rows, list) else ():
                if not isinstance(row, dict) or not isinstance(row.get("line"), str) or not row["line"].strip():
                    continue
                ids = [i for i in dict.fromkeys(row.get("records") or ()) if i in by_id and by_id[i].check_id == check_id and i in {m.id for m in chunk}]
                example = row.get("example") if isinstance(row.get("example"), dict) else {}
                if len(ids) < min_support or not all(isinstance(example.get(k), str) for k in ("input", "wrong", "right")):
                    continue
                key = (check_id, " ".join(row["line"].split()).casefold())
                old = found.get(key)
                merged = list(dict.fromkeys([*(old.source_ids if old else ()), *ids]))
                found[key] = Line("l-" + hashlib.sha1(repr(key).encode()).hexdigest()[:10], check_id, row["line"].strip(), {k: example[k] for k in ("input", "wrong", "right")},
                                  len(merged), merged, [by_id[i].case_id for i in merged if by_id[i].case_id])
    return sorted(found.values(), key=lambda l: (-l.frequency, l.id))


Scorer = Callable[[Sequence[str], Sequence[Mapping[str, Any]]], float]


def held_out_for(candidate: Line, cases: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    """The cases a line may be judged on: never one it was learned from."""
    return [c for c in cases if c.get("id") not in set(candidate.case_ids)]


def adopt(book: LineBook, check_id: str, candidates: Sequence[Line], held_out: Sequence[Mapping[str, Any]], score: Scorer, at: str = "", min_gain: float = 0.0) -> Dict[str, Any]:
    """Takes each candidate line (most frequent first) only when ``score`` of the check on the held-out cases strictly rises by more than ``min_gain`` with it added to the lines already adopted.
    A rejected candidate is not stored. Returns the lines taken, the scores and the version number (0 when nothing changed)."""
    current = book.lines_for(check_id, 10 ** 6)
    base = best = score(current, held_out)
    taken = []
    for candidate in sorted(candidates, key=lambda l: -l.frequency):
        if candidate.check_id != check_id or candidate.status == ADOPTED:
            continue
        cases = held_out_for(candidate, held_out)
        if not cases:
            continue
        before, after = score(current, cases), score([*current, candidate.text], cases)
        if after > before + min_gain:
            current = [*current, candidate.text]
            candidate.status = ADOPTED
            taken.append(candidate)
            book.lines.append(candidate)
            best = score(current, held_out)
    number = book.record(check_id, "adopt", base, best, [l.id for l in taken], at) if taken else 0
    for line in taken:
        line.adopted_in = number
    return {"taken": [l.id for l in taken], "score_before": base, "score_after": best, "version": number}


def retire(book: LineBook, check_id: str, held_out: Sequence[Mapping[str, Any]], score: Scorer, at: str = "") -> Dict[str, Any]:
    """Retires each adopted line whose removal does not lower the score on the held-out cases: a line that stopped paying. One version records the change."""
    base = score(book.lines_for(check_id, 10 ** 6), held_out)
    retired = []
    for line in list(book.adopted(check_id)):
        without = [l.text for l in book.adopted(check_id) if l is not line]
        if score(without, held_out) >= score([l.text for l in book.adopted(check_id)], held_out):
            line.status = RETIRED
            retired.append(line)
    after = score(book.lines_for(check_id, 10 ** 6), held_out)
    number = book.record(check_id, "retire", base, after, [l.id for l in retired], at) if retired else 0
    for line in retired:
        line.retired_in = number
    return {"retired": [l.id for l in retired], "score_before": base, "score_after": after, "version": number}
