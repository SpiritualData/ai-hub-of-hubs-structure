"""The relevance judge of Focus Context: a fast-tier model decides which candidate notes bear on the request, before the mind sees any of them.

A word count or an affinity score only ranks candidates (``arms``); it is never the gate. Two independent views, each asked the same question from its own side and run in
parallel (the structure of Decision Check: small structured prompts, a JSON verdict, no word search of a reply), name the numbers of the notes that bear on the request. A note
reaches the brief only when both views name it, so one cheap model's stray yes does not leak a note. Either view may name none: a trivial or unrelated request (the time, a
date, arithmetic, a definition) gets no note at all. A view that does not answer (no model, an error, a timeout, a reply that is not the JSON asked for) fails the judge: the
failure is logged loudly and kept in ``failure``, and nothing is added, never the lexical picks. The decision rule was fixed before any case was scored.

The candidates arrive ranked, best first, and are reviewed top down in small pages: a page of ``PAGE_SIZE`` candidates goes to the two views; the next page is reviewed only while the
page just reviewed produced a relevant note, and the review stops at the first run of ``GAP_PAGES`` pages with nothing judged relevant. A request nothing bears on therefore costs one
small page, never the whole store; the stop comes from the judged results, not from a number of notes. ``MAX_PAGES`` is only a ceiling on the calls of one gathering (the declared call
budget, as in Decision Check), so a store where everything is relevant cannot run away. The page size, the gap and the ceiling were chosen before any case was scored and are never tuned to a result. The model is the
hub's fast tier (``providers.model_for("anthropic", "fast")``), the same path as Folder View's ``model_pick``; no model name is written here."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence

from hubofhubs.the_intelligence.critical_thinking.decision_check.checks import parse_json, run_parallel
from hubofhubs.the_intelligence.subconscious.focus_context.notes import Note

LOG = logging.getLogger("hubofhubs.focus_context.judge")
TIER = "fast"
PAGE_SIZE = 5             # candidates shown to the judge at once
GAP_PAGES = 1             # consecutive pages with nothing judged relevant that end the review
MAX_PAGES = 6             # the ceiling on pages (calls: two views each) of one gathering
NOTE_CHARS = 400          # what the judge reads of one note: its start says what it is about

VIEWS = (
    ("need", "Would a person who answers this request well use what the note says? Say yes when the answer would be worse, or could be wrong, without it, including when the note "
             "is standing guidance the person saved about how to answer this kind of request (a zone, a format, a habit)."),
    ("about", "Does the note bear on this request, either because the request is about what the note is about, or because the note holds guidance, a preference or a fact the "
              "person set that applies to answering this request? A note that only shares a word with the request, or that is about a different thing, does not bear on it."),
)

PROMPT = """You decide which saved notes bear on a request, before any answer is written. Use ONLY the request and the notes below.
{focus}
Request:
{request}

Candidate notes (number, title, text):
{notes}

Question: {question}

An empty list is a correct and common answer. A trivial or general question (the time, a date, arithmetic, a definition, a summary of a well-known work) has no note that bears on it merely because a note shares a word with it; it has one only when a note holds standing guidance that applies to answering it (the person's zone or format for the time and the date, for example). A request about something other than what the notes hold has none. A short overview of the person's focus bears on a request about their own work in that focus.
Reply with JSON only: {{"relevant": [<the numbers of the notes that bear on the request, possibly none>]}}. Do not use em dashes."""


def fast_ask(tier: str = TIER, on_usage: Optional[Callable[[float, int, int], None]] = None) -> Callable[[str], str]:
    """One completion on the hub's tier for the Claude CLI provider on the operator's login (the path of Folder View's ``model_pick``); raises when the tier has no model. ``on_usage(cost_usd, tokens_in, tokens_out)`` is called in the calling thread after each call (the provider's counters are thread-local)."""
    from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
    from hubofhubs.the_world.tools.delegated_agent_sessions import providers
    engine = ClaudeCliProvider(claude_path="claude", timeout_seconds=90.0)
    model = providers.model_for("anthropic", tier)
    if not model:
        raise RuntimeError(f"no model for the {tier} tier")

    def ask(prompt: str) -> str:
        cost, tin, tout = engine.cost_usd, engine.tokens_in, engine.tokens_out
        try:
            return engine.answer([{"role": "user", "content": prompt}], model=model)
        finally:
            if on_usage:
                on_usage(engine.cost_usd - cost, engine.tokens_in - tin, engine.tokens_out - tout)
    ask.model = model                              # type: ignore[attr-defined]
    return ask


@dataclass
class Judgment:
    """What one judging found: the ``numbers`` (1-based positions in the candidate list) that bear on the request, the ``failure`` text ("" when the judge answered), the model
    calls made, the pages reviewed and how many candidates were shown to the judge."""
    numbers: List[int] = field(default_factory=list)
    failure: str = ""
    calls: int = 0
    pages: int = 0
    reviewed: int = 0


class RelevanceJudge:
    """Asks the two views in parallel and keeps the notes both name."""
    PAID = True

    def __init__(self, ask: Optional[Callable[[str], str]] = None, tier: str = TIER):
        self.injected, self.tier = ask, tier
        self.lock = threading.Lock()
        self.calls, self.cost_usd, self.tokens_in, self.tokens_out, self.model = 0, 0.0, 0, 0, ""

    def used(self, cost: float, tokens_in: int, tokens_out: int) -> None:
        with self.lock:
            self.cost_usd += cost
            self.tokens_in += tokens_in
            self.tokens_out += tokens_out

    def asker(self) -> Callable[[str], str]:
        return self.injected if self.injected is not None else fast_ask(self.tier, self.used)

    def view(self, ask: Callable[[str], str], prompt: str, count: int) -> Optional[set]:
        """The note numbers one view named, or None when it did not answer in the JSON asked for."""
        try:
            raw = ask(prompt)
        except Exception as error:  # noqa: BLE001 -- a view that cannot answer is a failed judge, said loudly by the caller
            LOG.error("focus-context judge: the model call failed (%s: %s)", type(error).__name__, error)
            return None
        finally:
            with self.lock:
                self.calls += 1
        found = parse_json(raw).get("relevant")
        if not isinstance(found, list):
            LOG.error("focus-context judge: the reply was not the JSON asked for")
            return None
        return {n for n in (int(x) if isinstance(x, (int, str)) and str(x).strip().isdigit() else 0 for x in found) if 1 <= n <= count}

    def page(self, ask: Callable[[str], str], request: str, notes: Sequence[Note], focus: str) -> Optional[set]:
        """The 1-based numbers (within this page) both views name, or None when a view did not answer."""
        listing = "\n".join(f"[{n}] {note.title}: {' '.join(note.text.split())[:NOTE_CHARS]}" for n, note in enumerate(notes, 1))
        head = f"The notes are saved by the person; their focus is {focus}.\n" if focus else ""
        prompts = [PROMPT.format(focus=head, request=request.strip()[:1500], notes=listing, question=question) for _, question in VIEWS]
        answers = run_parallel([lambda p=p: self.view(ask, p, len(notes)) for p in prompts], len(prompts))
        if any(a is None for a in answers):
            return None
        return set.intersection(*answers)

    def judge(self, request: str, notes: Sequence[Note], focus: str = "") -> Judgment:
        """Reviews ``notes`` (ranked, best first) page by page; see the module text for when the review goes on and when it stops."""
        if not notes:
            return Judgment()
        try:
            ask = self.asker()
        except Exception as error:  # noqa: BLE001 -- no provider or no model for the tier
            message = f"no model for the judge ({type(error).__name__}: {error})"
            LOG.error("focus-context judge: %s; adding nothing", message)
            return Judgment(failure=message)
        self.model = str(getattr(ask, "model", "") or self.model)
        out = Judgment()
        empty = 0
        for start in range(0, len(notes), PAGE_SIZE):
            if out.pages >= MAX_PAGES:
                break
            chunk = notes[start:start + PAGE_SIZE]
            found = self.page(ask, request, chunk, focus)
            out.pages += 1
            out.calls += len(VIEWS)
            out.reviewed += len(chunk)
            if found is None:
                message = "a judging view did not answer"
                LOG.error("focus-context judge: %s; adding nothing", message)
                return Judgment(failure=message, calls=out.calls, pages=out.pages, reviewed=out.reviewed)
            out.numbers += [start + n for n in sorted(found)]
            empty = 0 if found else empty + 1
            if empty >= GAP_PAGES:
                break
        return out
