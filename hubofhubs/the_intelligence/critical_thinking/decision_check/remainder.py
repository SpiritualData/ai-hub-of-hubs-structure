"""What is left of a reply after some of its sentences are taken out must still read as an answer.

Removing a sentence can leave a later one pointing at it: "Its current value is 50 percent." after the sentence that named the milestone, or "The quest's own check shows the
same figure." after the sentence that stated the figure. ``dangling`` finds such sentences structurally: a sentence that opens with a back-reference word (a pronoun or a
demonstrative) right after a removed sentence, a sentence holding "the same ..." right after one, and a demonstrative with a noun ("that blocker") whose noun was only ever said in
removed sentences. It reads grammar words only (pronouns and demonstratives, a closed class), never what the reply means.

``cohere`` repairs those sentences: one call that may only reword a dangling sentence from words the remaining reply already holds, or remove it. Code checks each rewrite
(no figure, date or name the remaining reply and the question do not hold, and the rewrite does not itself dangle) and removes the sentence when a rewrite fails the check or no
call can be made. ``shorten`` brings a reply to a sentence limit by removing the sentences it needs least (judged by structure: the opening answer, a sentence the question's words
point to and a sentence that carries a kept item are kept; a sentence that repeats an earlier one or shares no word with the question goes first), and never by position alone.
Standard library only."""
import json
import re
from typing import Callable, Iterable, List, Optional, Sequence, Set, Tuple

SENTENCE_SPLIT = re.compile(r"(?<=[.!?])[ \t]+(?=[\"'(\[*A-Z0-9])")
WORD = re.compile(r"[A-Za-z][A-Za-z'-]*")
FIGURE = re.compile(r"\d+(?:[.,]\d+)*")
CAPITALISED = re.compile(r"\b[A-Z][a-zA-Z'-]{2,}")
# Back-reference words: pronouns and demonstratives (a closed class of grammar words). A sentence opening with one leans on the sentence before it.
BACK_REFERENCE_OPENERS = frozenset("it its it's they their them theirs this that these those he she his her him such".split())
DEMONSTRATIVE_HEAD = re.compile(r"\b(?:this|that|these|those)\s+(?P<head>[A-Za-z][A-Za-z-]{2,})", re.IGNORECASE)
NOT_A_NOUN = frozenset("the and for but not you our his her its are was were has had have will would can could may might must does did should shall".split())
THE_SAME = re.compile(r"\bthe\s+same\b", re.IGNORECASE)
STEM = 5
STOP = frozenset(("that this with from have were been what when where which their there about would could should your they them then than also into over only just more most "
                  "some very much many does done each other still here these those will just being able after before since while").split())


class Unit:
    """One sentence of a reply, with the line breaks that came before it (so a reply keeps its paragraphs) and whether it is kept."""
    __slots__ = ("text", "lead", "kept", "protected")

    def __init__(self, text: str, lead: str = "", kept: bool = True, protected: bool = False):
        self.text, self.lead, self.kept, self.protected = text, lead, kept, protected

    def __repr__(self) -> str:      # pragma: no cover -- debugging aid
        return f"Unit({self.text!r}, kept={self.kept})"


def units_of(text: str) -> List[Unit]:
    """The sentences of ``text`` in order, each with the line breaks before it. Lines are split first, then sentences inside a line."""
    out: List[Unit] = []
    pending = ""
    for part in re.split(r"(\n+)", str(text or "")):
        if not part:
            continue
        if part.startswith("\n"):
            pending += part
            continue
        for k, piece in enumerate(SENTENCE_SPLIT.split(part)):
            if piece.strip():
                out.append(Unit(piece.strip(), pending if k == 0 else ""))
                pending = ""
    return out


def joined(units: Iterable[Unit]) -> str:
    """The kept sentences as one text: a sentence after a removed paragraph break keeps the break, sentences on one line are joined with a space."""
    out = ""
    carry = ""
    for u in units:
        if not u.kept:
            carry = carry or u.lead
            continue
        lead = u.lead or carry
        carry = ""
        if not out:
            out = u.text
        elif lead:
            out += ("\n\n" if lead.count("\n") > 1 else "\n") + u.text
        else:
            out += " " + u.text
    return out.strip()


def stems(text: str) -> List[str]:
    return [w.lower()[:STEM] for w in WORD.findall(text or "") if len(w) >= 3]


def topic_stems(text: str) -> Set[str]:
    return {w.lower()[:STEM] for w in WORD.findall(text or "") if len(w) >= 4 and w.lower() not in STOP}


def figures(text: str) -> Set[str]:
    """The numbers of ``text`` by value: thousands commas and leading zeros aside, so "1,000" and "1000", "02" and "2" are one figure."""
    out = set()
    for raw in FIGURE.findall(text or ""):
        plain = raw.replace(",", "") if re.fullmatch(r"\d{1,3}(?:,\d{3})+", raw) else raw
        out.add(plain.lstrip("0") or "0")
    return out


IMPERSONAL_REFERENCES = frozenset("it its this these those".split())
OPENING_WORDS = 3      # "It ...", "Behind it, ...", "Because of this, ...": a back-reference in the first words leans on the sentence before


def opener(text: str) -> str:
    """The back-reference word among the sentence's first words, or its first word when there is none."""
    words = [w.lower() for w in WORD.findall(text or "")[:OPENING_WORDS]]
    # Past the first word only the impersonal back-references count: "that" and "such" there are usually a conjunction or an adjective ("I know that ..."), and a
    # personal pronoun ("Is she free?") usually names a person an earlier kept sentence named.
    return next((w for k, w in enumerate(words) if w in BACK_REFERENCE_OPENERS and (k == 0 or w in IMPERSONAL_REFERENCES)), words[0] if words else "")


def dangling(units: Sequence[Unit], question: str = "") -> List[int]:
    """Indexes of kept sentences that refer back to a removed one: a back-reference opener or "the same" right after a removed sentence, or a demonstrative whose noun only a
    removed sentence said (not an earlier kept sentence, not the sentence itself elsewhere, not the question)."""
    asked = set(stems(question))
    removed_stems = {s for u in units if not u.kept for s in stems(u.text)}
    out: List[int] = []
    said: Set[str] = set()
    previous_removed = False
    for i, u in enumerate(units):
        if not u.kept:
            previous_removed = True
            continue
        words = stems(u.text)
        heads = [m for m in DEMONSTRATIVE_HEAD.finditer(u.text) if m.group("head").lower() not in NOT_A_NOUN]
        # A demonstrative with its own noun ("That key ...") is judged by that noun below, not by what came right before it.
        opens_with_noun = bool(heads) and heads[0].start() == len(u.text) - len(u.text.lstrip())
        lost = previous_removed and ((opener(u.text) in BACK_REFERENCE_OPENERS and not opens_with_noun) or bool(THE_SAME.search(u.text)))
        if not lost and removed_stems:
            for m in heads:
                head = m.group("head").lower()[:STEM]
                if head in removed_stems and head not in said and head not in asked and words.count(head) <= 1:
                    lost = True
                    break
        if lost:
            out.append(i)
        said.update(words)
        previous_removed = False
    return out


COHERE_PROMPT = """Some sentences were taken out of a reply because they could not be confirmed. The sentences marked below now point back to something that is no longer said.

The question the reply answers:
{question}

The reply as it is now (numbered):
{reply}

Sentences that point back to removed text: {marked}

For each marked sentence, either rewrite it so it reads on its own, using only words, names, dates and figures the reply above already holds, or remove it. Never bring back what the
removed sentences said, and never add a fact, figure, date or name.
Reply with JSON only: {{"sentences": [{{"n": <the sentence's number>, "action": "rewrite" or "remove", "text": "<the rewritten sentence, empty when removing>"}}]}}. Do not use em dashes."""


def rewrite_allowed(text: str, units: Sequence[Unit], index: int, question: str) -> bool:
    """A rewrite of a dangling sentence stands only when it states no figure and no capitalised name that the remaining reply (or the question) does not hold, and does not open
    with a back-reference itself when the sentence before it was removed."""
    if not text.strip():
        return False
    held = " ".join(u.text for u in units if u.kept) + " " + (question or "")
    if figures(text) - figures(held):
        return False
    names = {w.lower() for w in CAPITALISED.findall(held)} | {w.lower() for w in WORD.findall(held)}
    if any(w.lower() not in names for w in CAPITALISED.findall(text) if w.lower() not in BACK_REFERENCE_OPENERS):
        return False
    trial = [Unit(u.text, u.lead, u.kept) for u in units]
    trial[index].text = text
    return index not in dangling(trial, question)


def cohere(units: List[Unit], question: str = "", ask: Optional[Callable[[str], Optional[str]]] = None) -> Tuple[List[Unit], str]:
    """``(units, how)`` with every dangling sentence rewritten from the remaining reply or removed. ``how`` is "coherent" (nothing dangled), "rewritten" (a call reworded at
    least one), or "removed" (dangling sentences were taken out). Never removes the last kept sentence: a reply of one dangling sentence is left for the caller to judge."""
    lost = dangling(units, question)
    if not lost:
        return units, "coherent"
    how = "removed"
    if ask is not None:
        kept = [i for i, u in enumerate(units) if u.kept]
        number = {i: n for n, i in enumerate(kept, 1)}
        reply = "\n".join(f"{number[i]}. {units[i].text}" for i in kept)
        try:
            raw = ask(COHERE_PROMPT.format(question=question or "(not given)", reply=reply, marked=", ".join(str(number[i]) for i in lost)))
        except Exception:  # noqa: BLE001 -- a failed call removes the dangling sentences instead
            raw = None
        rows = parse_rows(raw)
        by_number = {n: i for i, n in number.items()}
        for row in rows:
            i = by_number.get(row.get("n"))
            if i is None or i not in lost:
                continue
            text = " ".join(str(row.get("text") or "").split())
            if row.get("action") == "rewrite" and rewrite_allowed(text, units, i, question):
                units[i].text = text
                how = "rewritten"
    for _ in range(len(units)):
        lost = dangling(units, question)
        if not lost:
            break
        for i in lost:
            if sum(u.kept for u in units) > 1:
                units[i].kept = False
    return units, how


def parse_rows(raw: object) -> List[dict]:
    text = str(raw or "")
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return []
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return []
    rows = data.get("sentences") if isinstance(data, dict) else None
    out = []
    for row in rows if isinstance(rows, list) else ():
        if isinstance(row, dict):
            try:
                out.append(dict(row, n=int(row.get("n"))))
            except (TypeError, ValueError):
                continue
    return out


def cohered_text(before: str, after: str, question: str = "", ask: Optional[Callable[[str], Optional[str]]] = None) -> str:
    """``after`` (``before`` with sentences removed) with every sentence that pointed back to a removed one rewritten or removed. Sentences of ``before`` that ``after`` no longer
    holds count as removed; a sentence ``after`` changed or added is kept where it stands."""
    units = units_of(before)
    remaining = [u.text for u in units_of(after)]
    pool = list(remaining)
    for u in units:
        if u.text in pool:
            pool.remove(u.text)
        else:
            u.kept = False
    if pool:      # sentences ``after`` holds that ``before`` did not (a rewrite): judge ``after`` alone, with nothing marked removed
        return after
    units, _ = cohere(units, question, ask)
    return joined(units)


def need(unit: Unit, index: int, units: Sequence[Unit], question_stems: Set[str], fact_stems: Set[str]) -> float:
    """How much a sentence is needed, by structure: sharing the question's words, sharing the facts' words and stating a figure keep it; repeating the words of an earlier kept
    sentence, or a back-reference whose antecedent is gone, make it the first to go. The order breaks ties: a later sentence goes before an earlier one."""
    own = topic_stems(unit.text)
    score = 0.0
    if own & question_stems:
        score += 3 + len(own & question_stems) / max(1, len(question_stems))
    if own & fact_stems:
        score += 2
    if figures(unit.text):
        score += 1
    earlier = set()
    for u in units[:index]:
        if u.kept:
            earlier |= topic_stems(u.text)
    if own and len(own & earlier) >= 0.6 * len(own):
        score -= 4      # says again what an earlier sentence said
    return score - index * 0.001


def shorten(units: List[Unit], limit: int, question: str = "", facts: str = "") -> List[Unit]:
    """``units`` with the least needed unprotected sentences removed until at most ``limit`` count (a protected sentence, such as a kept draft's, is kept and not counted), and with
    any sentence left pointing back to a removed one removed too. The opening sentence (the answer, in every reply standard) and the sentence that shares most with the question
    are kept. Never removes every sentence."""
    counted = [i for i, u in enumerate(units) if u.kept and not u.protected]
    if limit <= 0 or len(counted) <= limit:
        return units
    question_stems, fact_stems = topic_stems(question), topic_stems(facts)
    keep = {counted[0]}
    best = max(counted, key=lambda i: (len(topic_stems(units[i].text) & question_stems), -i))
    if topic_stems(units[best].text) & question_stems:
        keep.add(best)
    while True:
        counted = [i for i, u in enumerate(units) if u.kept and not u.protected]
        if len(counted) <= limit:
            break
        candidates = [i for i in counted if i not in keep]
        if not candidates:
            break
        drop = min(candidates, key=lambda i: need(units[i], i, units, question_stems, fact_stems))
        units[drop].kept = False
        for i in dangling(units, question):
            if not units[i].protected and i not in keep:
                units[i].kept = False
    return units


def shortened_text(text: str, limit: int, question: str = "", facts: str = "", protected: Sequence[str] = ()) -> str:
    """``text`` held to ``limit`` sentences by ``shorten``; a sentence inside any of ``protected`` (a kept draft, a line with a link) is kept and not counted."""
    units = units_of(text)
    for u in units:
        u.protected = any(u.text in p or (p and p in u.text) for p in protected if p)
    return joined(shorten(units, limit, question, facts))
