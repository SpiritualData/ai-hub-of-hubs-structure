"""Choosing an approach, a step of Critical Thinking: several distinct ways to do a piece of work are proposed, and the one that best meets the solution's
requirements is picked.

Each view is one cheap call with its own wording of what to propose (the most direct way, the way that reuses what already exists, the way a careful
specialist would take), run in parallel. The approaches are deduplicated by their normalised name. With fewer than two distinct approaches the one is
returned and no picking call is made. Otherwise ONE picking call sees the approaches unlabelled, in an order shuffled deterministically from the frame (so the
first proposed does not win by position), and the requirements, and answers the index that would best meet them. An answer that is not an index falls back to the
first valid approach. Standard library plus the hub."""
import hashlib
import random
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from hubofhubs.the_intelligence.critical_thinking.decision_check.checks import parse_json, run_parallel

#: Each view is forced along its own dimension. Three views asked the same open question return the recorded approach three times in other words (seen
#: live), which is no choice at all: so one view states the recorded way concretely, one builds from the hardest requirement, one changes the form.
DEFAULT_VIEWS = (
    "State the way already recorded for this work, made concrete for these requirements (when no way is recorded, the most direct way).",
    "Find the requirement that is hardest to meet here and name it. Propose a way built around meeting that one first, which therefore differs from the "
    "recorded way in what is done first and what is left out.",
    "Propose a way that changes the form of the work: a different unit, order, grouping or source for the same result, chosen so that the gap the "
    "recorded way leaves is closed and not worked around.",
)

PROPOSE_PROMPT = """The work: {frame}

What the result must meet:
{requirements}

{instruction}

A rewording of the recorded way is worthless unless the instruction above asks for the recorded way: say in "how" the one thing this way does that the
recorded way does not. Reply with JSON only: {{"name": "<2 to 5 words naming the approach>", "how": "<2 to 3 sentences: how the work is done this way>",
"disadvantage": "<its main weakness against these requirements, one sentence>"}}.
Use only the work as given: no fact about the subject that it does not state. Do not use em dashes."""

PICK_PROMPT = """The work: {frame}

What the chosen approach must meet:
{requirements}

The approaches (unlabelled, in no order of merit):
{listing}

Which one would best meet the requirements? Reply with JSON only: {{"index": <the number of that approach>, "reason": "<one line>"}}. Do not use em dashes."""

PLACEHOLDERS = frozenset({"", "none", "n/a", "na", "tbd", "todo", "unknown", "...", "<name>", "<how>"})


def clean(value: Any) -> str:
    text = " ".join(str(value or "").replace("—", ",").split())
    return "" if text.casefold().strip(" .<>") in PLACEHOLDERS else text


def valid(raw: Any) -> Optional[Dict[str, str]]:
    """The approach a view's reply holds (``name``, ``how``, ``disadvantage``), or None when the name or how is missing."""
    data = parse_json(raw)
    out = {key: clean(data.get(key)) for key in ("name", "how", "disadvantage")}
    return out if out["name"] and out["how"] else None


def normalised(name: str) -> str:
    return " ".join("".join(c if c.isalnum() else " " for c in name.casefold()).split())


def choose_approach(frame: str, requirements: Sequence[str], decide: Callable[[str], str], views: Sequence[str] = DEFAULT_VIEWS,
                    width: int = 3) -> Dict[str, Any]:
    """``{"chosen": {name, how, disadvantage}, "alternatives": [the others], "calls": n, "reason": str}``; ``chosen`` is None when no view gave a valid approach."""
    listed = "\n".join(f"- {r}" for r in requirements) or "- (none stated)"
    jobs = [(lambda instruction=instruction: decide(PROPOSE_PROMPT.format(frame=frame, instruction=instruction, requirements=listed))) for instruction in views]
    replies = run_parallel(jobs, width)
    calls = len(jobs)
    found: List[Dict[str, str]] = []
    seen = set()
    for reply in replies:
        approach = valid(reply)
        if approach is not None and normalised(approach["name"]) not in seen:
            seen.add(normalised(approach["name"]))
            found.append(approach)
    if len(found) < 2:
        return {"chosen": found[0] if found else None, "alternatives": [], "calls": calls, "reason": ""}
    order = list(range(len(found)))
    random.Random(int(hashlib.sha1(frame.encode("utf-8")).hexdigest()[:8], 16)).shuffle(order)
    listing = "\n".join(f"{n}. {found[i]['name']}: {found[i]['how']} Weakness: {found[i]['disadvantage'] or 'not stated'}" for n, i in enumerate(order, 1))
    data = parse_json(decide(PICK_PROMPT.format(frame=frame, requirements=listed, listing=listing)))
    calls += 1
    index = data.get("index")
    answered = isinstance(index, int) and not isinstance(index, bool) and 1 <= index <= len(order)
    picked = order[index - 1] if answered else 0
    return {"chosen": found[picked], "alternatives": [a for i, a in enumerate(found) if i != picked], "calls": calls,
            "reason": clean(data.get("reason")) if answered else ""}
