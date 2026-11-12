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
}
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
    return (squash(ask.question)[:15] in squash(text) and (not needle or needle in squash(text))
            and any(re.search(r"\by\b.*\bn\b|approve.*refuse", r, re.I) for r in seen[-1].rows))


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
    for snap in reversed(cap.snapshots):
        if snap.at <= end:
            for row in snap.rows:
                if re.search(r"\bEsc\b", row):
                    return row.strip()
    return None


def key_hints(caps: Sequence[Capture]) -> Optional[bool]:
    rows = [hint_row(c) for c in caps]
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
    return any(r.startswith(present.GOAL_GLYPH) and goal in re.sub(r"\s+", "", r) for r in rows) and not any(re.search(r"\bstarted:", r) for r in rows)
