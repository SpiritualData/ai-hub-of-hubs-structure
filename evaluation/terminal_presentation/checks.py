"""The named checks of layer 1 of the presentation metric: each judges one ``Capture`` (the screen as drawn) and answers True, False, or None (it does not apply to this
arm or this capture). Each is tied to requirements of docs/explanation/working-with-the-ai-while-it-works.md. The bounds are stated here and in esoi.toml, fixed before any
arm was scored: repaints at most 10 a second and 4 cursor jumps a repaint; first output within 1 second (Nielsen's one-second limit for keeping the flow of thought);
contrast 4.5:1 (WCAG 2.2 success criterion 1.4.3), judged against the cell's own background, else against a black default; a snapshot is taken at every write."""
from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from screen import DARK_DEFAULT, Capture

MAX_REPAINTS_PER_SECOND = 10
MAX_JUMPS_PER_REPAINT = 4
MIN_RATE_SECONDS = 2.0           # a rate is taken over at least two seconds: the first and the last paint of a run are not flicker (set on 2026-11-11 after one one-second run showed 11 paints, before any arm was recorded)
FIRST_OUTPUT_SECONDS = 1.0
MIN_CONTRAST = 4.5
CLOSING_MARGIN = 0.15             # an arm may take one redraw interval to replace its live view with the closing report
DECORATION = re.compile(r"^[─-▟\s]+$")      # box drawing and block elements: decoration, held to 3:1 (WCAG 1.4.11 non-text contrast), not 4.5:1
MIN_CONTRAST_DECORATION = 3.0
GRACE = 0.35                     # seconds a screen is given to show an event that has arrived
DEFAULT_TEXT = (229, 229, 229)
STAMP = re.compile(r"^\s*\[\d+:\d\d\]\s*")

#: check id -> requirement ids (the doc's X numbers)
REQUIREMENTS = {
    "each-update-once": ("X1", "X13"), "current-step-visible": ("X2",), "stop-then-resume-keeps-work": ("X4", "X5", "X21"),
    "correction-sent-then-taken-up": ("X6", "X23"), "risky-step-waits-with-preview": ("X9", "X19"), "closing-report-complete": ("X10", "X33"),
    "no-row-wider-than-the-terminal": ("X13",), "repaints-under-bound": ("X13",), "contrast-4.5": ("X18",), "plain-when-not-a-terminal": ("X13",),
    "key-hints-present-and-whole": ("X4", "X6"), "first-output-within-a-second": ("X1", "X2"),
    "round-trip-stop": ("X4",), "round-trip-resume": ("X5",), "round-trip-steer": ("X6",), "round-trip-approve": ("X9",), "round-trip-refuse": ("X9",),
    "unavailable-control-shown": ("X8",),
    # revision 2 (2026-11-11): no new requirement ids; each restates what an existing one asks, in the owner's words from a real run
    "no-raw-markdown": ("X10", "X13"), "no-internal-vocabulary": ("X16", "X18"), "answer-once": ("X10", "X18"), "no-empty-figure-segment": ("X3", "X33"),
    "resume-command-unbroken": ("X33",), "header-has-full-name": ("X2", "X3"), "no-stray-leading-padding": ("X18",), "cost-at-cent-precision": ("X3",),
    "goal-as-persons-message": ("X1",),
    # revision 4 (2026-11-12): the agent hierarchy, X34 to X38 (agents_scenarios.py)
    "agents-shown-with-state": ("X34",), "agent-view-enter-and-leave": ("X34",), "message-reaches-the-right-agent": ("X35",), "stop-only-that-agent": ("X35",),
    "children-enterable-at-any-depth": ("X36",), "one-key-up-one-level": ("X36",), "depth-keeps-the-screen": ("X37",), "depth-keeps-latency": ("X37",),
    "finished-agent-enterable": ("X38",), "agent-result-once": ("X38",),
    # revision 5 (2026-11-12): the feed, the stop and the words, X39 to X43 (feed_scenarios.py; the capitalisation check runs on every scenario)
    "no-bookkeeping-tool-lines": ("X39",), "failed-command-one-muted-line": ("X40",), "ceiling-stop-said-once": ("X41",), "labels-capitalised": ("X42",), "footer-clean-at-every-width": ("X43",),
}
# revision 6 (2026-11-12): the richness of the screen, X44 to X48 (capabilities_scenarios.py), scored for every arm including the stock clients
REQUIREMENTS.update({"command-surface-listed": ("X44",), "command-surface-broad": ("X44",), "session-list-and-resume": ("X45",), "session-switching": ("X46",), "agent-navigation": ("X47",),
                     "kind-presentation": ("X48",)})
REVISION_6 = ("command-surface-listed", "command-surface-broad", "session-list-and-resume", "session-switching", "agent-navigation", "kind-presentation")
REVISION_5 = ("no-bookkeeping-tool-lines", "failed-command-one-muted-line", "ceiling-stop-said-once", "labels-capitalised", "footer-clean-at-every-width")
REVISION_2 = ("no-raw-markdown", "no-internal-vocabulary", "answer-once", "no-empty-figure-segment", "resume-command-unbroken", "header-has-full-name", "no-stray-leading-padding",
              "cost-at-cent-precision", "goal-as-persons-message")
#: the protocol ceiling column: hub information a surface may be unable to show at all (a miss there, not a rendering fault)
CEILING = ("structure-on-request", "spend-against-ceilings", "who-the-ai-acts-for", "correction-taken-up", "stop-one-helper")


def norm(row: str) -> str:
    return " ".join(STAMP.sub("", row).split())


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def events(cap: Capture, kind: Optional[type] = None) -> List[Tuple[float, Any]]:
    return [(at, e) for at, e in cap.arrivals if kind is None or isinstance(e, kind)]


def labels(cap: Capture) -> List[str]:
    found = []
    for _, e in cap.arrivals:
        for text in (getattr(e, "label", ""), getattr(e, "task", "")):
            if text and len(text) >= 3 and e.type in ("step", "agent-started") and getattr(e, "kind", "") not in ("note", "message-received"):
                found.append(text)
    return sorted(set(found))


def finish_time(cap: Capture) -> float:
    done = [at for at, e in cap.arrivals if e.type == "finished"]
    return done[-1] if done else cap.seconds


# --- the checks ---------------------------------------------------------------------------------------------------------------------

def each_update_once(cap: Capture) -> Optional[bool]:
    names = labels(cap)
    if not cap.snapshots or not names:
        return None
    has = lambda row: any(name in row for name in names)
    for snap in cap.snapshots:
        live = [norm(r) for r in snap.live if r.strip() and has(r)]
        if len(live) != len(set(live)):
            return False
        kept = {norm(r) for r in snap.scroll if r.strip() and has(r)}
        if kept & set(live) and cap.kind == "stream":
            return False
    final = [norm(r) for r in cap.final.scroll + cap.final.rows if r.strip() and has(r)]
    if cap.kind == "stream" and len(final) != len(set(final)):
        return False
    return True


def current_step_visible(cap: Capture) -> Optional[bool]:
    steps = [(at, e) for at, e in events(cap) if e.type == "step" and e.kind not in ("note", "message-received") and e.label]
    end = finish_time(cap) - CLOSING_MARGIN
    judged = shown = 0
    for snap in cap.snapshots:
        if not steps or snap.at > end:
            continue
        seen = [e for at, e in steps if at <= snap.at - GRACE]
        if not seen:
            continue
        judged += 1
        shown += seen[-1].label in cap.text_at(snap)
    if judged < 3:
        return None
    return shown / judged >= 0.9


def stop_then_resume_keeps_work(cap: Capture) -> Optional[bool]:
    names = [e.label for _, e in events(cap) if e.type == "step" and e.kind == "edit" and e.state == "done"]
    if not names:
        return False
    text = cap.final_text()
    return all(name in text for name in set(names)) and "resum" in cap.all_text().lower()


def correction_sent_then_taken_up(cap: Capture) -> Optional[bool]:
    sent = [c for _, c, ok in cap.controls if c.type == "steer"]
    if not sent:
        return None
    body = sent[0].text
    first_sent = next((i for i, s in enumerate(cap.snapshots) if any(body in r and re.search(r"queued|sent|you:|waiting", r) for r in s.scroll + s.rows)), None)
    first_taken = next((i for i, s in enumerate(cap.snapshots) if any("taken up" in r for r in s.scroll + s.rows)), None)
    return first_sent is not None and first_taken is not None and first_taken > first_sent


def risky_step_waits_with_preview(cap: Capture) -> Optional[bool]:
    waits = events(cap, None)
    waiting = [(at, e) for at, e in waits if e.type == "waiting"]
    if not waiting:
        return None
    at, ask = waiting[0]
    answers = [t for t, c, ok in cap.controls if c.type in ("approve", "refuse")]
    until = answers[0] if answers else finish_time(cap)
    seen = [s for s in cap.snapshots if at <= s.at < until]       # a screen that did not change since is the screen still showing
    if not seen:
        return False
    text = cap.text_at(seen[-1])
    needle = squash(ask.preview)[:20]
    return (squash(ask.question)[:15] in squash(text) and (not needle or needle in squash(text)) and choices_offered(cap, seen[-1]))


def declared(cap: Capture, name: str) -> Optional[str]:
    """The word or marker the arm declares its screen uses for ``name`` (``allow``, ``refuse``, ``stop``, ``person``), or None when it declares nothing (the hub's shared words apply).
    A declared label may be wrong or empty: the checks then fail it, they never fall back to the shared words."""
    return cap.labels.get(name) if name in cap.labels else None


def label_shown(label: str, text: str) -> bool:
    return bool(label.strip()) and label.strip().lower() in text.lower()


def choices_offered(cap: Capture, snap: Any) -> bool:
    """A choice to allow and a choice to refuse are offered on the waiting screen: the labels the arm declares for them are on the screen (whatever the words); an arm that declares
    neither is held to the hub's shared words (a row naming y and n, or approve and refuse)."""
    allow, refuse = declared(cap, "allow"), declared(cap, "refuse")
    if allow is None and refuse is None:
        return any(re.search(r"\by\b.*\bn\b|approve.*refuse", r, re.I) for r in snap.rows)
    text = cap.text_at(snap)
    return label_shown(allow or "", text) and label_shown(refuse or "", text)


def closing_report_complete(cap: Capture) -> Optional[bool]:
    done = [e for _, e in events(cap) if e.type == "finished"]
    if not done:
        return False
    last = done[-1]
    text, flat = cap.final_text().lower(), squash(cap.final_text())
    words = {"met": ("met", "done"), "unmet": ("unmet", "not met", "left"), "stopped": ("stopped",), "failed": ("failed",)}[last.outcome]
    ok = any(w in text for w in words)
    ok = ok and all(squash(name) in flat for name in last.changed)
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present
    ok = ok and (not last.report.strip() or squash(present.strip_markdown(last.report))[:30] in flat)       # the answer is on screen with its markers drawn or taken out
    ok = ok and bool(re.search(r"\$\d|unknown|\d:\d\d", text))
    if last.outcome == "stopped":
        ok = ok and ("--resume" in text or "resume" in text)
    return ok


def no_row_wider_than_the_terminal(cap: Capture) -> Optional[bool]:
    return cap.wide_rows == 0 and cap.sideways == 0


def repaints_under_bound(cap: Capture) -> Optional[bool]:
    if cap.kind != "stream":
        return None
    per_second = cap.repaints / max(cap.seconds, MIN_RATE_SECONDS)
    return per_second <= MAX_REPAINTS_PER_SECOND and (not cap.repaints or cap.jumps / cap.repaints <= MAX_JUMPS_PER_REPAINT)


def luminance(rgb: Sequence[int]) -> float:
    def lin(v: int) -> float:
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(v) for v in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: Sequence[int], b: Sequence[int]) -> float:
    x, y = sorted((luminance(a), luminance(b)), reverse=True)
    return (x + 0.05) / (y + 0.05)


def contrast_ok(cap: Capture) -> Optional[bool]:
    seen = {(fg, bg, bool(DECORATION.match(text))) for s in cap.snapshots for fg, bg, text, _ in s.styled}
    if not seen:
        return None
    for fg, bg, decoration in seen:
        if ratio(fg or DEFAULT_TEXT, bg or DARK_DEFAULT) < (MIN_CONTRAST_DECORATION if decoration else MIN_CONTRAST):
            return False
    return True


def hint_row(cap: Capture) -> Optional[str]:
    end = finish_time(cap)
    stop = declared(cap, "stop")
    for snap in reversed(cap.snapshots):
        if snap.at <= end:
            for row in snap.rows:
                if (label_shown(stop, row) if stop is not None else re.search(r"\bEsc\b", row)):
                    return row.strip()
    return None


def key_hints(caps: Sequence[Capture]) -> Optional[bool]:
    """A hint for stopping the work is shown whole while it runs, at every size. An arm that declares its stop label is held to that label whole (whatever the verb) on a row of the screen;
    an arm that declares nothing is held to the hub's shared row (``Esc`` and the word stop, the narrower hints kept from the widest)."""
    rows = [hint_row(c) for c in caps]
    if any(declared(c, "stop") is not None for c in caps):
        return all(r is not None for r in rows)
    if any(r is None or "stop" not in r for r in rows):
        return False
    wide = set(rows[max(range(len(caps)), key=lambda i: caps[i].width)].replace("|", " ").split())      # the widest screen's hints are the whole ones
    return all(set(r.replace("|", " ").split()) <= wide and r.replace("|", " ").split()[-1] in wide for r in rows)


def first_output(cap: Capture) -> Optional[bool]:
    first = next((s.at for s in cap.snapshots if any(r.strip() for r in s.rows)), None)
    return first is not None and first <= FIRST_OUTPUT_SECONDS


def plain_text(text: str, names: Sequence[str], report: str) -> Optional[bool]:
    return "\x1b" not in text and all(n in text for n in names) and (not report.strip() or squash(report)[:20] in squash(text))


def round_trip(cap: Capture, control: str, shown: str, text: Optional[str] = None) -> Optional[bool]:
    sent = [c for _, c, ok in cap.controls if c.type == control and ok]
    if not sent:
        return False
    return bool(re.search(shown, cap.all_text(), re.I)) and (text is None or text in cap.all_text())


def unavailable_shown(cap: Capture) -> Optional[bool]:
    stops = [c for _, c, ok in cap.controls if c.type == "stop" and c.agent_id]
    if not stops:
        return False
    caps = getattr(cap.report, "view", None)
    ended = [e for _, e in events(cap) if e.type == "agent-ended"]
    if ended and ended[0].state in ("failed", "stopped"):
        return True
    return bool(re.search(r"cannot stop|not available|unavailable|can't stop", cap.all_text(), re.I))


def combine(values: Sequence[Optional[bool]]) -> Optional[bool]:
    known = [v for v in values if v is not None]
    return None if not known else all(known)


# --- revision 2 (2026-11-11): what the owner saw on a narrow terminal ---------------------------------------------------------------------------------------------------
# Added after arms were scored on revision 1, from the owner's own words about a real run; their weights are fixed in esoi.toml before any arm is scored on them.

CSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\r")


def screen_rows(cap: Capture) -> List[str]:
    """Every row the screen holds or has scrolled above it, at the end of the run (a transcript widget's own lines already hold what it shows, so only the rows outside it are added)."""
    if cap.kind == "textual":
        return [r for r in cap.final.scroll + cap.final.live]
    return [r for r in cap.final.scroll + cap.final.rows]


def logical_lines(cap: Capture) -> List[str]:
    """The lines the arm wrote, before any terminal wrapped them: the bytes of a stream arm, the transcript of a screen arm."""
    if cap.kind == "stream":
        return CSI.sub("", cap.raw).splitlines()
    text = getattr(cap.report, "text", "") or ""
    return CSI.sub("", text).splitlines()


def flat(cap: Capture) -> str:
    return " ".join(r.strip() for r in screen_rows(cap) if r.strip())


MARKDOWN_MARKERS = re.compile(r"\*\*|__|`|^\s*#{1,6}\s|\]\(http|^\s*```")


def no_raw_markdown(cap: Capture) -> Optional[bool]:
    """No markdown marker is on the screen (bold, code, headings, fences, links)."""
    rows = [r for r in screen_rows(cap) if r.strip()]
    return None if not rows else not any(MARKDOWN_MARKERS.search(r) for r in rows)


def internal_words() -> Tuple[Any, ...]:
    """The harness's own vocabulary, read from the renderers' own names (the contract's event types and step kinds, and the lifecycle labels the shared rules hide), never a hand list."""
    from hubofhubs.the_consciousness.ai_session_experience.session_events import EVENTS, STEP_KINDS
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present
    hyphenated = sorted({w for w in list(EVENTS) + list(STEP_KINDS) if "-" in w})
    column = re.compile(r"^\W{0,3}\s*(\[\d+:\d\d\]\s*)?(ok|\.\.|!!|xx)?\s*(" + "|".join(k for k in STEP_KINDS if "-" not in k) + r")\s{2,}\S")       # a kind word padded in a column: "ok run      date"
    return hyphenated, column, re.compile(present.LIFECYCLE.pattern.strip("^$"), re.I)


def no_internal_vocabulary(cap: Capture) -> Optional[bool]:
    rows = [r.strip() for r in screen_rows(cap) if r.strip()]
    if not rows:
        return None
    hyphenated, column, lifecycle = internal_words()
    for row in rows:
        body = re.sub(r"^[^\w]+", "", row)
        bracketed_state = bool(re.search(r"\[(running|met|unmet|finished|stopped|failed|waiting)\]", row)) and "AI Hub" in row or bool(re.match(r"^ahohs\s+\S+\s+\[", row))       # the old header: the acronym, the worker and a bracketed state
        if any(w in row for w in hyphenated) or column.match(row) or lifecycle.search(body) or bracketed_state:
            return False
    return True


def answer_text(cap: Capture) -> str:
    done = [e for _, e in events(cap) if e.type == "finished"]
    return done[-1].report if done else ""


def answer_once(cap: Capture) -> Optional[bool]:
    """The answer's words are on the screen once: not again as a truncated note, a step or a summary."""
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present
    answer = present.squash(answer_text(cap))
    if len(answer) < 20:
        return None
    needle = re.sub(r"\s+", "", answer)[:30]
    return re.sub(r"\s+", "", present.strip_markdown(flat(cap)).lower()).count(needle) <= 1


def no_empty_figure_segment(cap: Capture) -> Optional[bool]:
    """No figure line has a segment without its number or an empty segment (``calls | 135 tokens``, ``· ·``)."""
    rows = [r for r in screen_rows(cap) if r.strip()]
    bad = [r for r in rows if re.search(r"(^|[|·]\s+)(calls?|tokens?)\s*([|·]|$)", r.strip()) or re.search(r"[|·]\s*[|·]", r) or re.search(r"[|·]\s*$", r.strip())]
    return None if not rows else not bad


def resume_command_unbroken(cap: Capture) -> Optional[bool]:
    """The command that resumes the session is on one logical line, whole (a hard wrap in the middle makes it uncopyable)."""
    lines = logical_lines(cap)
    hits = [l for l in lines if "--resume" in l]
    if not hits:
        return None
    return all(re.search(r"ahohs work --resume \S+( --harness \S+)?\s*$", l.strip()) for l in hits)


def header_has_full_name(cap: Capture) -> Optional[bool]:
    """Some live row carries the product's full name whole, and no row cuts it."""
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present
    seen = False
    for snap in cap.snapshots:
        for row in snap.rows:
            if "AI Hub of" in row or "Hubs Structure" in row:
                if present.PRODUCT not in row or len(row.rstrip()) > cap.width:
                    return False
                seen = True
    return seen


def no_stray_leading_padding(cap: Capture) -> Optional[bool]:
    """Rows share one left margin; a row that starts with an odd extra space (a wrapped line under no hanging indent, a lone padding space) is stray."""
    rows = [r.rstrip() for r in logical_lines(cap) if r.strip() and not DECORATION.match(r)]       # the lines the arm wrote, so a terminal's own wrapping is not counted
    if not rows:
        return None
    lead = [len(r) - len(r.lstrip(" ")) for r in rows]
    margin = min(lead)
    return all((n - margin) % 2 == 0 for n in lead)


def cost_at_cent_precision(cap: Capture) -> Optional[bool]:
    amounts = re.findall(r"\$\d[\d,]*(?:\.\d+)?", " ".join(screen_rows(cap)))
    return None if not amounts else all(re.fullmatch(r"\$\d[\d,]*\.\d\d", a) for a in amounts)


def goal_as_message(cap: Capture) -> Optional[bool]:
    """The goal is drawn as the person's own message (a prompt glyph and their words), not as a ``started:`` line."""
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present
    started = [e for _, e in events(cap) if e.type == "run-started"]
    if not started or not started[0].goal:
        return None
    goal = re.sub(r"\s+", "", started[0].goal)[:20]
    rows = [r.strip() for r in cap.all_text().splitlines()]
    marker = declared(cap, "person")
    if marker is not None:             # the arm declares the marker that sets the person's message apart (whatever it is): their goal follows it, and the AI's answer does not carry it
        if not marker.strip():
            return False
        mine = any(r.startswith(marker.strip()) and goal in re.sub(r"\s+", "", r) for r in rows)
        answer = re.sub(r"\s+", "", present.strip_markdown(answer_text(cap)))[:20]
        theirs = bool(answer) and any(r.startswith(marker.strip()) and answer in re.sub(r"\s+", "", r) for r in rows)
        return mine and not theirs and not any(re.search(r"\bstarted:", r) for r in rows)
    return any(r.startswith(present.GOAL_GLYPH) and goal in re.sub(r"\s+", "", r) for r in rows) and not any(re.search(r"\bstarted:", r) for r in rows)


# --- revision 5 (2026-11-12): what the owner saw in a real run of the full-screen views --------------------------------------------------------------------------------------
# Added after arms were scored on revision 4, from the owner's own words about a real run (bookkeeping lines, raw failed commands, a stop said four ways, lowercase labels, a clipped footer);
# their weights are fixed in esoi.toml before any arm is scored on them.

#: Exempt from the capitalisation policy, defined once (the metric record names the same list): file names and paths, shell commands a person types (the resume command, a slash command), key
#: names (they are written capitalised), and any text the agent itself supplied (its answer, a step's file or command, a helper's task, a note, the person's own goal). Wrapped continuation lines
#: (a row that follows a row that filled the width) are exempt too. Every other row that starts a sentence, a label or an item must begin with a capital letter, a digit or a symbol, and so
#: must the intro phrase before a colon.
CAPITAL_EXEMPT = ("a path or a file name", "a shell command the person types (the resume command, a slash command)", "a key name", "text the agent supplied (answer, step, task, note, goal)",
                  "a wrapped continuation line")


def agent_text(cap: Capture) -> str:
    """Every string the agent or the person supplied during the run (the scenario's own words), lower-cased: rows made of these are the agent's text, not the screen's labels."""
    parts: List[str] = []
    for _, e in cap.arrivals:
        for name in ("label", "task", "summary", "report", "question", "preview", "goal", "detail", "error", "text"):
            value = getattr(e, name, "")
            if isinstance(value, str) and value:
                parts.append(value)
        parts.extend(str(x) for x in getattr(e, "changed", ()))
    for _, control, _ok in cap.controls:
        parts.append(getattr(control, "text", "") or "")
    return " ".join(parts).lower()


def lead_of(row: str) -> str:
    """The first word a person reads in a row: leading symbols, glyphs, cursor marks, list numbers and clock stamps taken off."""
    text = STAMP.sub("", row.strip())
    return re.sub(r"^(?:[^\w\s]+\s*|\d+[.)]\s+)+", "", text)


def starts_lowercase(row: str, agent: str, width: int, previous: str) -> bool:
    """True when ``row`` begins a sentence, label or item with a lowercase letter that is not exempt."""
    text = row.strip()
    if not text or DECORATION.match(text):
        return False
    body = lead_of(text)
    if not body or not body[0].isalpha() or not body[0].islower():
        return False
    first = body.split()[0]
    if "/" in first or "." in first.strip(".,;:") or "_" in first or first.startswith(("ahohs", "http")) or re.match(r"^[\w.-]+\.\w{1,5}\b", body):
        return False                                  # a path, a file name or a command the person types
    if " ".join(body.lower().split()[:3]) in agent or body.lower()[:25] in agent:
        return False                                  # the agent's or the person's own words
    if previous and (len(previous.rstrip()) >= width - 25 or (len(previous.strip()) >= 40 and previous.rstrip()[-1] not in ".!?:;)")):
        return False                                  # a wrapped continuation of the row above (it filled the width, or it is a prose line that did not end)
    return True


def intro_lowercase(row: str, agent: str) -> bool:
    """True when the phrase before a colon starts a label with a lowercase letter that is not the agent's own text (``structure: x``, ``helper: y``)."""
    found = re.match(r"^\W*(?:\[\d+:\d\d\]\s*)?([A-Za-z][A-Za-z ]{1,30}):\s", row.strip())
    if not found:
        return False
    phrase = found.group(1)
    return phrase[0].islower() and phrase.lower() not in agent and not phrase.startswith(("ahohs",))


def labels_capitalised(cap: Capture) -> Optional[bool]:
    """Every line a person reads begins with a capital, a digit or a symbol, and so does every intro phrase before a colon (the exemptions are ``CAPITAL_EXEMPT``), on every screen the
    scenario drew (the rows as they stood at every snapshot, and the lines the arm wrote)."""
    agent = agent_text(cap)
    screens = [list(s.scroll) + list(s.rows) for s in cap.snapshots] + [logical_lines(cap)]
    seen = False
    for rows in screens:
        previous = ""
        for row in rows:
            if row.strip():
                seen = True
                if starts_lowercase(row, agent, cap.width, previous) or intro_lowercase(row, agent):
                    return False
            previous = row
    return True if seen else None


def bookkeeping_names() -> Tuple[str, ...]:
    from hubofhubs.the_consciousness.ai_session_experience.session_events import BOOKKEEPING_TOOLS
    return tuple(sorted(BOOKKEEPING_TOOLS))


def no_bookkeeping_lines(cap: Capture) -> Optional[bool]:
    """The agent's own task-list tools are never drawn: no step, row or panel names one of ``BOOKKEEPING_TOOLS`` at any moment."""
    text =cap.all_text() + "\n" + "\n".join(logical_lines(cap))
    return not any(re.search(r"\b" + name + r"\b", text) for name in bookkeeping_names())


def red(rgb: Optional[Sequence[int]]) -> bool:
    return bool(rgb) and rgb[0] >= 170 and rgb[1] <= 130 and rgb[2] <= 130


def failed_command_muted(cap: Capture) -> Optional[bool]:
    """A command that did not work is one short muted line: what was tried in a few words, no raw shell text, no ``...`` cut, not drawn in the colour of an error, and a repeat counted, never a
    new line each time."""
    failed = [(at, e) for at, e in cap.arrivals if e.type == "step" and e.kind == "run" and e.state == "failed"]
    if not failed:
        return None
    for at, e in failed:        # once it has failed, the raw command is not on the screen (while it ran, the screen may name it)
        after = "\n".join(cap.text_at(s) for s in cap.snapshots if s.at >= at + GRACE)
        if e.label and e.label in after + "\n" + "\n".join(logical_lines(cap)):
            return False                                  # the raw command reached the screen
    lines = [l.strip() for l in logical_lines(cap) if re.search(r"did not work|could not be checked", l)]
    if not lines or any(len(l) > 70 or "..." in l or "Command failed" in l for l in lines):
        return False
    for snap in cap.snapshots:
        for fg, _bg, sample, _named in snap.styled:
            if re.search(r"did not work|could not be checked", sample) and red(fg):
                return False
    return True


def ceiling_stop_said_once(cap: Capture) -> Optional[bool]:
    """A run stopped at its ceiling says so once, in plain words: what happened, that finished work is kept, how to continue and how to raise the limit, in one place; no second line says the
    same (a helper that was stopped, a hand-off, ``stopped:`` and the limit line)."""
    if not any(e.type == "notice" and e.kind == "hard-limit" for _, e in cap.arrivals):
        return None
    lines = [l.strip() for l in logical_lines(cap) if l.strip()]
    limit = [l for l in lines if re.search(r"\bat the (spend|time) (limit|ceiling)\b|\bat its (spend|time) (limit|ceiling)\b", l, re.I)]       # what happened, said once (how to raise it is its own line)
    kept = [l for l in lines if re.search(r"work is kept", l, re.I)]
    resume = [l for l in lines if "--resume" in l and l.startswith("ahohs")]
    raise_how = [l for l in lines if re.search(r"--max-(spend|time)", l)]
    echoes = [l for l in lines if re.search(r"was stopped|Handed off|^stopped:|stopped at its|Used\s*[·]?\s*$", l, re.I)]
    return len(limit) == 1 and len(kept) == 1 and len(resume) == 1 and len(raise_how) == 1 and not echoes


def clipped_word(row: str, agent: str) -> bool:
    """A row that ends with an ellipsis after a word cut in the middle (``Find one interesting find…``): the text before it is not a whole-word start of anything the agent said."""
    found = re.search(r"(\S.*?)(…|\.\.\.)\s*$", row.strip())
    if not found:
        return False
    stem = re.sub(r"[\s,;:-]+$", "", found.group(1)).lower()
    words = stem.split()
    if len(words) < 2:
        return False
    at = agent.find(" ".join(words[-3:]))
    if at < 0:
        return False
    after = agent[at + len(" ".join(words[-3:])):][:1]
    return after.isalnum()                                  # the agent's word goes on: it was cut inside it


def repeated_words(row: str) -> bool:
    """The same run of three words twice in one row (a name printed twice)."""
    words = re.findall(r"\w{3,}", row.lower())
    grams = [tuple(words[i:i + 3]) for i in range(len(words) - 2)]
    return len(grams) != len(set(grams))


def footer_clean(cap: Capture) -> Optional[bool]:
    """The live area below the feed (the structure, agents and key rows) is laid out whole at this width: no row cut inside a word, none ending at the very edge in a letter, none with a name
    twice, an Agents heading above the helper rows, and no half hint."""
    agent = agent_text(cap)
    seen = False
    for snap in cap.snapshots:
        rows = [r.rstrip() for r in snap.live if r.strip()]
        for index, row in enumerate(rows):
            body = row.strip()
            if re.match(r"^[>›]?\s*\d+\.\s", body):
                seen = True
                if not any(r.strip() in ("Agents", "Agents:") for r in rows[:index]):
                    return False                                  # helper rows without their heading
            if clipped_word(row, agent) or repeated_words(row) or re.search(r"\(Tab shows\s?\w{0,3}$|\bTab shows th$", body):
                return False
            if len(row) >= cap.width - 1 and row[-1:].isalnum() and re.match(r"^[>›]?\s*\d+\.\s", body):
                return False                                      # an agent row cut at the edge
    return True if seen else None
