"""Two advisory judged checks of a reply that applied structure, kept apart from the metric's score: whether the six terms are used consistently, and whether the
reply stands on its own for someone who has never heard them. Each is a prompt the caller sends to a model at the tier it uses for a review step, and a parser
of the one JSON object the model answers; this module calls no model. Standard library only."""
import json
from typing import Any, Callable, Dict, Mapping

from hubofhubs.the_intelligence.critical_thinking.structure_in_conversation.terms import TERMS

CONSISTENT_QUESTIONS = ("each_term_has_its_one_meaning", "no_term_replaced_by_a_synonym", "no_term_is_a_bare_label_or_heading", "framework_is_not_the_point")
STANDS_ALONE_QUESTIONS = ("says_what_the_reply_is_for", "says_what_the_options_are", "says_how_to_tell_which_works", "says_the_next_step")


def consistency_prompt(reply: str, block: Mapping[str, Any]) -> str:
    """The prompt that judges the terms: each used in its one meaning, in a sentence that makes it clear, never a bare label, never swapped for a synonym."""
    meanings = "\n".join(f"- {term}: {meaning}" for term, meaning in TERMS)
    return ("You review one reply. The reply may use these six terms, each with one meaning:\n" + meanings + "\n\nStructure the reply was written from (JSON):\n"
            + json.dumps(block, sort_keys=True)[:1500] + "\n\nReply:\n" + reply[:3000] + "\n\nAnswer ONLY a JSON object with a boolean for each key: "
            + ", ".join(CONSISTENT_QUESTIONS) + ". A term that does not appear is not a failure. 'framework_is_not_the_point' is true when the reply never names a framework "
            "or explains the terms for their own sake.")


def stands_alone_prompt(reply: str) -> str:
    """The prompt a newcomer judge answers from the reply alone, knowing nothing of the terms."""
    return ("You are a person who has never heard of any framework. Read only this reply:\n" + reply[:3000] + "\n\nAnswer ONLY a JSON object with a boolean for each key: "
            + ", ".join(STANDS_ALONE_QUESTIONS) + ". Each is true only when the reply makes it clear to you in its own words.")


def parse(answer: str, keys: tuple) -> Dict[str, bool]:
    """The judge's booleans for ``keys`` (a key it did not answer is False), or all False when the answer holds no JSON object."""
    start, end = answer.find("{"), answer.rfind("}")
    try:
        data = json.loads(answer[start:end + 1]) if start >= 0 < end else {}
    except ValueError:
        data = {}
    return {key: data.get(key) is True for key in keys}


def advisory_checks(reply: str, block: Mapping[str, Any], ask: Callable[[str], str]) -> Dict[str, Any]:
    """Both advisory checks for one reply: ``ask`` sends a prompt to the caller's review-step model and returns its text. The shares are advice, never a score."""
    consistent = parse(ask(consistency_prompt(reply, block)), CONSISTENT_QUESTIONS)
    alone = parse(ask(stands_alone_prompt(reply)), STANDS_ALONE_QUESTIONS)
    return {"consistent_terms": consistent, "stands_alone": alone,
            "consistent_share": sum(consistent.values()) / len(consistent), "stands_alone_share": sum(alone.values()) / len(alone)}
