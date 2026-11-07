"""Takes the em dash out of text a person reads or that the AI writes into their data, and the arm that holds a response to that rule.

Brand rule of many writers: no em dash anywhere a reader sees. A prompt line asking the model to avoid it leaks (a cheap model writes one in about one reply in ten), so
the code does it once, at the places text leaves the AI. It reads punctuation only, never meaning:

* a PAIR of dashes in one sentence wraps an aside, so it becomes parentheses;
* one dash after a short label on a bullet line becomes a colon;
* between two numbers it is a range, written "to";
* a dash that starts or ends a line is dropped;
* any other single dash becomes a comma (never a hyphen glued to the words).
"""
from __future__ import annotations

import re
from typing import Any, Optional, Sequence

from esoi import implementation

EM_DASHES = "\u2014\u2015"
DASH_CLASS = f"[{EM_DASHES}]"
#: A dash with the spaces around it (or none) that sits inside a line.
SPACED = re.compile(rf"[ \t]*{DASH_CLASS}[ \t]*")
RANGE = re.compile(rf"(?<=\d)[ \t]*{DASH_CLASS}[ \t]*(?=\d)")
LINE_START = re.compile(rf"(?m)^([ \t]*(?:[-*•][ \t]+)?){DASH_CLASS}[ \t]*")
LINE_END = re.compile(rf"[ \t]*{DASH_CLASS}[ \t]*$", re.M)
#: A bullet's one or two word label then a spaced dash (a bullet that reads label, dash, text).
LABEL = re.compile(rf"(?m)^([ \t]*[-*•][ \t]+[A-Za-z0-9][^\s.,;:!?{EM_DASHES}]*(?:[ \t]+[^\s.,;:!?{EM_DASHES}]+){{0,1}})[ \t]+{DASH_CLASS}[ \t]+(?=\S)")
SENTENCE_END = re.compile(r"[.!?\n]")


def pair_in_sentence(match: "re.Match[str]") -> str:
    return f"({match.group(1).strip()})"


PAIR = re.compile(rf"[ \t]*{DASH_CLASS}[ \t]*([^{EM_DASHES},;.!?\n]{{2,80}}?)[ \t]*{DASH_CLASS}[ \t]*")


def replace_pairs(text: str) -> str:
    """Two dashes in one sentence wrap an aside: parentheses around it, a space before it (none when it opens the line)."""
    def wrap(match: "re.Match[str]") -> str:
        start = match.start()
        lead = re.split(r"[.!?\n]", text[:start])[-1]
        if len(lead.split()) < 2:
            return match.group(0)    # a dash after one or two words is a pause, not an aside: the comma rule below takes it
        before = "" if start == 0 or text[start - 1] in "\n(" else " "
        return f"{before}({match.group(1).strip()}) "
    out, last = [], 0
    for match in PAIR.finditer(text):
        out.append(text[last:match.start()])
        out.append(wrap(match))
        last = match.end()
    out.append(text[last:])
    joined = "".join(out)
    return re.sub(r"\) ([,.;:!?)])", r")\1", joined)


def remove_em_dashes(text: str) -> str:
    """``text`` without any em dash, using the punctuation its context needs. Text with no em dash is returned unchanged."""
    if not isinstance(text, str) or not any(d in text for d in EM_DASHES):
        return text
    out = RANGE.sub(" to ", text)
    out = LINE_START.sub(r"\1", out)
    out = LINE_END.sub("", out)
    out = replace_pairs(out)
    out = LABEL.sub(lambda m: m.group(1) + ": ", out)
    # Any dash left is a single break inside a sentence: a comma, unless a comma or other stop already stands there.
    out = re.sub(rf"[ \t]*[,;:]?[ \t]*{DASH_CLASS}[ \t]*(?=[,.;:!?])", "", out)
    out = SPACED.sub(", ", out)
    return re.sub(r",[ \t]*,", ",", out)


def clean_value(value: Any, skip_keys: frozenset = frozenset()) -> Any:
    """``value`` with every string in it passed through ``remove_em_dashes`` (lists and dicts are walked; ids and other keys named
    in ``skip_keys`` are left alone)."""
    if isinstance(value, str):
        return remove_em_dashes(value)
    if isinstance(value, list):
        return [clean_value(v, skip_keys) for v in value]
    if isinstance(value, dict):
        return {k: (v if k in skip_keys or str(k).endswith("id") else clean_value(v, skip_keys)) for k, v in value.items()}
    return value


@implementation("response-quality", "em_dash_free")
class EmDashFree:
    """A response holds when it carries no em dash; ``repair`` rewrites each one with the punctuation its place needs."""
    REQUIRES = ()     # pure functions

    def judge(self, response: str, evidence: str = "", profile: Optional[Any] = None) -> Sequence[str]:
        """One finding per em dash, unless the profile lists no such criterion."""
        if profile is not None and getattr(profile, "criterion", None) and profile.criterion("tone fit") is None:
            return []
        return self.critique(response, evidence)

    def critique(self, answer: str, evidence: str = "") -> Sequence[str]:
        count = sum(str(answer or "").count(d) for d in EM_DASHES)
        return [f"em dash in the response: {count}"] if count else []

    def repair(self, response: str, evidence: str = "") -> str:
        return remove_em_dashes(response)
