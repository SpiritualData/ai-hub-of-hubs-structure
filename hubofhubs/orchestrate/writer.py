"""The Response Writer: writes what the Mind outputs for its reader from the results of the delegated pieces, to the quality profile that
applies. Each arm takes the results (``text``, ``items`` with their sources, and ``refused`` or ``error`` when a worker did not deliver)
and returns the text. A piece that was refused or failed is said so plainly, never smoothed over. Standard library plus the hub and ``esoi``."""
from typing import Any, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi.assemble import Lazy

from ..seats import ModelPlumbing

REFUSALS = {"authority": "was not done: it needs authority this request does not carry",
            "budget": "was not done: the budget for this request was spent",
            "cancelled": "was not done: the request was cancelled"}


def said(result: Mapping[str, Any]) -> str:
    """What one result says for itself: its text, or why the piece was not done."""
    if result.get("refused"):
        return f"{result.get('piece', 'a step')} {REFUSALS.get(result['refused'], 'was not done')}"
    if result.get("error"):
        return f"{result.get('piece', 'a step')} failed: {result['error']}"
    return str(result.get("text") or "").strip()


def sources_of(results: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[str, Dict[str, Any]] = {}
    for result in results:
        for item in result.get("items") or ():
            if item.get("url"):
                seen.setdefault(item["url"], item)
    return list(seen.values())


@implementation("response-writer", "cited_results")
class CitedResults:
    """The results in order, one paragraph each, then the sources they came from, each by its title and link. Nothing is added that a
    result did not say, so every link in the response is one the evidence holds."""
    REQUIRES = ()     # no model

    def write(self, results: Sequence[Mapping[str, Any]], profile: Optional[Any] = None) -> str:
        paragraphs = [said(r) for r in results if said(r)]
        cited = sources_of(results)
        if cited:
            paragraphs.append("Sources:\n" + "\n".join(f"- {i.get('title') or i['url']}: {i['url']}" for i in cited))
        return "\n\n".join(paragraphs)


PROMPT = """Write the reply to the request from the material below and nothing else. Say what a step could not do plainly. When a claim comes
from a source, give its link as written in the material. Keep it as short as the request needs. Do not use em dashes.

Quality criteria for this reader: {criteria}

Material:
{material}
"""


@implementation("response-writer", "model_synthesis")
class ModelSynthesis:
    """One model call writes the reply from the results, under the profile's criteria. It costs a call and can add words the results did
    not say, which Response Quality then judges."""
    REQUIRES = ()     # the model comes through Model Plumbing
    PAID = True

    def __init__(self, plumbing: Lazy[ModelPlumbing]):
        self.plumbing = plumbing

    def write(self, results: Sequence[Mapping[str, Any]], profile: Optional[Any] = None) -> str:
        material = "\n\n".join(said(r) for r in results if said(r))
        for item in sources_of(results):
            material += f"\nSource: {item.get('title', '')} {item['url']}"
        criteria = "; ".join(f"{c.name} ({c.meaning})" for c in getattr(profile, "criteria", ())) or "helpful and faithful to the material"
        return self.plumbing.ask(PROMPT.format(criteria=criteria, material=material), "cheap")
