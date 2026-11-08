"""The parts every Decision Check arm shares: what a consumer hands in (``CheckBinding``, ``View``, ``Vote``), the small structured prompts, the structural reading of a model's
JSON reply, the code that verifies a quote or a span is really in the text it claims to come from, the call budget and the bounded parallel run.

A model's reply is read only as a structured verdict (an option id, ABSTAIN, a list of spans, an action). Nothing here searches a reply for words to decide an outcome: a reply that
is not the JSON asked for is a view that did not answer, and a quote or span that is not in the text it names is a view that did not ground its answer. Standard library only."""
import json
import re
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

ABSTAIN = "ABSTAIN"
PICK, REPLY = "pick", "reply"


@dataclass(frozen=True)
class View:
    """One small check: an ``instruction`` and the ``evidence`` slice it alone sees (the owner's rules only, the prior examples only, the actions executed only, ...)."""
    id: str
    instruction: str
    evidence: str


@dataclass(frozen=True)
class Vote:
    """An opinion the consumer already holds, so it costs no call: ``pick`` with the words it rests on (``quote``) and the ``evidence`` they come from."""
    id: str
    pick: str
    quote: str = ""
    evidence: str = ""


@dataclass
class CheckBinding:
    """What a consumer supplies. ``kind`` is ``pick`` (a pick among ``options``, each a mapping with ``id`` and ``text``) or ``reply`` (a text whose failing spans are repaired). ``draft_basis`` is what the
    producer of a pick gave as its reason. ``known`` maps a view id to its known-mistake lines (most frequent first), and ``token_cap`` bounds the tokens they take in a prompt.
    ``max_calls`` is the declared cap on model calls for this decision and ``parallel`` the most that run at once."""
    kind: str = PICK
    options: Sequence[Mapping[str, Any]] = ()
    views: Sequence[View] = ()
    votes: Sequence[Vote] = ()
    draft_basis: str = ""
    known: Mapping[str, Sequence[str]] = field(default_factory=dict)
    token_cap: int = 300
    max_calls: int = 6
    parallel: int = 4
    #: Seconds after which a call still unanswered is asked once more in parallel and the first answer is taken (a provider's retry wait, not the work, makes the
    #: slowest calls slow). 0 asks every call once.
    hedge_after_seconds: float = 0.0
    #: For a reply: the question it answers. What is left after a removal is held to it (a sentence pointing back to a removed one is rewritten or removed).
    question: str = ""


def as_binding(value: Any) -> CheckBinding:
    """A ``CheckBinding`` from itself or from the mapping a caller of ``hubofhubs.run`` passes."""
    if isinstance(value, CheckBinding):
        return value
    data = dict(value or {})
    data["views"] = [v if isinstance(v, View) else View(**v) for v in data.get("views") or ()]
    data["votes"] = [v if isinstance(v, Vote) else Vote(**v) for v in data.get("votes") or ()]
    return CheckBinding(**data)


class Calls:
    """The declared call budget of one decision: ``take`` spends a call and says whether one was left."""

    def __init__(self, limit: int):
        self.limit, self.used, self.lock = max(0, int(limit)), 0, threading.Lock()

    def take(self) -> bool:
        with self.lock:
            if self.used >= self.limit:
                return False
            self.used += 1
            return True

    @property
    def left(self) -> int:
        return max(0, self.limit - self.used)


class CallPool:
    """Model calls run on a pool of ``width`` in flight; ``next_answers`` gives each logical call's answer as soon as it is in. With ``hedge_after`` set, a call still
    unanswered after that many seconds is sent once more alongside (on top of the width, since the slow one is waiting on the provider, not working) and the first
    answer that is not a failed call wins; the other copy is left to finish unread. ``hedged`` counts the extra sends."""

    def __init__(self, ask: Callable[[str], Optional[str]], width: int, hedge_after: float = 0.0, on_hedge: Optional[Callable[[], None]] = None):
        self.ask, self.hedge_after, self.on_hedge = ask, max(0.0, float(hedge_after or 0.0)), on_hedge
        self.pool = ThreadPoolExecutor(max_workers=max(1, int(width)) * (2 if self.hedge_after else 1))
        self.width = max(1, int(width))
        self.queue: List[Tuple[Any, str]] = []
        self.flying: Dict[Any, Tuple[int, float]] = {}     # future -> (logical call, sent at)
        self.calls: Dict[int, Dict[str, Any]] = {}
        self.hedged = 0

    def submit(self, tag: Any, prompt: str) -> None:
        self.queue.append((tag, prompt))

    def _launch(self) -> None:
        live = len({n for n, _ in self.flying.values()})
        while self.queue and live < self.width:
            tag, prompt = self.queue.pop(0)
            n = len(self.calls)
            self.calls[n] = {"tag": tag, "prompt": prompt, "copies": 1, "hedged": False}
            self.flying[self.pool.submit(self.ask, prompt)] = (n, time.monotonic())
            live += 1

    def busy(self) -> bool:
        return bool(self.queue or self.flying)

    def next_answers(self) -> List[Tuple[Any, Optional[str]]]:
        """The ``(tag, answer)`` of every logical call that has settled since the last call, waiting until at least one has."""
        while True:
            self._launch()
            if not self.flying:
                return []
            timeout = None
            if self.hedge_after:
                now = time.monotonic()
                due = [sent + self.hedge_after - now for n, sent in self.flying.values() if not self.calls[n]["hedged"]]
                timeout = max(0.0, min(due)) if due else None
            done, _ = wait(list(self.flying), timeout=timeout, return_when=FIRST_COMPLETED)
            out = []
            for future in done:
                n, _ = self.flying.pop(future)
                call = self.calls[n]
                call["copies"] -= 1
                if call.get("settled"):
                    continue
                raw = future.result()
                if raw is not None and str(raw).startswith("ERROR ") and call["copies"] > 0:
                    continue        # a failed copy: the other copy may still answer
                call["settled"] = True
                for other in [f for f, (m, _) in self.flying.items() if m == n]:
                    del self.flying[other]          # left to finish unread
                out.append((call["tag"], raw))
            if self.hedge_after:
                now = time.monotonic()
                for n, sent in list(self.flying.values()):
                    call = self.calls[n]
                    if not call["hedged"] and not call.get("settled") and now - sent >= self.hedge_after:
                        call["hedged"], call["copies"] = True, call["copies"] + 1
                        self.hedged += 1
                        if self.on_hedge:
                            self.on_hedge()
                        self.flying[self.pool.submit(self.ask, call["prompt"])] = (n, now)
            if out:
                return out

    def close(self) -> None:
        self.pool.shutdown(wait=False, cancel_futures=True)


def run_parallel(jobs: Sequence[Callable[[], Any]], width: int) -> List[Any]:
    """The results of ``jobs`` in order, at most ``width`` at once."""
    if not jobs:
        return []
    if width <= 1 or len(jobs) == 1:
        return [job() for job in jobs]
    with ThreadPoolExecutor(max_workers=min(width, len(jobs))) as pool:
        return [f.result() for f in [pool.submit(job) for job in jobs]]


def parse_json(text: Any) -> Dict[str, Any]:
    """The JSON object in a model's reply, or an empty mapping when there is none."""
    raw = str(text or "")
    start, end = raw.find("{"), raw.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(raw[start:end + 1])
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


def squash(text: Any) -> str:
    return " ".join(str(text or "").casefold().split())


def quoted(quote: Any, evidence: Any) -> bool:
    """Whether the words quoted are in the evidence (case and spacing aside). An empty quote is not a quote."""
    wanted = squash(quote)
    return len(wanted) >= 2 and wanted in squash(evidence)


def known_block(lines: Sequence[str], token_cap: int) -> str:
    """The known-mistake lines of a check as a prompt block, in the order given (most frequent first), cut to ``token_cap`` tokens (four characters each)."""
    kept, spent = [], 0
    for line in lines or ():
        cost = (len(str(line)) + 3) // 4 + 1
        if spent + cost > token_cap:
            break
        kept.append(f"- {str(line).strip()}")
        spent += cost
    return ("Mistakes this check is known to make (do not repeat them):\n" + "\n".join(kept) + "\n") if kept else ""


def options_listing(options: Sequence[Mapping[str, Any]]) -> str:
    return "\n".join(f"{o.get('id')} | {str(o.get('text') or '')[:300]}" for o in options)


PICK_PROMPT = """You are one of several independent checkers. Use ONLY the evidence below.
Task: {instruction}

Options (id | text):
{options}

Evidence:
{evidence}
{known}
Reply with JSON only: {{"pick": "<an option id exactly as listed, or {abstain} when the evidence does not decide>", "quote": "<words copied exactly from the evidence that decide it, or empty>"}}. Do not use em dashes."""

ADJUDICATE_PROMPT = """Independent checks disagreed about which option is right. Each is shown with what it was asked, the only evidence it saw and the words it quoted. Decide using ONLY that evidence.

Options (id | text):
{options}

The checks:
{views}

Pick the option the evidence above decides, and copy exactly the words from that evidence which decide it. If the evidence does not decide, pick {abstain}.
Reply with JSON only: {{"pick": "<an option id exactly as listed, or {abstain}>", "quote": "<words copied exactly from the evidence above>"}}. Do not use em dashes."""

FINDINGS_PROMPT = """You are one of several independent checkers of a reply. Use ONLY the evidence below.
Task: {instruction}

Reply:
{draft}

Evidence:
{evidence}
{known}
Only a part of the kind the task is about can fail it; a part of any other kind does not fail it and is not listed. A part that the evidence supports does not fail. List each part of the reply that fails the task, copied exactly as written in the reply. If nothing fails, list none.
Reply with JSON only: {{"findings": [{{"span": "<words copied exactly from the reply>", "quote": "<words copied exactly from the evidence that contradict it, or empty>"}}]}}. Do not use em dashes."""

CONFIRM_PROMPT = """Use ONLY the evidence below.
Task: {instruction}

Statements, each judged on its own:
{statements}

Evidence:
{evidence}

For each numbered statement: does it fail the task? It fails only if it is of the kind the task is about and the evidence does not support it (or contradicts it). A statement of any other kind does not fail.
Reply with JSON only: {{"verdicts": [{{"n": <the statement's number>, "fails": true or false, "quote": "<words copied exactly from the evidence that show it, or empty>"}}]}}, one entry per statement. Do not use em dashes."""


def numbered(spans: Sequence[str]) -> str:
    return "\n".join(f"{i}. {span}" for i, span in enumerate(spans, 1))


def read_verdicts(raw: Any, count: int) -> Dict[int, Dict[str, Any]]:
    """The verdicts of one confirmation call, by statement index (0-based); a statement the reply gives no true/false for is missing, i.e. not answered."""
    rows = parse_json(raw).get("verdicts")
    out: Dict[int, Dict[str, Any]] = {}
    for row in rows if isinstance(rows, list) else ():
        if not isinstance(row, dict) or not isinstance(row.get("fails"), bool):
            continue
        try:
            n = int(row.get("n")) - 1
        except (TypeError, ValueError):
            continue
        if 0 <= n < count and n not in out:
            out[n] = {"fails": row["fails"], "quote": str(row.get("quote") or "")}
    return out


REPAIR_PROMPT = """One part of a reply fails this task: {instruction}

Sentence containing it:
{sentence}

The failing part:
{span}

Evidence it must agree with:
{evidence}

Rewrite only the failing part so that it agrees with the evidence, or remove it when nothing true can take its place.
Reply with JSON only: {{"action": "rewrite" or "remove", "text": "<the replacement for the failing part, empty when removing>"}}. Do not use em dashes."""


def sentence_of(draft: str, span: str) -> str:
    """The sentence of ``draft`` that holds ``span``."""
    for part in re.split(r"(?<=[.!?])\s+|\n+", draft):
        if span in part:
            return part
    return span


def remove_span(draft: str, span: str) -> str:
    """``draft`` without its first ``span``, spacing and an emptied line tidied."""
    out = draft.replace(span, "", 1)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return re.sub(r"\n[ \t]+\n", "\n\n", out).strip()


def pick_view_prompt(view: View, binding: CheckBinding) -> str:
    return PICK_PROMPT.format(instruction=view.instruction, options=options_listing(binding.options), evidence=view.evidence,
                              known=known_block(binding.known.get(view.id, ()), binding.token_cap), abstain=ABSTAIN)


def read_pick(raw: Any, view_id: str, evidence: str, options: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    """One view's reading: the option it picked and the words it rests on, or an abstain with the reason it did not stand (no JSON, not an option, quote not in its evidence)."""
    data = parse_json(raw)
    pick, quote = data.get("pick"), data.get("quote")
    row = {"id": view_id, "pick": "", "quote": "", "reason": ""}
    if not isinstance(pick, str):
        return dict(row, reason="the reply was not the JSON asked for")
    pick = pick.strip()
    if pick.upper() == ABSTAIN:
        return dict(row, reason="the view found the evidence does not decide")
    if pick not in {str(o.get("id")) for o in options}:
        return dict(row, reason="the pick was not an option offered")
    if not quoted(quote, evidence):
        return dict(row, reason="the quote is not in the evidence this view saw")
    return dict(row, pick=pick, quote=str(quote).strip())


def spent_view(view_id: str, reason: str) -> Dict[str, Any]:
    return {"id": view_id, "pick": "", "quote": "", "reason": reason}
