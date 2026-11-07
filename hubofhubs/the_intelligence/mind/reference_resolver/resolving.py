"""Resolve a reference: the arms of the one seat that says which candidate a phrase refers to, or abstains.

``exact_match`` matches by id, by the whole name or an alias, or by whole words of a name (a first name, "Post B" for "Post B on video"), and abstains when none matches or
more than one does. ``model_judged`` shows a model the phrase and the candidates and takes its answer only when it names one candidate offered, or says none; an answer outside the list
raises ``ReferenceNotSettled`` and is never repaired. ``shared_words`` matches the candidate that shares the most words with the phrase and never abstains while any word is shared: the way
references were once settled, kept as the bound that shows what abstaining is worth. Standard library plus the hub and ``esoi``."""
import json
import re
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from esoi import implementation
from esoi import Lazy

from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing

#: Words that carry no reference on their own.
FILLER = frozenset("a an and at by for from in my of on our the this that to with goal goals post posts item".split())
NONE = "NONE"

PROMPT = """A phrase refers to at most one of these candidates. The phrase:
{phrase}

Candidates (id | name | text):
{listing}

Which candidate is the very same thing the phrase refers to? A candidate that only shares a topic or some words with the phrase is not the same thing. Reply with JSON only:
{{"id": "<that candidate's id exactly as listed, or {none} when none is the same thing>"}}. Do not use em dashes."""


class ReferenceNotSettled(ValueError):
    """The arm could not settle the reference: the model's reply was not a candidate offered and not NONE."""


def words_of(text: Any) -> List[str]:
    """The lower case words of ``text`` without the filler words."""
    return [w for w in re.findall(r"[a-z0-9]+", str(text or "").casefold()) if w not in FILLER]


def squash(text: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(text or "").casefold()))


def abstain(reason: str) -> Dict[str, str]:
    return {"outcome": "abstain", "id": "", "reason": reason}


def matched(candidate: Mapping[str, Any], reason: str) -> Dict[str, str]:
    return {"outcome": "match", "id": str(candidate.get("id")), "reason": reason}


def names_of(candidate: Mapping[str, Any]) -> List[str]:
    return [str(candidate.get("name") or ""), *[str(a) for a in candidate.get("aliases") or ()]]


@implementation("resolve-a-reference", "exact_match")
class ExactMatch:
    """Settles a reference by its id, its whole name or alias, or whole words of a name; two candidates that fit, or none, is an abstain. No model call."""
    REQUIRES = ()     # nothing

    def resolve(self, phrase: str, candidates: Sequence[Mapping[str, Any]], context: Optional[Mapping[str, Any]] = None,
                ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        want = squash(phrase)
        if not want:
            return abstain("the phrase names nothing")
        by_id = [c for c in candidates if squash(c.get("id")) == want]
        if len(by_id) == 1:
            return matched(by_id[0], "the phrase is the candidate's id")
        whole = [c for c in candidates if want in {squash(n) for n in names_of(c) if n}]
        if len(whole) == 1:
            return matched(whole[0], "the phrase is the candidate's whole name")
        if len(whole) > 1:
            return abstain("more than one candidate has that name")
        wanted = set(words_of(phrase))
        if not wanted:
            return abstain("the phrase holds no word that names anything")
        parts = [c for c in candidates if any(wanted <= set(words_of(n)) for n in names_of(c) if n)]
        if len(parts) == 1:
            return matched(parts[0], "every word of the phrase is a word of the candidate's name")
        return abstain("more than one candidate fits the phrase" if parts else "no candidate holds every word of the phrase")


@implementation("resolve-a-reference", "model_judged")
class ModelJudged:
    """One model call is shown the phrase and the candidates and says which one is the same thing, or none. Reads meaning where the words differ ("the Friday video" for "Post B"); an answer that
    is not a candidate offered raises. Costs a call, and a wrong "same" is the harm to guard against: the prompt says a shared topic or word is not sameness."""
    REQUIRES = ()     # the model comes through Model Plumbing
    PAID = True

    def __init__(self, plumbing: Lazy[ModelPlumbing], tier: str = "cheap"):
        self.plumbing, self.tier = plumbing, tier

    def resolve(self, phrase: str, candidates: Sequence[Mapping[str, Any]], context: Optional[Mapping[str, Any]] = None,
                ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        if not candidates:
            return abstain("there are no candidates")
        listing = "\n".join(f"{c.get('id')} | {c.get('name') or ''} | {str(c.get('text') or '')[:200]}" for c in candidates)
        prompt = PROMPT.format(phrase=str(phrase).strip()[:800], listing=listing, none=NONE)
        raw = ask(prompt) if ask is not None else self.plumbing.ask(prompt, self.tier)
        text = str(raw or "").strip()
        start, end = text.find("{"), text.rfind("}")
        try:
            data = json.loads(text[start:end + 1]) if start >= 0 and end > start else {}
        except ValueError as error:
            raise ReferenceNotSettled(f"the reply is not JSON: {error}") from error
        given = data.get("id") if isinstance(data, dict) else None
        chosen = given.strip() if isinstance(given, str) else ""
        if chosen.upper() == NONE:
            return abstain("the model found none of the candidates to be the same thing")
        found = [c for c in candidates if str(c.get("id")) == chosen]
        if len(found) != 1:
            raise ReferenceNotSettled(f"the reply names no candidate offered: {data!r}")
        return matched(found[0], "the model judged it the same thing")


@implementation("resolve-a-reference", "shared_words")
class SharedWords:
    """The candidate that shares the most words with the phrase wins, the first when tied, and it abstains only when no word is shared. The old way, and the bound: it matches look-alikes."""
    REQUIRES = ()     # nothing

    def resolve(self, phrase: str, candidates: Sequence[Mapping[str, Any]], context: Optional[Mapping[str, Any]] = None,
                ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]:
        wanted = set(words_of(phrase))
        scored = [(len(wanted & set(words_of(" ".join(names_of(c))))), c) for c in candidates]
        best = max(scored, key=lambda pair: pair[0], default=(0, None))
        return matched(best[1], "it shares the most words with the phrase") if best[0] > 0 else abstain("no candidate shares a word with the phrase")
