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

DEFAULT_VIEWS = (
    "Propose the most direct way to do this work: the fewest steps from where things stand to the result.",
    "Propose the way that reuses the most of what already exists, and adds the least that is new.",
    "Propose the way a careful specialist in this kind of work would take, one that guards against the usual ways such work goes wrong.",
)

PROPOSE_PROMPT = """The work: {frame}

{instruction}

Reply with JSON only: {{"name": "<2 to 5 words naming the approach>", "how": "<2 to 3 sentences: how the work is done this way>", "disadvantage": "<its main weakness, one sentence>"}}.
Use only the work as given. Do not use em dashes."""

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
    jobs = [(lambda instruction=instruction: decide(PROPOSE_PROMPT.format(frame=frame, instruction=instruction))) for instruction in views]
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
    data = parse_json(decide(PICK_PROMPT.format(frame=frame, requirements="\n".join(f"- {r}" for r in requirements) or "- (none stated)", listing=listing)))
    calls += 1
    index = data.get("index")
    answered = isinstance(index, int) and not isinstance(index, bool) and 1 <= index <= len(order)
    picked = order[index - 1] if answered else 0
    return {"chosen": found[picked], "alternatives": [a for i, a in enumerate(found) if i != picked], "calls": calls,
            "reason": clean(data.get("reason")) if answered else ""}
