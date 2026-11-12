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
}
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
    ok = ok and (not last.report.strip() or squash(last.report)[:30] in flat)
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
    wide = set(rows[-1].replace("|", " ").split())
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
