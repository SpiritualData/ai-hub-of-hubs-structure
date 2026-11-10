"""The hub as its own harness: a small tool loop over a pure text completion, with no model or provider knowledge.

Role: an external coding agent spends most of its calls and tokens finding things and carrying a growing transcript. This loop spends
fewer and smaller calls. Before the first call it maps the working folder and puts the files that matter in view; every call's prompt is
rebuilt from the goal, the folder map, the current text of the files in view and a compact history (never appended to), so an edited file is
shown once, current. The model replies with text that holds actions; this code runs them and the loop repeats until the work is finished.

The reply protocol (parsed leniently, in order of appearance): ``READ: <path>``, SEARCH/REPLACE edit blocks (the vendored Aider format of
``file_editing.editblock``), ``RUN: <command>``, ``CHECK: <command>``, ``DELEGATE: <subtask>``, ``USE: <name> <input>`` (a ``Tool`` the caller
handed in), ``NOTE: <line>``, ``REPORT:`` (to the end of the text or to a line ``END REPORT``) and ``BLOCKED: <reason>``.

A run can continue an earlier one: ``save`` receives a ``LoopState`` after every call's actions, and ``state`` starts a run from one. A person can
steer a running loop: ``inbox`` is polled before each call and each message goes into the history, where the next prompt shows it in full; a
report is not accepted in a call during which a message arrived unseen.

When the loop ends met: a call has a REPORT and every action in it succeeded (an edit applied, a file read, a command not refused, a
delegated part met) and, when it ran commands, its CHECK exited 0. A call with RUN commands and a REPORT but no CHECK is accepted only when
every RUN exited 0 (the assumption: the model saw nothing surprising in its own commands). A reply that only reads files and reports is not
accepted, since the report was written before the files were seen; the same holds for a reply that only uses a tool and reports. The first reply may be a plain answer from the files in view.

The completion is injected (``complete(system, prompt) -> text``), so the loop is tested with a stub. Standard library and the hub only.
"""
from __future__ import annotations

import json
import os
import re
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_world.tools.command_running import clip, run_command
from hubofhubs.the_world.tools.file_editing.editblock import (DIVIDER, HEAD, UPDATED, apply_edit, find_original_update_blocks,
                                                              find_similar_lines)
from hubofhubs.the_world.tools.file_reading.read_files import inside

SKIPPED_FOLDERS = (".git", "__pycache__", "node_modules")
MAP_ENTRIES = 300
REVIEW_PROSE = "prose"            # ``review`` value: review every written text, not only one in which the code check found something
COMMON_WORDS = frozenset("this that with from have will your what which when where there their them then than they into every each about folder file files using write make report tell goal should must also only does done after before been were being more most some such very just like over under between".split())
PROSE_SUFFIXES = ("", ".md", ".txt", ".rst", ".adoc", ".html", ".htm")
MAP_FILE_LIMIT = 200_000          # a larger file is not listed or put in view at launch (READ can still show its start)
SNAPSHOT_FILES = 5000
OLD_RESULT_CHARS = 300
COMMAND_LIMIT = 4000
REPORT_DELEGATE_CHARS = 600
MESSAGE_LINE = "MESSAGE FROM THE PERSON (follow it; it overrides the plan so far): "
MESSAGE_ADVICE = "A message from the person arrived while you worked, so your REPORT was not accepted. Answer the message, then report again."
NO_ACTION_ADVICE = ("Your last reply used none of the actions. Reply with READ:, RUN:, CHECK:, edit blocks or DELEGATE: lines to do the work, "
                    "or REPORT: when it is finished, or BLOCKED: when it cannot be done.")

SYSTEM = """You work in one folder. The files in view are current and complete; the folder map lists the rest, and marks each file you have not seen. Never report on, summarise or cite a file that is not in view: READ it first. Act by writing these lines, each on its own line, anywhere in your reply:
READ: <path>     show a file from the folder (several lines allowed)
RUN: <command>   run a shell command in the folder (several allowed)
CHECK: <command> your acceptance check for the whole task, run after all other actions
NOTE: <one line> something you want to remember for the next reply
REPORT: <text>   the final report; everything after it to the end of the reply (or to a line END REPORT) is the report
BLOCKED: <reason> the task cannot be done
{delegate}{tools}To change or create a file write an edit block, the path on its own line, then:

src/app.py
<<<<<<< SEARCH
lines exactly as they are now
=======
the lines they become
>>>>>>> REPLACE

A new file uses an empty SEARCH section. Copy SEARCH lines exactly from the files in view.

How to work: several actions per reply are welcome and preferred. Read everything you need at once and make all edits at once. Do the work fully in as few replies as possible. When the task has a way to check itself (tests, or a rubric you can verify with a command), put that command in CHECK with your REPORT in the same reply; if CHECK exits 0 the work ends there. The REPORT states concretely what you found or changed and answers the goal directly, restating every fact the goal asks for. When the goal asks you to write a document, begin your reply with a section headed REQUIREMENTS: a numbered list of (a) each separate thing the goal asks for, in the form it asks for, and (b) each limit, deadline, rule or instruction any file states that the document has to respect (a word limit someone set, a date, a thing someone said not to do), naming the file. For each limit, find the current amount in the files and state the room left, with the arithmetic (a limit of 500 with 420 used leaves 80), and plan inside it. Read every file in view for these before you list them. Then write the document so that every number is met, and say in the REPORT how each one is met. Deliver every part the goal asks for: when the files do not settle a part, build it from what they do say and mark it as a proposal, and never invent a figure, name, date or source. Never change files the goal did not ask you to change. Never claim what you did not do."""
REVIEW_SYSTEM = """You review finished work against its goal. You did not do the work. The files shown are current. Reply in this order:

REQUIREMENTS: a numbered list of (a) each separate thing the goal asks for, in the form it asks for, and (b) each limit, deadline, rule or instruction the other files state that the work has to respect (a word limit someone set, a date, a thing someone said not to do).
VERDICTS: for each number, "met" or "not met", with the place in the written files that shows it.
UNSUPPORTED: each figure, name, date, quotation and claim in the written files that is not found in the other files shown, and each citation whose source does not exist or does not say that. Write "none" when there is none.

Then, if every requirement is met and nothing is unsupported, end with the single word OK. Otherwise correct the written files with edit blocks: add what is asked for and missing, make the work respect each limit, and remove what the files do not support or mark it plainly as a proposal or as open. When the goal asks for something the sources do not settle, the work still delivers it, built from what the sources do say and marked as a proposal; a refusal to deliver is a requirement not met. An edit block is the path on its own line, then:

path/to/file.md
<<<<<<< SEARCH
lines exactly as they are now
=======
the lines they become
>>>>>>> REPLACE

Copy SEARCH lines exactly. Keep everything that is right as it is."""
DELEGATE_LINE = "DELEGATE: <subtask> hand one separate part of the work to a helper that starts fresh in the same folder; you get its short report back\n"

MARKER = re.compile(r"^[\s>*`#-]*(READ|RUN|CHECK|DELEGATE|NOTE|BLOCKED)\s*:\**\s*(.*?)\s*$")
TOOL_MARKER = re.compile(r"^[\s>*`#-]*(READ|RUN|CHECK|DELEGATE|USE|NOTE|BLOCKED)\s*:\**\s*(.*?)\s*$")
REPORT_START = re.compile(r"^[\s>*`#-]*REPORT\s*:\**\s*(.*)$")
REPORT_END = re.compile(r"^[\s>*`#-]*END REPORT\b")


class CallCounter:
    """The model calls left for a whole tree of loops; ``take`` is atomic, so a parent and its children never overspend."""

    def __init__(self, limit: int):
        self.limit = int(limit)
        self.used = 0
        self.lock = threading.Lock()

    def take(self) -> bool:
        with self.lock:
            if self.used >= self.limit:
                return False
            self.used += 1
            return True

    def left(self) -> int:
        with self.lock:
            return max(self.limit - self.used, 0)


@dataclass
class LoopResult:
    """How a loop ended. ``calls`` counts the model calls of this loop and of the helpers it delegated to; ``changed`` and ``read`` are
    paths relative to the working folder; ``commands`` counts commands that ran; ``log`` holds one dict per call."""
    met: bool = False
    report: str = ""
    calls: int = 0
    changed: List[str] = field(default_factory=list)
    read: List[str] = field(default_factory=list)
    commands: int = 0
    error: str = ""
    log: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class Action:
    kind: str            # edit, read, run, check, delegate, use
    text: str = ""       # the path, command, subtask or "<tool name> <input>"
    search: str = ""
    replace: str = ""
    order: int = 0


@dataclass
class Reply:
    actions: List[Action] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    report: Optional[str] = None
    blocked: str = ""
    problems: List[str] = field(default_factory=list)


@dataclass
class Outcome:
    label: str
    ok: bool
    text: str = ""


@dataclass
class Tool:
    """An operation beyond the shell that the caller hands the loop: ``run(input)`` returns text. The hub knows none by name (a consumer's
    connected-system operations, a web search...)."""
    description: str
    run: Callable[[str], str]


@dataclass
class LoopState:
    """What is needed to continue a run: the goal, the history (call number, note, outcomes as label/ok/text, advice; never the raw replies, and
    a message from the person as ``{"message": text}``), the paths in view with their named flag, the changed and read paths and the calls used."""
    goal: str = ""
    entries: List[Dict[str, Any]] = field(default_factory=list)
    view: List[Tuple[str, bool]] = field(default_factory=list)
    changed: List[str] = field(default_factory=list)
    read: List[str] = field(default_factory=list)
    calls: int = 0

    def to_json(self) -> str:
        entries: List[Dict[str, Any]] = []
        for entry in self.entries:
            if "message" in entry:
                entries.append({"message": str(entry["message"])})
                continue
            entries.append({"call": int(entry.get("call", 0)), "note": str(entry.get("note") or ""), "advice": str(entry.get("advice") or ""),
                            "outcomes": [{"label": o.label, "ok": bool(o.ok), "text": o.text} for o in entry.get("outcomes", [])]})
        return json.dumps({"goal": self.goal, "entries": entries, "view": [[path, bool(named)] for path, named in self.view],
                           "changed": list(self.changed), "read": list(self.read), "calls": int(self.calls)}, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "LoopState":
        """The state ``to_json`` wrote. Raises ``ValueError`` for text that is not one."""
        try:
            data = json.loads(text)
            entries: List[Dict[str, Any]] = []
            for item in data.get("entries", []):
                if "message" in item:
                    entries.append({"message": str(item["message"])})
                    continue
                entries.append({"call": int(item["call"]), "note": str(item.get("note") or ""), "advice": str(item.get("advice") or ""), "reply": "",
                                "outcomes": [Outcome(str(o["label"]), bool(o["ok"]), str(o.get("text") or "")) for o in item.get("outcomes", [])]})
            return cls(goal=str(data.get("goal") or ""), entries=entries, view=[(str(p), bool(n)) for p, n in data.get("view", [])],
                       changed=[str(p) for p in data.get("changed", [])], read=[str(p) for p in data.get("read", [])], calls=int(data.get("calls", 0)))
        except (TypeError, KeyError, AttributeError, ValueError) as error:
            raise ValueError(f"not a saved loop state: {error}") from error


# --- the working folder ----------------------------------------------------------------------------------------------------------------

def walk(root: str, limit: int = SNAPSHOT_FILES) -> List[Tuple[str, int, float]]:
    """``(relative path, size, mtime)`` of the files under ``root``, shallow first, skipping version-control, cache, dependency and hidden folders."""
    found: List[Tuple[str, int, float]] = []
    for folder, names, files in os.walk(root):
        names[:] = sorted(n for n in names if n not in SKIPPED_FOLDERS and not n.startswith(".") and not os.path.islink(os.path.join(folder, n)))
        for name in files:
            full = os.path.join(folder, name)
            try:
                stat = os.stat(full)
            except OSError:
                continue
            found.append((os.path.relpath(full, root).replace(os.sep, "/"), stat.st_size, stat.st_mtime_ns))
            if len(found) >= limit:
                break
    return sorted(found, key=lambda f: (f[0].count("/"), f[0]))


def read_text(path: Path, limit: int = 2_000_000) -> Optional[str]:
    """The text of ``path``, or None when it is missing, too large, a directory or binary-looking."""
    try:
        if not path.is_file() or path.stat().st_size > limit:
            return None
        data = path.read_bytes()
        return None if b"\0" in data else data.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def listing(root: str) -> Tuple[List[Tuple[str, int]], str]:
    """The text files that fit ``MAP_FILE_LIMIT`` as ``(path, size)`` and the map text: one line per file (at most ``MAP_ENTRIES``) with a line
    saying how many were left out."""
    base = Path(root)
    texts = [(rel, size) for rel, size, _ in walk(root) if size <= MAP_FILE_LIMIT and read_text(base / rel) is not None]
    shown = texts[:MAP_ENTRIES]
    lines = [f"{rel} ({size} bytes)" for rel, size in shown] or ["(no files yet)"]
    if len(texts) > len(shown):
        lines.append(f"... {len(texts) - len(shown)} more files not listed")
    return texts, "\n".join(lines)


def mentions(text: str, name: str) -> bool:
    return re.search(r"(?<![\w.-])" + re.escape(name) + r"(?!\w)", text) is not None


class View:
    """The files in view, least recently used first. A named file (one the goal or context mentions) is never evicted."""

    def __init__(self, root: str, view_chars: int):
        self.root, self.view_chars = root, view_chars
        self.files: "OrderedDict[str, bool]" = OrderedDict()

    def start(self, files: Sequence[Tuple[str, int]], named_text: str) -> None:
        named = [rel for rel, _ in files if mentions(named_text, rel) or mentions(named_text, rel.rsplit("/", 1)[-1])]
        used = 0
        for rel in named:
            self.files[rel] = True
            used += self.size(rel)
        rest = [(rel, size) for rel, size in files if rel not in self.files]
        if used + sum(size for _, size in rest) <= self.view_chars:
            ranked = sorted(rest, key=lambda f: f[1])                       # the whole folder fits: everything is in view
        else:                                                               # it does not: only what the goal's own words point at
            words = {w for w in re.findall(r"[a-z0-9]{4,}", named_text.lower()) if w not in COMMON_WORDS}
            scored = [(self.relevance(rel, words), rel, size) for rel, size in rest]
            ranked = [(rel, size) for score, rel, size in sorted(scored, key=lambda f: (-f[0], f[2])) if score > 0]
        chosen: List[str] = []
        for rel, size in ranked:
            if used + size > self.view_chars:
                continue
            chosen.append(rel)
            used += size
        for rel in reversed(chosen):    # the first chosen end up the most recently used, so the last go first when space is needed
            self.files[rel] = False

    def relevance(self, rel: str, words: set) -> int:
        """How many of the goal's words a file's path (counted three times) and its first 2000 characters hold."""
        if not words:
            return 0
        text = read_text(Path(self.root) / rel) or ""
        path_words = set(re.findall(r"[a-z0-9]{4,}", rel.lower()))
        head_words = set(re.findall(r"[a-z0-9]{4,}", text[:2000].lower()))
        return 3 * len(words & path_words) + len(words & head_words)

    def size(self, rel: str) -> int:
        text = read_text(Path(self.root) / rel)
        return min(len(text), self.view_chars) if text is not None else 0

    def add(self, rel: str, named: bool = False) -> None:
        self.files[rel] = self.files.get(rel, False) or named
        self.files.move_to_end(rel)
        while sum(self.size(r) for r in self.files) > self.view_chars * 2:
            victim = next((r for r, keep in self.files.items() if not keep and r != rel), None)
            if victim is None:
                break
            del self.files[victim]

    def render(self) -> Tuple[str, List[str]]:
        """The text of the files in view as they are on disk now, and their paths."""
        parts: List[str] = []
        shown: List[str] = []
        for rel in list(self.files):
            text = read_text(Path(self.root) / rel)
            if text is None:
                continue
            shown.append(rel)
            if not text.strip():
                text = "(empty file)\n"
            elif len(text) > self.view_chars:
                text = text[:self.view_chars] + f"\n[the file goes on: {len(text) - self.view_chars} more characters; use RUN: sed -n to see them]\n"
            parts.append(f"=== {rel} ===\n{text if text.endswith(chr(10)) else text + chr(10)}")
        return "\n".join(parts) if parts else "(none)", shown


# --- the reply -------------------------------------------------------------------------------------------------------------------------

def parse_reply(text: str, tools: bool = False) -> Reply:
    """The actions in a reply, in order of appearance. The report (from ``REPORT:`` to the end or to ``END REPORT``) is cut out first so that
    nothing written inside it runs. ``USE:`` lines are actions only when ``tools`` is true."""
    marker = TOOL_MARKER if tools else MARKER
    lines = text.splitlines()
    reply = Reply()
    body: List[str] = []
    index = 0
    while index < len(lines):
        found = REPORT_START.match(lines[index])
        if found and reply.report is None:
            chunk = [found.group(1)]
            index += 1
            while index < len(lines) and not REPORT_END.match(lines[index]):
                chunk.append(lines[index])
                index += 1
            reply.report = "\n".join(chunk).strip()
            index += 1
            continue
        body.append(lines[index])
        index += 1
    spans: List[int] = []
    mask = [False] * len(body)
    head, divider, updated = re.compile(HEAD), re.compile(DIVIDER), re.compile(UPDATED)
    cursor = 0
    while cursor < len(body):
        if head.match(body[cursor].strip()):
            spans.append(cursor)
            end = cursor + 1
            while end < len(body) and not divider.match(body[end].strip()):
                end += 1
            end += 1
            while end < len(body) and not (updated.match(body[end].strip()) or divider.match(body[end].strip())):
                end += 1
            for k in range(cursor, min(end + 1, len(body))):
                mask[k] = True
            cursor = end + 1
        else:
            cursor += 1
    blocks: List[Tuple[str, str, str]] = []
    try:
        for item in find_original_update_blocks("\n".join(body) + "\n"):
            if len(item) == 3:
                blocks.append(item)
    except ValueError as error:
        reply.problems.append("an edit block is malformed: " + str(error).strip().splitlines()[-1])
    for position, (name, search, replace) in zip(spans, blocks):
        reply.actions.append(Action("edit", name, search, replace, order=position))
    for position, line in enumerate(body):
        if mask[position]:
            continue
        found = marker.match(line)
        if not found:
            continue
        kind, value = found.group(1).lower(), found.group(2)
        if len(value) > 1 and value.startswith("`") and value.endswith("`") and value.count("`") == 2:
            value = value[1:-1]
        if kind == "note":
            if value:
                reply.notes.append(value)
        elif kind == "blocked":
            reply.blocked = reply.blocked or value or "blocked"
        elif value:
            reply.actions.append(Action(kind, value, order=position))
    reply.actions.sort(key=lambda a: a.order)
    return reply


# --- the prompt ------------------------------------------------------------------------------------------------------------------------

def history_text(entries: Sequence[Mapping[str, Any]]) -> str:
    """One compact entry per earlier call. The latest call's results are shown in full, older ones clipped to ``OLD_RESULT_CHARS``."""
    if not entries:
        return "Nothing yet: this is your first reply."
    lines: List[str] = []
    last_call = max((position for position, entry in enumerate(entries) if "message" not in entry), default=-1)
    for position, entry in enumerate(entries):
        if "message" in entry:
            full = position > last_call
            lines.append(MESSAGE_LINE + (str(entry["message"]) if full else clip(str(entry["message"]), OLD_RESULT_CHARS)))
            continue
        latest = position == last_call
        lines.append(f"Call {entry['call']}:" + (f" NOTE: {entry['note']}" if entry.get("note") else ""))
        for outcome in entry["outcomes"]:
            text = outcome.text if latest else clip(outcome.text, OLD_RESULT_CHARS)
            lines.append(f"  {outcome.label}: {'ok' if outcome.ok else 'FAILED'}" + (f"\n{indent(text)}" if text.strip() else ""))
        if latest and entry.get("advice"):
            lines.append(f"  {entry['advice']}")
    return "\n".join(lines)


def indent(text: str) -> str:
    return "\n".join("    " + line for line in text.rstrip().splitlines())


def build_prompt(goal: str, context: str, folder_map: str, files_text: str, entries: Sequence[Mapping[str, Any]], note: str,
                 earlier_goal: str = "") -> str:
    parts = [f"GOAL:\n{goal.strip()}"]
    if earlier_goal.strip() and earlier_goal.strip() != goal.strip():
        parts.append(f"EARLIER GOAL:\n{earlier_goal.strip()}")
    if context.strip():
        parts.append(f"CONTEXT:\n{context.strip()}")
    parts += [f"FOLDER MAP (paths relative to the working folder):\n{folder_map}", f"FILES IN VIEW (current):\n{files_text}",
              f"WHAT HAS HAPPENED SO FAR:\n{history_text(entries)}"]
    if note:
        parts.append(note)
    return "\n\n".join(parts)


# --- running the actions ---------------------------------------------------------------------------------------------------------------

def snapshot(root: str) -> Dict[str, Tuple[int, float]]:
    return {rel: (size, mtime) for rel, size, mtime in walk(root)}


def short(text: str, chars: int = 120) -> str:
    one = " ".join(text.split())
    return one if len(one) <= chars else one[:chars - 3] + "..."


def apply_block(action: Action, root: str) -> Tuple[Outcome, bool]:
    """Apply one edit block. Returns the outcome and whether the file was written."""
    label = f"EDIT {action.text}"
    try:
        path = inside(Path(root), action.text)
    except (ValueError, OSError):
        return Outcome(label, False, f"{action.text!r} is outside the working folder; edits stay inside it"), False
    if path.is_dir():
        return Outcome(label, False, f"{action.text!r} is a folder"), False
    content = None
    if path.exists():
        content = read_text(path)
        if content is None:
            return Outcome(label, False, f"{action.text!r} cannot be read as text"), False
    updated = apply_edit(content, action.search, action.replace, fname=action.text)
    if updated is None:
        if content is None:
            return Outcome(label, False, f"{action.text!r} does not exist, so a SEARCH section cannot match; to create it leave SEARCH empty"), False
        close = find_similar_lines(action.search, content)
        text = "the SEARCH text was not found in the file; the file is shown in view, copy lines from it exactly"
        return Outcome(label, False, text + (f". Closest lines:\n{close}" if close else "")), False
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(updated, encoding="utf-8")
    except OSError as error:
        return Outcome(label, False, f"could not write: {error}"), False
    return Outcome(label, True, "applied" if content is not None else "created"), True


def run_loop(goal: str, *, working_dir: str, complete: Callable[[str, str], str], context: str = "", max_calls: int = 15, depth: int = 1,
             cancel: Optional[Callable[[], bool]] = None, emit: Optional[Callable[[str], None]] = None, command_timeout: float = 60.0,
             environment: Optional[Mapping[str, str]] = None, wrap: Sequence[str] = (), view_chars: int = 100000,
             counter: Optional[CallCounter] = None, review: bool = True, state: Optional[LoopState] = None,
             save: Optional[Callable[[LoopState], None]] = None, inbox: Optional[Callable[[], Sequence[str]]] = None,
             tools: Optional[Mapping[str, Tool]] = None) -> LoopResult:
    """Work ``goal`` in ``working_dir`` until a call's report is accepted, the model is blocked, ``max_calls`` model calls are spent (the
    ``counter`` is shared with helpers and counts all of them) or ``cancel()`` is true. Never raises. With ``review``, written text in which a code check
    (``unsupported``) finds a figure no source file holds, or a named file that is not in the folder, gets one more call before it is accepted: a
    reviewer that sees only the goal, the files as they are now and those findings (not the worker's reasoning) and corrects the files. Work with no
    such finding is accepted with no extra call: measured on the hard deliverables, reviewing every written text cost a call each and passed no more.

    ``state`` continues an earlier run (its history and view; the files are rendered fresh from disk; calls count from zero for this run) and
    ``save`` gets the new ``LoopState`` after every call's actions. ``inbox`` returns the messages a person sent; ``tools`` are the operations
    the model may ``USE``."""
    result = LoopResult()
    try:
        loop(result, goal, working_dir, complete, context, max_calls, depth, cancel, emit, command_timeout, environment, wrap, view_chars,
             counter if counter is not None else CallCounter(max_calls), review, state, save, inbox, tools)
    except Exception as error:  # noqa: BLE001 -- the loop reports a failure, it does not raise
        result.met = False
        result.error = result.error or f"the loop failed: {type(error).__name__}: {error}"
    return result


def loop(result: LoopResult, goal: str, working_dir: str, complete, context: str, max_calls: int, depth: int, cancel, emit, command_timeout: float,
         environment, wrap, view_chars: int, counter: CallCounter, review: bool = True, state: Optional[LoopState] = None,
         save: Optional[Callable[[LoopState], None]] = None, inbox: Optional[Callable[[], Sequence[str]]] = None,
         tools: Optional[Mapping[str, Tool]] = None) -> None:
    root = os.path.abspath(working_dir)
    say = emit or (lambda _text: None)
    files, _ = listing(root)
    view = View(root, view_chars)
    entries: List[Dict[str, Any]] = []
    changed: "OrderedDict[str, None]" = OrderedDict()
    seen: "OrderedDict[str, None]" = OrderedDict()
    earlier_goal = ""
    earlier_calls = 0
    if state is None:
        view.start(files, goal + "\n" + context)
    else:
        earlier_goal = state.goal
        earlier_calls = int(state.calls)
        entries.extend(dict(entry) for entry in state.entries)
        for rel, named in state.view:
            view.files[rel] = bool(named)
        for rel, _size in files:
            if rel not in view.files and (mentions(goal, rel) or mentions(goal, rel.rsplit("/", 1)[-1])):
                view.add(rel, named=True)
        changed.update((rel, None) for rel in state.changed)
        seen.update((rel, None) for rel in state.read)
    tool_lines = "".join(f"USE: {name} <input>   {' '.join(tool.description.split())}\n" for name, tool in (tools or {}).items())
    system = SYSTEM.format(delegate=DELEGATE_LINE if depth > 0 else "", tools=tool_lines)

    def fetch() -> List[str]:
        """The messages a person sent since the last look, added to the history; the texts."""
        if inbox is None:
            return []
        try:
            got = [str(m) for m in (inbox() or []) if str(m).strip()]
        except Exception:  # noqa: BLE001 -- a broken inbox never ends a run
            return []
        for message in got:
            entries.append({"message": message.strip()})
        return got

    saved_at: List[Any] = [None]

    def persist(force: bool = False) -> None:
        """Hand ``save`` the state, once per call (and again when messages were added since)."""
        marker = (own_calls, len(entries))
        if save is None or (saved_at[0] == marker and not force):
            return
        saved_at[0] = marker
        try:
            save(LoopState(goal=goal, entries=[dict(e) for e in entries], view=list(view.files.items()), changed=list(changed),
                           read=list(seen), calls=earlier_calls + own_calls))
        except Exception:  # noqa: BLE001 -- a store that cannot write never ends a run
            pass
    last_text = ""
    nudged = False
    advice = ""
    own_calls = 0
    check_passed = False
    while True:
        if own_calls:
            persist()
        if cancel is not None and cancel():
            result.error = "the run was cancelled"
            break
        if not counter.take():
            result.error = f"the call limit ({counter.limit}) was spent before the work was finished"
            break
        fetch()
        own_calls += 1
        result.calls += 1
        files_text, shown = view.render()
        folder_map = marked(listing(root)[1], shown)
        for rel in shown:
            seen.setdefault(rel)
        note = ""
        if counter.left() == 0:
            note = "This is your last call: finish with a REPORT now, saying what is done and what is not."
        elif counter.left() == 1:
            note = "One call remains after this one: aim to finish with a REPORT."
        try:
            text = complete(system, build_prompt(goal, context, folder_map, files_text, entries, note, earlier_goal)) or ""
        except Exception as error:  # noqa: BLE001
            result.error = f"the model call failed: {type(error).__name__}: {error}"
            break
        reply = parse_reply(text, tools=bool(tools))
        entry: Dict[str, Any] = {"call": earlier_calls + own_calls, "note": " | ".join(reply.notes), "outcomes": [], "advice": "", "reply": text}
        result.log.append({"call": own_calls, "reply": text, "outcomes": entry["outcomes"]})
        entries.append(entry)
        late = fetch()     # a message that came in while the model worked: unseen by this reply
        if reply.notes:
            last_text = reply.notes[-1]
        if reply.report is not None:
            last_text = reply.report or last_text
        if reply.blocked:
            result.error = f"blocked: {reply.blocked}"
            result.report = last_text
            break
        if not reply.actions and reply.report is None:
            if own_calls == 1 and text.strip() and not reply.notes and not late:
                result.met, result.report = True, text.strip()
                break
            if late:
                entry["advice"] = MESSAGE_ADVICE
                continue
            if nudged:
                result.error = "the model did not use the action protocol"
                result.report = last_text
                break
            nudged = True
            entry["advice"] = NO_ACTION_ADVICE
            continue
        failed: List[str] = []
        codes: List[int] = []
        checks: List[Action] = []
        new_reads = other_work = False
        for problem in reply.problems:
            entry["outcomes"].append(Outcome("EDIT", False, problem))
            failed.append(problem)
        for action in reply.actions:
            if action.kind == "check":
                checks.append(action)
                continue
            outcome = execute(action, root, view, changed, seen, result, depth, complete, context, max_calls, cancel, emit, command_timeout,
                              environment, wrap, view_chars, counter, codes, tools)
            entry["outcomes"].append(outcome)
            if action.kind == "read" and outcome.ok:
                new_reads = new_reads or outcome.text.startswith("added")
            elif action.kind == "use":
                new_reads = new_reads or outcome.ok
            elif action.kind != "read":
                other_work = True
            if not outcome.ok and (action.kind != "run" or outcome.text.startswith("refused")):
                failed.append(outcome.label)
            say(f"call {own_calls}: {outcome.label} {'ok' if outcome.ok else 'failed'}")
        passed = True
        for action in checks:
            before = snapshot(root)
            done = run_command(action.text, working_dir=root, timeout=command_timeout, environment=environment, wrap=wrap, limit=COMMAND_LIMIT)
            result.commands += 0 if done.refused else 1
            track(root, before, changed)
            ok = done.code == 0 and not done.refused
            passed = passed and ok
            check_passed = check_passed or ok
            entry["outcomes"].append(Outcome(f"CHECK {short(action.text)}", ok, f"exit {done.code}\n{done.output}".strip()))
            say(f"call {own_calls}: check {'passed' if ok else 'failed'}")
        if reply.report is None:
            continue
        if late:
            entry["advice"] = MESSAGE_ADVICE
        elif new_reads and not other_work and not checks:
            entry["advice"] = "You read files or used a tool in this reply, so your REPORT was written before seeing the result. It is in view now: report from it."
        elif failed:
            entry["advice"] = f"Your REPORT was not accepted because these actions failed: {'; '.join(failed)}. Fix them and report again."
        elif checks and not passed:
            entry["advice"] = "Your REPORT was not accepted because CHECK did not exit 0 (see above). Fix the cause, then report again with the CHECK."
        elif not checks and any(code != 0 for code in codes):
            entry["advice"] = "Your REPORT was not accepted because a RUN exited non-zero (see above). Fix the cause, then report again."
        else:
            result.met, result.report = True, reply.report
            found = unsupported(root, list(changed)) if review and changed else []
            if (found or (review == REVIEW_PROSE and any(prose(rel) for rel in changed))) and counter.take():
                result.calls += 1
                outcomes = reviewed(goal, context, root, view, changed, complete, found)
                result.log.append({"review": True, "outcomes": outcomes})
                say(f"review: {'no change' if not outcomes else str(len(outcomes)) + ' correction(s)'}")
            break
        last_text = reply.report or last_text
        result.report = last_text
    result.report = result.report or last_text
    result.changed = list(changed)
    result.read = list(seen)
    persist()


def prose(rel: str) -> bool:
    """Whether a file is written text: what it claims cannot be verified by a command, so a CHECK that passed does not stand in for a review."""
    return os.path.splitext(rel)[1].lower() in PROSE_SUFFIXES


def marked(folder_map: str, shown: Sequence[str]) -> str:
    """The folder map with every file whose text is not in view marked, so the model knows what it has not read."""
    inview = set(shown)
    lines = []
    for line in folder_map.splitlines():
        rel = line.rsplit(" (", 1)[0]
        lines.append(line if rel in inview or not line.endswith("bytes)") else line + "  [not in view: READ it before relying on it]")
    return "\n".join(lines)


NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?![\w])")
CITED_FILE = re.compile(r"(?<![\w/.-])[\w./-]*\w\.(?:md|txt|csv|json|yaml|yml|rst|py)(?![\w])")


def figures(text: str) -> List[str]:
    """The numbers of two digits or more in ``text``, without thousands separators or a trailing ``.0``."""
    out = []
    for raw in NUMBER.findall(text):
        value = raw.replace(",", "").rstrip(".")
        if sum(ch.isdigit() for ch in value) >= 2:
            out.append(value)
    return out


def derived(known: Sequence[str], limit: int = 150) -> set:
    """The sums, differences and products of each pair of source figures (the first ``limit`` of them): a figure worked out from two figures the
    sources hold is supported by them, so the code check does not list it."""
    values = []
    for text in sorted(known)[:limit]:
        try:
            values.append(float(text))
        except ValueError:
            continue
    out = set()
    for a in values:
        for b in values:
            for result in (a + b, a - b, a * b):
                if result > 0:
                    out.add(str(int(result)) if float(result).is_integer() else f"{result:.2f}".rstrip("0").rstrip("."))
    return out


def unsupported(root: str, changed: Sequence[str], limit: int = 20) -> List[str]:
    """What code alone can tell about written text, with no model: each figure in a changed prose file that appears in no other file of the folder,
    and each file it names that is not in the folder. A figure worked out from the sources is listed too; the reviewer decides."""
    written = {rel: read_text(Path(root) / rel) or "" for rel in changed if prose(rel)}
    if not written:
        return []
    paths = [rel for rel, _, _ in walk(root)]
    sources = " ".join(read_text(Path(root) / rel) or "" for rel in paths if rel not in changed)
    known = set(figures(sources))
    known |= derived(known)
    names = set(paths) | {rel.rsplit("/", 1)[-1] for rel in paths}
    found: List[str] = []
    for rel, text in written.items():
        for value in dict.fromkeys(figures(text)):
            if value not in known:
                found.append(f"{rel}: the figure {value} is in no source file")
        for name in dict.fromkeys(CITED_FILE.findall(text)):
            if name not in names and name.lstrip("./") not in names:
                found.append(f"{rel}: names the file {name}, which is not in the folder")
    return found[:limit]


def reviewed(goal: str, context: str, root: str, view: View, changed: "OrderedDict[str, None]", complete, found: Sequence[str] = ()) -> List[Outcome]:
    """One review of finished work by a call that sees the goal and the files as they are, never the worker's replies. Its edit blocks are applied to
    the files the work changed (a reviewer corrects the work, it does not widen it); any other reply changes nothing. A failure changes nothing."""
    for rel in changed:
        if read_text(Path(root) / rel) is not None:
            view.add(rel, named=True)
    files_text, shown = view.render()
    prompt = "\n\n".join(filter(None, [f"GOAL:\n{goal.strip()}", f"CONTEXT:\n{context.strip()}" if context.strip() else "",
                                       f"FILES WRITTEN OR CHANGED BY THE WORK: {', '.join(changed)}", f"FILES (current):\n{files_text}",
                                       ("FOUND BY A CODE CHECK (certain, not a judgment; list each under UNSUPPORTED and deal with it: keep a figure only "
                                        "where the written file shows the arithmetic from figures that are in the sources):\n" + "\n".join(found)) if found else ""]))
    try:
        reply = parse_reply(complete(REVIEW_SYSTEM, prompt) or "")
    except Exception:  # noqa: BLE001 -- a review that cannot run leaves the accepted work as it is
        return []
    outcomes = []
    for action in reply.actions:
        if action.kind == "edit" and action.text.strip().lstrip("./") in changed:
            outcomes.append(apply_block(action, root)[0])
    return outcomes


def execute(action: Action, root: str, view: View, changed: "OrderedDict[str, None]", seen, result: LoopResult, depth: int, complete, context: str,
            max_calls: int, cancel, emit, command_timeout: float, environment, wrap, view_chars: int, counter: CallCounter,
            codes: List[int], tools: Optional[Mapping[str, Tool]] = None) -> Outcome:
    if action.kind == "edit":
        outcome, wrote = apply_block(action, root)
        rel = os.path.relpath(inside(Path(root), action.text), Path(root).resolve()).replace(os.sep, "/") if outcome.ok or wrote else action.text
        if wrote:
            changed.setdefault(rel)
            view.add(rel)
        elif not outcome.ok:
            try:      # a failed SEARCH: show the file as it is now
                target = inside(Path(root), action.text)
                if read_text(target) is not None:
                    view.add(os.path.relpath(target, Path(root).resolve()).replace(os.sep, "/"))
            except (ValueError, OSError):
                pass
        return outcome
    if action.kind == "read":
        label = f"READ {action.text}"
        try:
            path = inside(Path(root), action.text)
        except (ValueError, OSError):
            return Outcome(label, False, "outside the working folder")
        rel = os.path.relpath(path, Path(root).resolve()).replace(os.sep, "/")
        if not path.exists():
            return Outcome(label, False, "no such file")
        if read_text(path) is None:
            return Outcome(label, False, "not a readable text file")
        known = rel in view.files
        view.add(rel)
        return Outcome(label, True, "already in view" if known else "added to view; its text is in view from the next reply")
    if action.kind == "run":
        before = snapshot(root)
        done = run_command(action.text, working_dir=root, timeout=command_timeout, environment=environment, wrap=wrap, limit=COMMAND_LIMIT)
        track(root, before, changed)
        label = f"RUN {short(action.text)}"
        if done.refused:
            return Outcome(label, False, f"refused: {done.refused}")
        result.commands += 1
        codes.append(done.code)
        return Outcome(label, done.code == 0, ("timed out; " if done.timed_out else "") + f"exit {done.code}\n{done.output}".rstrip())
    if action.kind == "use":
        name, _, given = action.text.partition(" ")
        label = f"USE {name} {short(given)}".strip()
        tool = (tools or {}).get(name)
        if tool is None:
            return Outcome(label, False, f"there is no tool named {name!r}; the tools are: {', '.join(tools or {}) or 'none'}")
        try:
            return Outcome(label, True, clip(str(tool.run(given.strip())), COMMAND_LIMIT))
        except Exception as error:  # noqa: BLE001 -- a failing tool is a failed action, not a failed run
            return Outcome(label, False, f"{type(error).__name__}: {error}")
    if action.kind == "delegate":
        label = f"DELEGATE {short(action.text)}"
        if depth <= 0:
            return Outcome(label, False, "delegation is not available here")
        child = run_loop(action.text, working_dir=root, complete=complete, context=context, max_calls=max_calls, depth=depth - 1, cancel=cancel,
                         emit=emit, command_timeout=command_timeout, environment=environment, wrap=wrap, view_chars=view_chars, counter=counter,
                         review=False, tools=tools)      # the parent's review covers what its helpers wrote
        result.calls += child.calls
        result.commands += child.commands
        result.log.append({"delegated": action.text, "calls": child.calls, "met": child.met})
        for rel in child.changed:
            changed.setdefault(rel)
        for rel in child.read:
            seen.setdefault(rel)
        text = f"met={child.met}; report: {clip(child.report or child.error, REPORT_DELEGATE_CHARS)}"
        if child.changed:
            text += f"\nfiles changed: {', '.join(child.changed)}"
        return Outcome(label, child.met, text)
    return Outcome(action.kind.upper(), False, "unknown action")


def track(root: str, before: Mapping[str, Tuple[int, float]], changed: "OrderedDict[str, None]") -> None:
    """Add to ``changed`` every file a command created or modified (compared with the snapshot taken before it)."""
    for rel, state in snapshot(root).items():
        if before.get(rel) != state:
            changed.setdefault(rel)
