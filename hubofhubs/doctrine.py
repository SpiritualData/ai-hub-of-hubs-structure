"""Situational doctrine: a prompt carries only the rules that apply to the situation it is built for.

A rule is data: an id, its text and ``applies_when``, a declarative condition over a situation. A situation is a plain
mapping of facts the consumer already holds in structured form (a mode, a verdict, a flag), never words read out of a
model's own output. ``assemble_doctrine`` takes the rules in prompt order and a situation and returns the ordered text, its
estimated token count and which rule ids went in and which stayed out.

A condition is ``{fact: allowed}`` (all facts must match; ``allowed`` is one value or a list of values) or a list of such
mappings (any one may match). An empty condition always applies. A fact the situation does not know (missing or None)
matches, so a rule is left out only on a positive reason: unknown fails open and the prompt keeps the rule.

The hub ships no rules: wording is the consumer's. Standard library only, no environment reads, no consumer import.
"""
from dataclasses import dataclass
from math import ceil
from typing import Any, List, Mapping, Sequence, Tuple, Union

Condition = Union[Mapping[str, Any], Sequence[Mapping[str, Any]]]


@dataclass(frozen=True)
class Rule:
    """One rule of a prompt: ``text`` is included when ``applies_when`` holds for the situation."""
    id: str
    text: str
    applies_when: Condition = ()


@dataclass(frozen=True)
class Doctrine:
    """The assembled prompt text with its estimated size and which rules it holds."""
    text: str
    tokens: int
    included: Tuple[str, ...]
    excluded: Tuple[str, ...]


def clauses(rule: Rule) -> List[Mapping[str, Any]]:
    """The rule's condition as a list of alternatives (empty when it always applies)."""
    cond = rule.applies_when
    return [cond] if isinstance(cond, Mapping) else list(cond)


def matches(clause: Mapping[str, Any], situation: Mapping[str, Any]) -> bool:
    for fact, allowed in clause.items():
        value = situation.get(fact)
        options = allowed if isinstance(allowed, (list, tuple, set, frozenset)) else (allowed,)
        if value is not None and value not in options:
            return False
    return True


def applies(rule: Rule, situation: Mapping[str, Any]) -> bool:
    alternatives = [c for c in clauses(rule) if c]
    return not alternatives or any(matches(c, situation) for c in alternatives)


def estimate_tokens(text: str, chars_per_token: float = 3.5) -> int:
    """A tokenizer-free estimate: characters over ``chars_per_token``, rounded up."""
    return ceil(len(text) / chars_per_token) if text else 0


def assemble_doctrine(rules: Sequence[Rule], situation: Mapping[str, Any], *, chars_per_token: float = 3.5) -> Doctrine:
    """The rules that apply to ``situation``, joined in the order given, with their size and the ids in and out."""
    chosen = [r for r in rules if applies(r, situation)]
    text = "".join(r.text for r in chosen)
    kept = {r.id for r in chosen}
    return Doctrine(text, estimate_tokens(text, chars_per_token), tuple(r.id for r in chosen),
                    tuple(r.id for r in rules if r.id not in kept))


def check_rules(rules: Sequence[Rule], facts: Sequence[str]) -> List[str]:
    """Problems in a rule set: an empty or repeated id, or a condition naming a fact the situation does not declare."""
    problems, seen = [], set()
    for r in rules:
        if not r.id or r.id in seen:
            problems.append(f"{r.id or '(empty)'}: id is empty or repeated")
        seen.add(r.id)
        problems += [f"{r.id}: unknown fact {fact!r}" for c in clauses(r) for fact in c if fact not in facts]
    return problems
