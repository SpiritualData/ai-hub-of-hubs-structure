"""citations -- compare the DOIs in a reply with the DOIs a turn actually had.

A model can write a DOI that reads perfectly and names no paper. The link guard checks links; a bare DOI is not a link, so this
checks the DOI strings. It is a data comparison, not a judgement of wording: every DOI found in the reply is looked up in the
DOIs that appear in the structured evidence the turn held (the tool results, the person's own message, the cards), and one that
is not there is replaced. Reading DOI strings in a reply to compare them with returned data is the only thing it does; it
never decides anything from what the model said around the DOI. A consumer that prefers to flag instead of replace passes its
own ``placeholder``.
"""
from __future__ import annotations

import re
from typing import Iterable, List, Set, Tuple

#: A DOI as it is written in prose or in a link: the 10.NNNN/ prefix, then up to a space or a character that closes a quote,
#: bracket or link. Trailing sentence punctuation is trimmed afterwards.
DOI_IN_TEXT = re.compile(r"10\.\d{4,9}/[^\s?#\"'<>\[\]{}|\\^`]+", re.I)
TRAILING = ".,;:)*_!"
PLACEHOLDER = "[DOI not verified]"


def doi_candidates(text: str) -> List[Tuple[int, int, str]]:
    """Each DOI in ``text`` as ``(start, end, doi)``, the DOI lower case without trailing punctuation or an unmatched ``)``."""
    found = []
    for match in DOI_IN_TEXT.finditer(text or ""):
        raw = match.group(0)
        end = match.end()
        while raw and raw[-1] in TRAILING and not (raw[-1] == ")" and raw.count("(") >= raw.count(")")):
            raw = raw[:-1]
            end -= 1
        if "/" in raw and len(raw.split("/", 1)[1]) >= 1:
            found.append((match.start(), end, raw.lower()))
    return found


def dois_in(*sources: object) -> Set[str]:
    """Every DOI that appears in the given texts (strings, or lists and dicts of them), lower case."""
    seen: Set[str] = set()

    def walk(item: object, depth: int = 0) -> None:
        if depth > 6 or item is None:
            return
        if isinstance(item, str):
            seen.update(d for _, _, d in doi_candidates(item))
        elif isinstance(item, dict):
            for value in item.values():
                walk(value, depth + 1)
        elif isinstance(item, Iterable):
            for value in item:
                walk(value, depth + 1)

    for source in sources:
        walk(source)
    return seen


def unlisted_dois(text: str, known: Iterable[str]) -> List[str]:
    """The DOIs in ``text`` that are not in ``known`` (lower case DOIs), in order of first appearance."""
    allowed = {k.lower() for k in known}
    out: List[str] = []
    for _, _, doi in doi_candidates(text):
        if doi not in allowed and doi not in out:
            out.append(doi)
    return out


def strip_unlisted_dois(text: str, known: Iterable[str], *, placeholder: str = PLACEHOLDER) -> Tuple[str, List[str]]:
    """``text`` with every DOI not in ``known`` replaced by ``placeholder``, and the DOIs replaced. Fails closed: an unknown
    DOI is removed, never kept. A DOI inside a link goes too, which leaves the link's address broken, so the link is plain words."""
    allowed = {k.lower() for k in known}
    removed: List[str] = []
    pieces: List[str] = []
    cursor = 0
    for start, end, doi in doi_candidates(text):
        if doi in allowed:
            continue
        pieces.append(text[cursor:start])
        pieces.append(placeholder)
        cursor = end
        if doi not in removed:
            removed.append(doi)
    pieces.append(text[cursor:])
    return "".join(pieces), removed
