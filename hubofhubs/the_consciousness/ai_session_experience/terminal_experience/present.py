"""How a run reads: one small set of pure rules that every terminal arm draws with, so no arm keeps a style of its own.

Revision of 2026-11-11 (the owner's feedback after using the terminal): the header spells the product's name out and leaves out what is not yet worth reading; the person's goal
is their own message; a step is one line (a glyph and a plain phrase, never the raw kind word in a column); the lifecycle of the harness is not drawn; an interim note that is the
answer is not drawn twice; markdown never reaches a screen as markers; a figure line is built from the fields that exist; the closing is the answer, one outcome line and the
command that resumes, alone on its own line so it can be copied.

A handful of glyphs and three meanings of colour (the person's words, the state of a step, quiet detail) are used everywhere. Colour is 256-colour codes readable on a dark
screen at 4.5:1 and never SGR 2 (faint is drawn at a strength each terminal chooses). Standard library only."""
from __future__ import annotations

import re
import textwrap
from typing import Any, Dict, List, Optional, Sequence, Tuple

from hubofhubs.the_consciousness.ai_session_experience.session_events import MAIN, Step, short
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import hub_lines

PRODUCT = "AI Hub of Hubs Structure"        # the repository's title and the expansion of the command name ahohs (README.md)
CEILING_SHARE = 0.5                          # a ceiling is named in the header only once this share of it is used
GLYPHS = {"running": "●", "done": "✓", "failed": "✗", "blocked": "⊘", "waiting": "?", "stopping": "◌", "stopped": "■", "met": "✓", "unmet": "◐", "finished": "✓", "idle": "○"}
GOAL_GLYPH = "❯"
HELPER_GLYPH = "↳"
GREEN, RED, AMBER, CYAN, GREY, RESET = "\x1b[38;5;77m", "\x1b[38;5;203m", "\x1b[38;5;221m", "\x1b[1;38;5;80m", "\x1b[38;5;245m", "\x1b[0m"
STATE_COLOR = {"running": AMBER, "done": GREEN, "failed": RED, "blocked": RED, "waiting": AMBER, "stopping": AMBER, "stopped": AMBER, "met": GREEN, "unmet": AMBER, "finished": GREEN,
               "idle": GREY}
HARNESS_WORDS = {"native": "native worker", "stream": "Claude Code worker", "loop": "solution loop", "adaptive": "adaptive worker", "solution_agents": "solution agents"}
LIFECYCLE = re.compile(r"^(starting the session|session started|session ended|resuming the session|session resumed)$", re.I)
SGR = re.compile(r"\x1b\[[0-9;]*m")


def plain(text: str) -> str:
    return SGR.sub("", text)


def visible(text: str) -> int:
    return len(plain(text))


def paint(text: str, color: str, on: bool) -> str:
    return f"{color}{text}{RESET}" if on and color and text else text


# --- markdown ------------------------------------------------------------------------------------------------------------------------

def strip_markdown(text: str) -> str:
    """The words of ``text`` with the markdown markers taken out: emphasis, code, headings, fences and links (a link keeps its words and its address), bullets as dots."""
    out = []
    for line in str(text or "").splitlines():
        if line.strip().startswith("```"):
            continue
        line = re.sub(r"^\s{0,3}#{1,6}\s+", "", line)
        line = re.sub(r"^(\s*)[-*+]\s+", r"\1• ", line)
        line = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"\1 (\2)", line)
        line = re.sub(r"`([^`]+)`", r"\1", line)
        line = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: m.group(1) or m.group(2), line)
        line = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", r"\1", line)
        line = re.sub(r"(?<![\w_])_([^_\s][^_]*)_(?![\w_])", r"\1", line)
        out.append(line.rstrip())
    return "\n".join(out).strip()


def one_line(text: str) -> str:
    return " ".join(strip_markdown(text).split())


def squash(text: str) -> str:
    return re.sub(r"\s+", " ", strip_markdown(text)).strip().rstrip(".…").strip().lower()


def is_the_answer(note: str, answer: str) -> bool:
    """True when ``note`` is the answer or its beginning (a harness shortens the note it reports), so showing both would draw the same words twice."""
    a, n = squash(answer), squash(note)
    return bool(a and n) and (a.startswith(n) or n.startswith(a) or n in a)


# --- figures -------------------------------------------------------------------------------------------------------------------------

def cost_text(cost: Optional[float]) -> str:
    """Dollars at cent precision; a cost under a cent is ``<$0.01``; unknown is said, never shown as zero."""
    if cost is None:
        return "cost unknown"
    if cost <= 0:
        return "$0.00"
    return "<$0.01" if cost < 0.005 else f"${cost:.2f}"


def count_text(count: Optional[int], singular: str, plural: str = "") -> str:
    """``2 calls``, ``1,350 tokens``; empty when the value is missing (the segment is dropped, never drawn without its number)."""
    if not count:
        return ""
    return f"{count:,} {singular if count == 1 else (plural or singular + 's')}"


def fit_parts(text: str, width: int, sep: str = " | ") -> str:
    """The parts of ``text`` that fit ``width`` whole, the last ones dropped first (a hint is never cut in half)."""
    parts = text.split(sep)
    while len(parts) > 1 and len(sep.join(parts)) > width:
        parts.pop()
    return sep.join(parts)


def join(parts: Sequence[str], sep: str = " · ") -> str:
    return sep.join(p for p in parts if p)


def ceilings_in_view(view: Any) -> Tuple[str, str]:
    """``(time ceiling text, spend ceiling text)``, each empty until its own ceiling is at least half used."""
    when = spent = ""
    if view.ceiling_seconds and view.elapsed() / view.ceiling_seconds >= CEILING_SHARE:
        when = f"of {hub_lines.clock(view.ceiling_seconds)}"
    if view.ceiling_usd and view.cost_usd is not None and view.cost_usd / view.ceiling_usd >= CEILING_SHARE:
        spent = f"of {cost_text(view.ceiling_usd)}"
    return when, spent


# --- the header ----------------------------------------------------------------------------------------------------------------------

def state_of(view: Any) -> str:
    done = view.final
    if view.status == "finished" and done is not None:
        return {"met": "met", "unmet": "unmet", "stopped": "stopped", "failed": "failed"}.get(done.outcome, "finished")
    return view.status if view.status in GLYPHS else "running"


def header(view: Any, width: int = 0, color: bool = False, segments: Sequence[str] = (), title: str = "") -> str:
    """One line: the state glyph, the product's name, the worker in plain words and who the AI acts for on the left; the time and the cost right-aligned (a ceiling only once it is
    half used). On a narrow terminal the least important parts go first (ceilings, the worker, who it acts for, extra segments, the cost) and the line never wraps."""
    state = state_of(view)
    when_ceiling, spend_ceiling = ceilings_in_view(view)
    elapsed = join([hub_lines.clock(view.elapsed()), when_ceiling], " ")
    spent = join([cost_text(view.cost_usd), spend_ceiling], " ")
    worker = HARNESS_WORDS.get(view.harness, view.harness or "")
    acting = f"for {view.acting_for}" if view.acting_for else ""
    extra = [s for s in segments if s]
    ladder = [(worker, acting, extra, elapsed, spent), (worker, acting, extra, hub_lines.clock(view.elapsed()), cost_text(view.cost_usd)),
              ("", acting, extra, hub_lines.clock(view.elapsed()), cost_text(view.cost_usd)), ("", "", [], hub_lines.clock(view.elapsed()), cost_text(view.cost_usd)),
              ("", "", [], hub_lines.clock(view.elapsed()), "")]
    mark = paint(GLYPHS[state], STATE_COLOR.get(state, ""), color)
    for worker_, acting_, extra_, when_, spent_ in ladder:
        left = f"{mark} {title or PRODUCT}" + "".join(f" · {p}" for p in [worker_, acting_] + extra_ if p)
        right = join([when_, spent_])
        gap = 2 if not width else width - visible(left) - visible(right) - 1
        if not width or gap >= 2:
            return left + " " * max(gap, 2) + right
    return f"{mark} {title or PRODUCT}"[:max(width - 1, 20)]


# --- steps and rows --------------------------------------------------------------------------------------------------------------------

PHRASES = {   # kind -> (present, done, failed): a plain verb phrase for each state, said of a label
    "read": ("Reading {}", "Read {}", "Could not read {}"),
    "edit": ("Editing {}", "Edited {}", "Could not edit {}"),
    "run": ("Running {}", "Ran {}", "Command failed: {}"),
    "check": ("Checking {}", "Checked {}", "Check failed: {}"),
    "tool": ("Using {}", "Used {}", "Could not use {}"),
    "delegate": ("Handing off {}", "Handed off {}", "Could not hand off {}"),
    "note": ("{}", "{}", "{}"),
}


def step_phrase(step: Step) -> str:
    """A person's words for one step: ``Ran date``, ``Edited notes.md``, ``Could not read a.txt`` (never the raw kind word)."""
    kinds = PHRASES.get(step.kind, ("{}", "{}", "{}"))
    index = 0 if step.state == "running" else 2 if step.state == "failed" else 1
    text = kinds[index].format(one_line(step.label))
    return text if step.kind in PHRASES else one_line(step.label or step.kind)


def step_line(step: Step, color: bool = False, who: str = "") -> str:
    """One row for a step: its glyph and phrase (a refused one says why); a helper's step names the helper after a dot."""
    glyph = paint(GLYPHS.get(step.state, GLYPHS["running"]), STATE_COLOR.get(step.state, ""), color)
    if step.kind == "message-received":
        return f"{glyph} Your note was taken up: {short(one_line(step.label), 70)}"
    phrase = step_phrase(step)
    if step.state == "blocked":
        phrase = f"Refused: {phrase}" + (f" ({short(one_line(step.detail), 60)})" if step.detail else "")
    return f"{glyph} {short(phrase, 90)}" + (f" · {who}" if who else "")


def is_lifecycle(step: Step) -> bool:
    return step.kind == "note" and bool(LIFECYCLE.match(one_line(step.label).strip()))


def goal_line(goal: str, resumed: bool = False, color: bool = False, width: int = 0) -> List[str]:
    """The person's goal as their own message: a prompt glyph and their words, wrapped under the words."""
    text = one_line(goal)
    lead = f"{paint(GOAL_GLYPH, CYAN, color)} "
    rows = wrap(paint(text, CYAN, color), width, lead, "  ") if width else [lead + paint(text, CYAN, color)]
    return rows + (["  continuing the earlier session"] if resumed else [])


def wrap(text: str, width: int, first: str = "", hang: str = "  ") -> List[str]:
    """``text`` wrapped at word boundaries to ``width`` columns, the first row led by ``first`` and the others hung by ``hang``; escape codes take no room."""
    if not width:
        return [first + text]
    if visible(first) + visible(text) <= width:
        return [first + text]
    bare = plain(text)
    pieces = textwrap.wrap(bare, max(width - visible(first), 10), subsequent_indent="", break_long_words=False, break_on_hyphens=False) or [bare]
    colored = text != bare
    start = text[:text.index(bare[0])] if colored and bare else ""
    end = RESET if colored else ""
    return [(first if i == 0 else hang) + (start + p + end if colored else p) for i, p in enumerate(pieces)]


# --- the closing ---------------------------------------------------------------------------------------------------------------------------

OUTCOME_WORDS = {"met": "Goal met", "unmet": "Goal not met", "stopped": "Stopped, your work is kept", "failed": "Failed"}


def files_phrase(files: Sequence[str]) -> str:
    return "no files changed" if not files else f"{len(files)} file{'' if len(files) == 1 else 's'} changed"


def outcome_line(view: Any, color: bool = False) -> str:
    """The one closing line: how it ended, the time, the cost, the calls and the files, each only when there is something to say."""
    return join(outcome_parts(view, color))


def outcome_rows(view: Any, color: bool = False, width: int = 0) -> List[str]:
    """The closing line as rows: it breaks only between its parts (never inside one), the next row hung under the first."""
    parts = [p for p in outcome_parts(view, color) if p]
    if not width:
        return [join(parts)]
    rows: List[str] = []
    for part in parts:
        if not rows:
            rows.append(part)
        elif visible(rows[-1]) + 3 + visible(part) <= width:
            rows[-1] += " · " + part
        else:
            rows.append("  " + part)
    return rows


def outcome_parts(view: Any, color: bool = False) -> List[str]:
    done = view.final
    outcome = done.outcome if done is not None else view.status
    state = {"met": "met", "unmet": "unmet", "stopped": "stopped", "failed": "failed"}.get(outcome, "finished")
    lead = paint(f"{GLYPHS[state]} {OUTCOME_WORDS.get(outcome, outcome)}", STATE_COLOR.get(state, ""), color)
    when_ceiling, spend_ceiling = ceilings_in_view(view)
    elapsed = join([hub_lines.clock(view.elapsed()), when_ceiling], " ")
    return [lead, elapsed, join([cost_text(view.cost_usd), spend_ceiling], " "), count_text(view.calls, "call"), count_text(view.tokens, "token"), files_phrase(view.changed())]


def resume_lines(view: Any) -> List[str]:
    """The line that says what the next one is, and the command alone on its own line (never wrapped by us, so it can be copied)."""
    if not (view.session_id and view.command):
        return []
    return ["Continue this session later, in this folder:", hub_lines.resume_command(view.harness, view.session_id, view.command)]
