"""Depth for a piece of work that falls short of its own solution's metric: the check returns it, it is split into the sub-pieces its missing
requirements need, each sub-piece is done with its own sub-prompt and checked on its own requirement, and the parts are combined and checked
again against the parent's whole rubric, within the request's budget; a recombined text still short goes round again, up to ``rounds`` times.

The loop is generic: the consumer gives ``work`` (one piece in, its text out: a writing call with the piece's sub-prompt, or a sub-agent for long
work), ``check`` (the metric's own check of a text against a piece's requirements: ``met``, ``score`` from 0 to 1, ``missing`` and ``reason``;
never the writer) and, optionally, ``split`` (default: one sub-piece per missing requirement, each with the parent's prompt and only that
requirement) and ``combine`` (default: the earlier text, then each part under its requirement). A stronger tier is one option a consumer's
``work`` may take for a sub-piece; it is not the first fix. The text returned is the best-scoring one checked, never a combination that scored
below what it started from. Standard library."""
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

DEFAULT_BUDGET = {"calls": 16, "depth": 2, "width": 4, "rounds": 2}
SUB_PROMPT = ("## Context, for reference only (do not write the whole piece)\n{prompt}\n\n## Your part\nThe whole piece is: {goal}\n"
              "Write only the sentences that meet this one requirement, nothing else: {requirement}\nUse no em dashes.")


def default_split(item: Mapping[str, Any], checked: Mapping[str, Any]) -> List[Dict[str, Any]]:
    """One sub-piece per missing requirement, each with the parent's prompt and only that requirement."""
    missing = [str(r) for r in checked.get("missing") or []] or [str(r) for r in item.get("requirements") or []]
    return [{"goal": f"{item.get('goal', '')}: {req}", "requirements": [req], "solution_id": item.get("solution_id", ""),
             "prompt": SUB_PROMPT.format(prompt=item.get("prompt", ""), goal=item.get("goal", ""), requirement=req)} for req in missing]


def default_combine(item: Mapping[str, Any], base: str, parts: Sequence[Mapping[str, Any]]) -> str:
    """The earlier text first, then each part that was written, under the requirement it meets."""
    return "\n\n".join([base.strip()] + [f"{p['requirements'][0]}\n{p['text'].strip()}" for p in parts if str(p.get("text") or "").strip()]).strip()


def build_out(item: Mapping[str, Any], work: Callable[[Mapping[str, Any]], str], check: Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
              split: Optional[Callable[[Mapping[str, Any], Mapping[str, Any]], Sequence[Mapping[str, Any]]]] = None,
              combine: Optional[Callable[[Mapping[str, Any], str, Sequence[Mapping[str, Any]]], str]] = None,
              budget: Optional[Mapping[str, int]] = None, base: Optional[str] = None) -> Dict[str, Any]:
    """Do ``item`` (``goal``, ``requirements``, ``prompt``, ``solution_id``) to its metric with depth. ``base`` is a text already made (the one-call
    result), checked first; with none, ``work`` makes it. Returns ``text``, ``met``, ``before`` and ``after`` (the check's score of the first text and
    of the last), ``calls`` (work and check calls), ``levels`` used, ``tree`` (each level's parts and their checks) and ``stopped`` (why it ended)."""
    bound = {**DEFAULT_BUDGET, **dict(budget or {})}
    spent = {"calls": 0}

    def call(fn: Callable[..., Any], *args: Any) -> Any:
        spent["calls"] += 1
        return fn(*args)

    def deepen(piece: Mapping[str, Any], text: str, checked: Dict[str, Any], level: int, tree: List[Dict[str, Any]], rounds_left: int = 1) -> Dict[str, Any]:
        if checked.get("met") or level >= bound["depth"] or spent["calls"] >= bound["calls"]:
            why = "met" if checked.get("met") else ("depth" if level >= bound["depth"] else "budget")
            return {"text": text, "checked": checked, "stopped": why}
        parts = [dict(p) for p in (split or default_split)(piece, checked)]
        room = max((bound["calls"] - spent["calls"]) // 2, 0)       # each part costs a work call and a check
        kept, cut = parts[:room], parts[room:]
        if not kept:
            return {"text": text, "checked": checked, "stopped": "budget"}

        def one(part: Dict[str, Any]) -> Dict[str, Any]:
            made = str(call(work, part) or "")
            below: List[Dict[str, Any]] = []
            done = deepen(part, made, dict(call(check, made, part) or {}), level + 1, below)
            return {**part, "text": done["text"], "checked": done["checked"], "below": below}
        with ThreadPoolExecutor(max_workers=max(1, min(bound["width"], len(kept)))) as pool:
            finished = list(pool.map(one, kept))
        tree.append({"level": level + 1, "parts": [{"goal": p["goal"], "met": p["checked"].get("met"), "score": p["checked"].get("score")} for p in finished],
                     "cut": [p["goal"] for p in cut]})
        combined = (combine or default_combine)(piece, text, finished)
        rechecked = dict(call(check, combined, piece) or {})
        if float(rechecked.get("score") or 0) < float(checked.get("score") or 0):
            combined, rechecked = text, checked       # a combination that scores below what it started from is not kept
        if not rechecked.get("met") and rounds_left > 1 and not cut and spent["calls"] < bound["calls"]:
            return deepen(piece, combined, rechecked, level, tree, rounds_left - 1)      # still short: the recombined text goes round once more
        return {"text": combined, "checked": rechecked, "stopped": "met" if rechecked.get("met") else ("budget" if cut else "rechecked")}

    first = base if base is not None else str(call(work, item) or "")
    before = dict(call(check, first, item) or {})
    tree: List[Dict[str, Any]] = []
    done = deepen(item, first, before, 0, tree, int(bound["rounds"]))
    return {"text": done["text"], "met": bool(done["checked"].get("met")), "before": before.get("score"), "after": done["checked"].get("score"),
            "calls": spent["calls"], "levels": len(tree), "tree": tree, "stopped": done["stopped"]}
