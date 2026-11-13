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

from hubofhubs.the_consciousness.ai_session_experience.session_events import MAIN, Step, is_bookkeeping, short
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import hub_lines

PRODUCT = "AI Hub of Hubs Structure"        # the repository's title and the expansion of the command name ahohs (README.md)
CEILING_SHARE = 0.5                          # a ceiling is named in the header only once this share of it is used
GLYPHS = {"running": "●", "done": "✓", "failed": "✗", "blocked": "⊘", "waiting": "?", "stopping": "◌", "stopped": "■", "met": "✓", "unmet": "◐", "finished": "✓", "idle": "○"}
#: The words the four views share, in one place and in sentence case (the metric ``terminal_presentation`` reads every screen against its capitalisation policy). A key's name keeps its own capital (Esc, Tab, Enter).
TEXT = {
    "structure": "Structure", "agents": "Agents", "helper": "Helper",
    "prompt_goal": "Type a goal, or / for commands", "prompt_goal_enter": "Type a goal and press Enter",
    "keys_default": "Esc stop | Type + Enter to steer | Tab structure | ? keys",
    "keys_waiting": "Y approve | N refuse | Esc stop",
    "keys_stopping": "Stopping, the session is kept",
    "keys_stopped": "Type resume to continue, or quit to leave",
    "notes_waiting": "{count} note{s} waiting, read after the current step",
    "no_structure": "No solution is named for this run yet, so there is no structure to show (give one with --solution).",
    "structure_hint": "Structure (Up and Down move, Right opens a solution's fields, Left closes, Tab hides)",
    "structure_tab": "(Tab shows the tree)",
}
KEY_SPECIAL = {"pgup": "PgUp", "pgdn": "PgDn"}


def key_name(key: str) -> str:
    """A key as it is written on a screen: each part capitalised (``alt+d`` is ``Alt+D``, ``up/down`` is ``Up/Down``, ``pgup/pgdn`` is ``PgUp/PgDn``)."""
    return re.sub(r"[A-Za-z0-9]+", lambda m: KEY_SPECIAL.get(m.group(0).lower(), m.group(0).capitalize() if len(m.group(0)) > 1 else m.group(0).upper()), key)


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
    "search": ("Searching {}", "Searched {}", "Could not search {}"),
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
    text = kinds[index].format(subject_of(step))
    return text if step.kind in PHRASES else one_line(step.label or step.kind)


SUBJECT_CHARS = 40


def shorten_path(path: str, chars: int = SUBJECT_CHARS) -> str:
    """A path as a person reads it: a home-folder or absolute path loses its leading folders, and a long one keeps its first folder and its file name with an ellipsis between
    (``stories/…/evidence_ledger.md``), at most about ``chars`` characters; a file name too long for that is cut at its start. Anything that is not a path is cut at a word boundary."""
    text = one_line(path)
    if not text or " " in text or "/" not in text:
        return clip_words(text, chars)
    parts = [p for p in text.replace("~/", "").split("/") if p]
    if text.startswith(("/", "~")) and len(parts) > 2:
        parts = parts[-3:] if len(parts) > 3 else parts
        text = "…/" + "/".join(parts)
    if len(text) <= chars:
        return text
    name = parts[-1]
    first = parts[0] if parts[0] != "…" and len(parts) > 1 else ""
    for lead in ([first] if first else []) + [""]:
        tidy = f"{lead}/…/{name}" if lead else f"…/{name}"
        if len(tidy) <= chars:
            return tidy
    return "…" + name[-(chars - 1):]


def subject_of(step: Step) -> str:
    """What a step was about, short: a file or a place as ``shorten_path``, a command or a pattern cut at a word boundary."""
    if step.kind in ("read", "edit", "search"):
        return shorten_path(step.label)
    if step.kind in ("run", "check"):
        return command_subject(step.label)
    return clip_words(one_line(step.label), 70)


def command_subject(command: str, chars: int = 60) -> str:
    """A command as a person reads it in a feed: a leading ``cd <folder> &&`` is left off (the folder is where the work is), each long absolute path is shortened, and the rest is cut at a word."""
    text = one_line(command)
    text = re.sub(r"^(?:cd\s+\S+\s*(?:&&|;)\s*)+", "", text) or text
    text = re.sub(r"(?<![\w.])(?:~|/)[^\s'\";|&]+", lambda m: shorten_path(m.group(0), 28), text)
    return clip_words(text, chars)


def helper_name(task: str, chars: int = 40) -> str:
    """A helper's name: the first sentence of its brief, cut at a word boundary (never mid-word)."""
    text = one_line(task)
    first = re.split(r"(?<=[.!?])\s|\s[-–]\s", text, maxsplit=1)[0] if text else ""
    return clip_words(first.rstrip(".!?"), chars)


def helper_marker(view: Any, agent_id: str) -> str:
    """The short marker a helper's rows carry in place of its name (``↳``, the one the breadcrumb and the agents list use); the name is said once, when the helper starts."""
    return HELPER_GLYPH if agent_id and agent_id != MAIN else ""


def clip_words(text: str, chars: int) -> str:
    """``text`` cut at a word boundary to at most ``chars`` characters, with an ellipsis only when something was cut (never mid-word, never ``Find one interesting find...``)."""
    one = " ".join(str(text or "").split())
    if len(one) <= chars:
        return one
    room = max(chars - 1, 1)
    cut = one[:room + 1]
    head = cut[:room] if cut[room:room + 1] == " " else cut[:room].rsplit(" ", 1)[0] if " " in cut[:room] else cut[:room]
    return head.rstrip(" ,;:-") + "…"


#: What a failed shell command was after, from its first word, in a few plain words (the raw text of a long shell loop never reaches the feed).
RUN_WORDS = (("ls", "list files"), ("find", "look for files"), ("grep", "search the text"), ("rg", "search the text"), ("cat", "read a file"), ("head", "read a file"), ("tail", "read a file"),
             ("sed", "read a file"), ("wc", "count lines"), ("git", "check the repository"), ("python", "run a script"), ("python3", "run a script"), ("node", "run a script"),
             ("npm", "run a project command"), ("curl", "fetch a page"), ("wget", "fetch a page"), ("mkdir", "make a folder"), ("cp", "copy a file"), ("mv", "move a file"),
             ("rm", "remove a file"), ("for", "go through several files"), ("while", "go through several files"), ("pytest", "run the tests"), ("make", "run a build"))


def tried_words(command: str) -> str:
    """The few plain words for what a command tried (``list files``), from the command's first real word (a leading ``cd x &&`` and variable settings are skipped)."""
    text = one_line(command)
    for part in re.split(r"\s*(?:&&|;|\|\||\|)\s*", text):
        words = part.split()
        while words and ("=" in words[0] and not words[0].startswith(("-", "="))):
            words = words[1:]
        if words and words[0] in ("cd", "export", "set", "true", "echo", "pushd"):
            continue
        if words:
            name = words[0].rsplit("/", 1)[-1]
            return dict(RUN_WORDS).get(name, "run a command")
    return "run a command"


def is_status(step: Step) -> bool:
    """A helper's live ``now`` row (its latest activity): it belongs to the agent's row, which names it once, so it is never a feed row of its own."""
    return step.kind == "tool" and step.step_id.endswith("-now")


def is_bookkeeping_step(step: Step) -> bool:
    return is_bookkeeping(step.kind, step.label)


def is_failed_command(step: Step) -> bool:
    """A shell command or check that did not work or that the permission mode refused: the agent usually works around it, so it is one muted line (``failed_line``)."""
    return step.kind in ("run", "check") and step.state in ("failed", "blocked")


def refusal_words(detail: str) -> str:
    """The plain sentence for a command the harness would not run, whatever client draws it: a path outside the working folder (the hub's fence, or the CLI's own) is ``not allowed in this
    folder``; anything else the permission mode could not check in advance (quoted text, a loop) is ``could not be checked``. The raw refusal text stays in the step's detail."""
    low = (detail or "").lower()
    if "you refused" in low:
        return "A command was not run because you refused it"
    if "nobody answered" in low or "before you answered" in low:
        return "A command was not run because it was not answered"
    if any(mark in low for mark in ("outside the working folder", "outside the folder", "was blocked", "not allowed", "outside of")):
        return "Skipped a command that was not allowed in this folder"
    return "Skipped a command that could not be checked"


def failed_line(step: Step, color: bool = False, who: str = "", times: int = 1, detail: bool = False) -> str:
    """A command that did not work, as one muted line: what was tried in a few words and that it did not work (or was not allowed), counted when the same thing keeps failing.
    With ``detail`` the command's own text follows (where a view offers the detail of an agent); everywhere else it stays in the step's ``label``."""
    again = " again" if times > 1 else ""
    count = f" ({times} times)" if times > 1 else ""
    what = ("Tried to " + tried_words(step.label)) if step.kind == "run" else "A check"
    if step.state == "blocked":      # the permission mode could not check it in advance: said in plain words, never as the mode's own refusal text
        text = "○ " + refusal_words(step.detail) + count
    else:
        text = f"○ {what}{again}, did not work{count}" if step.kind == "run" else f"○ A check did not work{count}"
    text += f": {clip_words(one_line(step.label), 100)}" if detail and step.label else ""
    return paint((f"{HELPER_GLYPH} " if who else "") + text, GREY, color)


def step_line(step: Step, color: bool = False, who: str = "", times: int = 1, detail: bool = False) -> str:
    """One row for a step: its glyph and phrase (a refused one says why); a helper's step begins with the helper marker (its name is said once, when it starts). A failed command is one
    muted line (``failed_line``)."""
    mark = f"{HELPER_GLYPH} " if who else ""
    glyph = paint(GLYPHS.get(step.state, GLYPHS["running"]), STATE_COLOR.get(step.state, ""), color)
    if step.kind == "message-received":
        return f"{glyph} Your note was taken up: {clip_words(one_line(step.label), 70)}"
    if is_failed_command(step):
        return failed_line(step, color, who, times, detail)
    phrase = step_phrase(step)
    if step.state == "blocked":
        phrase = f"Refused: {phrase}" + (f" ({clip_words(one_line(step.detail), 60)})" if step.detail else "")
    return f"{mark}{glyph} {clip_words(phrase, 90)}"


# --- consecutive steps of one kind as one line ---------------------------------------------------------------------------------------------

GROUP_WORDS = {"read": ("Read", "file", "files"), "search": ("Searched", "place", "places"), "run": ("Ran", "command", "commands"), "edit": ("Edited", "file", "files")}


def group_key(step: Step) -> Optional[Tuple[str, str]]:
    """The key steps are grouped by (kind, agent), or None for a step that stands alone (running, refused, a note, a delegation, a failed command)."""
    if step.state == "failed" and step.kind in ("read", "search"):
        return ("skipped", step.agent_id)
    if step.state == "done" and step.kind in GROUP_WORDS:
        return (step.kind, step.agent_id)
    return None


def activity_rows(view: Any, width: int = 80) -> List[str]:
    """A compact live summary for a screen that draws each step as its own entry: the counts of what was done so far (``Read 4 files, Searched 2 places``), then the helper that is running,
    by name. No paths, no commands and nothing the entries already say; empty before anything happened or once the run has ended."""
    if view.final is not None or view.status not in ("running", "waiting", "stopping"):
        return []
    steps = [s for s in view.steps.values() if s.kind != "note" and not is_lifecycle(s) and not is_status(s) and s.kind != "delegate"]
    running = [s for s in steps if s.state == "running"]
    counts: Dict[str, int] = {}
    for step in steps:
        if step.state == "done" and step.kind in GROUP_WORDS:
            counts[step.kind] = counts.get(step.kind, 0) + 1
    rows: List[str] = []
    done =", ".join(f"{GROUP_WORDS[kind][0]} {n} {GROUP_WORDS[kind][1] if n == 1 else GROUP_WORDS[kind][2]}" for kind, n in counts.items())
    if done:
        rows.append(clip_words("Done so far: " + done, max(width, 20)))
    for agent in view.agents.values():
        if agent.state == "running":
            rows.append(clip_words(f"{HELPER_GLYPH} Helper: {helper_name(agent.task)}" + (f" · {one_line(agent.activity)}" if agent.activity else ""), max(width, 20)))
    return rows


def group_runs(steps: Sequence[Step]) -> List[List[Step]]:
    """``steps`` as runs of consecutive steps with the same group key; every other step is a run of its own."""
    out: List[List[Step]] = []
    last: Optional[Tuple[str, str]] = None
    for step in steps:
        key = group_key(step)
        if key is not None and key == last:
            out[-1].append(step)
        else:
            out.append([step])
        last = key
    return out


def group_line(steps: Sequence[Step], color: bool = False, who: str = "", times: int = 1) -> str:
    """One row for a run of steps: ``Read 5 files: a.md, b.md and 3 more``, ``Ran 3 commands``, ``Searched 2 places``; failed reads fold into one muted ``Skipped 3 files that were not
    available``. A run of one is the step's own row. The helper marker leads a helper's row. The individual rows stay one level down (the helper's own view lists every step)."""
    first = steps[0]
    key = group_key(first)
    mark = f"{HELPER_GLYPH} " if who else ""
    if key is not None and key[0] == "skipped":
        count = len(steps)
        text = "○ Skipped a file that was not available" if count == 1 else f"○ Skipped {count} files that were not available"
        return paint(mark + text, GREY, color)
    if len(steps) == 1 or key is None:
        return step_line(first, color, who, times)
    verb, _, plural = GROUP_WORDS[key[0]]
    names: List[str] = []
    for step in steps:
        name = shorten_path(step.label, 24).rsplit("/", 1)[-1] if key[0] in ("read", "edit") else clip_words(one_line(step.label), 20) if key[0] == "search" else ""
        if name and name not in names:
            names.append(name)
    shown = names[:2]
    more = len(names) - len(shown)
    subject = (": " + ", ".join(shown) + (f" and {more} more" if more > 0 else "")) if shown else ""
    glyph = paint(GLYPHS["done"], STATE_COLOR["done"], color)
    return f"{mark}{glyph} " + clip_words(f"{verb} {len(steps)} {plural}{subject}", 90)


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

OUTCOME_WORDS = {"met": "Goal met", "unmet": "Goal not met", "stopped": "Stopped", "failed": "Failed"}
LIMIT_FLAGS = {"spend": ("--max-spend", "<dollars>", "spend"), "time": ("--max-time", "<time>", "time")}


def stop_headline(view: Any) -> str:
    """``Stopped`` or, for a run the hub stopped at a ceiling, ``Stopped at the spend limit of $20.00`` (the ceiling's size only when it is known)."""
    what = getattr(view, "hard_limit", "")
    if what not in LIMIT_FLAGS:
        return "Stopped at its limit" if what else OUTCOME_WORDS["stopped"]
    size = cost_text(view.ceiling_usd) if what == "spend" and view.ceiling_usd else hub_lines.clock(view.ceiling_seconds) if what == "time" and view.ceiling_seconds else ""
    return f"Stopped at the {what} limit" + (f" of {size}" if size else "")


def stop_lines(view: Any) -> List[str]:
    """What to read once when a run ended stopped: that finished work is kept, how to continue and, for a ceiling, how to raise it. The only place a stop is explained."""
    what = getattr(view, "hard_limit", "")
    lines = ["Finished work is kept. Type resume to continue."]
    if what in LIMIT_FLAGS:
        flag, example, noun = LIMIT_FLAGS[what]
        lines.append(f"Raise the {noun} limit with {flag} {example}.")
    return lines


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
    words = stop_headline(view) if outcome == "stopped" else OUTCOME_WORDS.get(outcome, outcome)
    lead = paint(f"{GLYPHS[state]} {words}", STATE_COLOR.get(state, ""), color)
    when_ceiling, spend_ceiling = ceilings_in_view(view)
    elapsed = join([hub_lines.clock(view.elapsed()), when_ceiling], " ")
    return [lead, elapsed, join([cost_text(view.cost_usd), spend_ceiling], " "), count_text(view.calls, "call"), count_text(view.tokens, "token"), files_phrase(view.changed())]


def resume_lines(view: Any) -> List[str]:
    """The line that says what the next one is, and the command alone on its own line (never wrapped by us, so it can be copied)."""
    if not (view.session_id and view.command):
        return []
    return ["Continue this session later, in this folder:", hub_lines.resume_command(view.session_id, view.command)]
