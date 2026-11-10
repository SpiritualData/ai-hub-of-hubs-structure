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
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Collection, Dict, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_world.tools.command_running import clip, run_command
from hubofhubs.the_world.tools.file_editing.editblock import (DIVIDER, HEAD, UPDATED, apply_edit, find_original_update_blocks,
                                                              find_similar_lines)
from hubofhubs.the_world.tools.file_reading.read_files import inside

FOLDER_VIEW = "folder-view"       # the solution that chooses the files in view and judges which folders to leave out (Subconscious)
LEFT_OUT_LINES = 25               # folders left out that the folder map names, with the reason
MAP_ENTRIES = 300
LEXICAL_FILES = 200                # above this many files the folder map is an outline, not a list
TOOL_LIMIT = 20_000                # characters kept from one tool result (a runbook or a page is read whole where a command's output is clipped)
SYSTEM_CHARS = 300_000              # the stable content of a run (instructions, goal, context, map, start files) the system text may hold; a setting of the runner
NOTHING_NEW = "(nothing has changed or been added since the start: the files shown at the start are current)"
# The files in view at the start go in the system text, after the instructions: a model service keeps a long system text between calls, so the
# second call of a run (and a review, and a helper) pays a fraction for them. The message then carries only what changed or was added.
VIEW_FILES = "FILES IN VIEW (current):"
CHANGED_FILES = "FILES IN VIEW CHANGED OR ADDED SINCE THE START (current):"
START_FILES = "FILES IN VIEW AT THE START (each is current unless the message shows it again, which then replaces this copy):"
REVIEW_PROSE = "prose"            # ``review`` value: review every written text, not only one in which the code check found something
PROSE_SUFFIXES = ("", ".md", ".txt", ".rst", ".adoc", ".html", ".htm")
MAP_FILE_LIMIT = 200_000          # a larger file is not listed or put in view at launch (READ can still show its start)
log = logging.getLogger("hubofhubs.deep")
SNAPSHOT_FILES = 5000
OLD_RESULT_CHARS = 300
HISTORY_CHARS = 20_000             # the history section of a message passes this and the older calls shrink further
GOAL_TITLE_CHARS = 200
COMMAND_LIMIT = 4000
CANCEL_POLL_SECONDS = 0.05      # how often a stop is looked for while a model call is in flight
REPORT_DELEGATE_CHARS = 600
MESSAGE_LINE = "MESSAGE FROM THE PERSON (follow it; it overrides the plan so far): "
MESSAGE_ADVICE = "A message from the person arrived while you worked, so your REPORT was not accepted. Answer the message, then report again."
NO_ACTION_ADVICE = ("Your last reply used none of the actions. Reply with READ:, RUN:, CHECK:, edit blocks or DELEGATE: lines to do the work, "
                    "or REPORT: when it is finished, or BLOCKED: when it cannot be done.")

SYSTEM = """You work in one folder. The files in view are current and complete; the folder map lists the rest, and marks each file you have not seen. Never report on, summarise or cite a file that is not in view: READ it first. Act by writing these lines, each on its own line, anywhere in your reply:
READ: <path>     show a file from the folder (several lines allowed)
RUN: <command>   run a shell command in the folder (several allowed; function-call markup such as <invoke> is not needed and these plain lines are the form to use). A command of several lines is a fenced block (```bash then the lines then ```), or a RUN line that ends in a heredoc opener with its body after it: RUN: python3 - <<'EOF' then the code, then EOF alone on a line
CHECK: <command> your acceptance check for the whole task, run after all other actions
STATE: <your working memory>   REWRITE this in every reply that acts; the loop shows it at the top of every message and keeps only the latest (about 4,000 characters), older results are clipped. Write what is DONE, what you LEARNED that matters later (the facts themselves, paths, ids, values), what is NEXT, and what FAILED and must not be retried. Put it last in the reply, or end it with END STATE. Example:
STATE: done: scanned the board, found 12 rows in /tmp/scan.json. learned: the sheet id is S-42, the assignee id is U-7. next: write rows to out.csv. failed: curl to the old URL (404), do not retry.
END STATE
NOTE: <one line> adds a line to your STATE
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
REVIEW_ROLE = ("FOR THIS MESSAGE YOUR ROLE IS DIFFERENT FROM THE ONE DESCRIBED AT THE TOP: the work is finished and you are its reviewer. Of the "
               "actions listed at the top only edit blocks apply. ")
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
STATE_START = re.compile(r"^[\s>*`#-]*STATE\s*:\**\s*(.*)$")
STATE_END = re.compile(r"^[\s>*`#-]*END STATE\b")
STATE_CHARS = 4000               # the working memory the loop keeps and shows at the top of every message
REPEAT_REFUSED_AFTER = 2         # an exact command or tool call that failed this many times with the same error is not run again


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


class Abandoned(Exception):
    """The run was stopped while a model call was in flight and the call was given up (its result, if it ever comes, is discarded)."""


class Telling:
    """The structured account of a run for a surface, as plain dicts shaped like the session events of the Consciousness container (``type``, ``at``,
    ``agent_id`` and the event's own fields), so nothing here imports a screen. One ``Telling`` is shared by a loop and its helpers: each helper gets an
    agent id of its own and announces itself under its parent. ``sink`` gets each dict; a sink that raises never ends a run."""

    def __init__(self, sink: Optional[Callable[[Dict[str, Any]], None]], agent: str = "main", solution: str = "",
                 shared: Optional[Dict[str, Any]] = None, clock: Callable[[], float] = time.monotonic):
        self.sink, self.agent, self.solution, self.clock = sink, agent, solution, clock
        self.shared = shared if shared is not None else {"start": clock(), "helper": 0, "step": 0, "message": 0, "lock": threading.Lock()}

    def send(self, event_type: str, /, **data: Any) -> None:
        if self.sink is None:
            return
        data.setdefault("agent_id", self.agent)
        data.update(type=event_type, at=max(round(self.clock() - self.shared["start"], 3), 0.001))
        try:
            self.sink(data)
        except Exception:  # noqa: BLE001 -- a surface that fails never ends a run
            pass

    def count(self, name: str) -> int:
        with self.shared["lock"]:
            self.shared[name] += 1
            return self.shared[name]

    def helper(self, task: str, solution: str = "") -> "Telling":
        """Announce a helper under this agent and return the ``Telling`` it reports through."""
        agent = f"helper-{self.count('helper')}"
        self.send("agent-started", agent_id=agent, parent_id=self.agent, task=short(task), solution=solution)
        return Telling(self.sink, agent, solution, self.shared, self.clock)

    def step(self, kind: str, label: str, state: str = "running", step_id: str = "", detail: str = "") -> str:
        lines = [line for line in label.strip().splitlines() if line.strip()]
        if len(lines) > 1:      # a command of several lines is named by its first line and how many more there are
            label = f"{lines[0].strip()} (+{len(lines) - 1} more lines)"
        step_id = step_id or f"{self.agent}-step-{self.count('step')}"
        self.send("step", step_id=step_id, kind=kind, label=short(label), state=state, detail=short(detail, 100))
        return step_id


def normalised(text: str) -> str:
    return " ".join(str(text).split())


def first_error(text: str) -> str:
    """The first line of a failed result that says why: the output's first non-empty line after the ``exit N`` header, else the header."""
    lines = [line.strip() for line in str(text).splitlines() if line.strip()]
    body = [line for line in lines if not re.fullmatch(r"(timed out; )?exit -?\d+", line)]
    return (body or lines or [""])[0][:200]


class Repeats:
    """What the loop has seen an exact command, tool call or check do: how often it failed with the same first error line, and how often it ran. An exact
    repeat of a failure is told so the second time and not run the third time; a check that cannot pass by repeating it is told so; a command that keeps
    succeeding unchanged is told that too."""

    def __init__(self) -> None:
        self.failed: Dict[str, Tuple[str, int]] = {}
        self.ran: Dict[str, int] = {}

    def refusal(self, key: str) -> str:
        found = self.failed.get(key)
        if found and found[1] >= REPEAT_REFUSED_AFTER:
            return (f"not run: this exact command has already failed {found[1]} times with the same error ({found[0]}). Do not retry it unchanged: change what it does, "
                    "try another way, or report what a person has to fix.")
        return ""

    def failure(self, key: str, text: str) -> Tuple[int, str]:
        """Record a failure; the number of times it has now failed with this error and the line to add to its result (empty the first time)."""
        error = first_error(text)
        before = self.failed.get(key)
        count = before[1] + 1 if before and before[0] == error else 1
        self.failed[key] = (error, count)
        if count < 2:
            return count, ""
        return count, f"\nThis has now failed {count} times with the same error ({error}) and must not be retried unchanged."

    def success(self, key: str) -> str:
        self.failed.pop(key, None)
        self.ran[key] = self.ran.get(key, 0) + 1
        if self.ran[key] >= 3:
            return f"\nThis exact command has now run {self.ran[key]} times; if it is not changing anything, do something different."
        return ""


def bounded_state(text: str) -> str:
    """The working memory within ``STATE_CHARS``: whole lines from the end when it is longer (the newest lines stay)."""
    text = text.strip()
    if len(text) <= STATE_CHARS:
        return text
    kept: List[str] = []
    total = 0
    for line in reversed(text.splitlines()):
        if total + len(line) + 1 > STATE_CHARS:
            break
        kept.append(line)
        total += len(line) + 1
    return "\n".join(reversed(kept)) or text[-STATE_CHARS:]


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
    ended: str = ""               # why the loop ended: met, blocked, no_action, call_limit, cancelled, partial, model_failed, failed
    partial: bool = False          # ended not met on purpose: a check cannot pass, and the report says what a person has to do
    state: str = ""                # the working memory at the end


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
    state: Optional[str] = None
    unmapped: str = ""      # markup the reply held that named no action the loop knows (its first characters)


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
    state: str = ""
    ended: str = ""

    def to_json(self) -> str:
        entries: List[Dict[str, Any]] = []
        for entry in self.entries:
            if "message" in entry:
                entries.append({"message": str(entry["message"])})
                continue
            entries.append({"call": int(entry.get("call", 0)), "note": str(entry.get("note") or ""), "advice": str(entry.get("advice") or ""),
                            "outcomes": [{"label": o.label, "ok": bool(o.ok), "text": o.text} for o in entry.get("outcomes", [])]})
        return json.dumps({"goal": self.goal, "entries": entries, "view": [[path, bool(named)] for path, named in self.view],
                           "changed": list(self.changed), "read": list(self.read), "calls": int(self.calls), "state": self.state, "ended": self.ended}, ensure_ascii=False)

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
                       changed=[str(p) for p in data.get("changed", [])], read=[str(p) for p in data.get("read", [])], calls=int(data.get("calls", 0)), state=str(data.get("state") or ""), ended=str(data.get("ended") or ""))
        except (TypeError, KeyError, AttributeError, ValueError) as error:
            raise ValueError(f"not a saved loop state: {error}") from error


def selected_folder_view() -> Callable[..., Any]:
    """The ``choose`` of the hub's selected Folder View implementation, resolved by name from the records (the way ``arm_choice`` resolves a harness)."""
    from esoi import selection
    return selection.resolve(FOLDER_VIEW, scope="hubofhubs")().choose


# --- the working folder ----------------------------------------------------------------------------------------------------------------

def walk(root: str, limit: int = SNAPSHOT_FILES, skip: Collection[str] = ()) -> List[Tuple[str, int, float]]:
    """``(relative path, size, mtime)`` of the files under ``root``, level by level from the top (so a cap keeps the shallow files of a very large
    folder and stops scanning). A folder whose relative path is in ``skip`` (the folders the selection left out) is not entered. At most ``limit`` files."""
    found: List[Tuple[str, int, float]] = []
    level = [(root, "")]
    while level and len(found) < limit:
        deeper: List[Tuple[str, str]] = []
        for folder, rel_folder in level:
            try:
                entries = sorted(os.scandir(folder), key=lambda e: e.name)
            except OSError:
                continue
            for entry in entries:
                try:
                    if entry.is_symlink():
                        continue
                    rel = (rel_folder + "/" if rel_folder else "") + entry.name
                    if entry.is_dir():
                        if rel not in skip:
                            deeper.append((entry.path, rel))
                    elif entry.is_file() and len(found) < limit:
                        stat = entry.stat()
                        found.append((rel, stat.st_size, stat.st_mtime_ns))
                except OSError:
                    continue
            if len(found) >= limit:
                break
        level = deeper
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


def head_text(path: Path, chars: int = 2048) -> Optional[str]:
    """The first ``chars`` bytes of ``path`` as text, or None when it cannot be read or looks binary. Reading only the head keeps a folder of
    thousands of files quick to map."""
    try:
        with path.open("rb") as handle:
            data = handle.read(chars)
    except OSError:
        return None
    return None if b"\0" in data else data.decode("utf-8", errors="ignore")


def listing(root: str, skip: Collection[str] = (), left_out: Sequence[Any] = ()) -> Tuple[List[Tuple[str, int]], str]:
    """The text files that fit ``MAP_FILE_LIMIT`` as ``(path, size)`` and the map text: one line per file (at most ``MAP_ENTRIES``) with a line
    saying how many were left out, then the folders the selection left out, each with its reason in a few words."""
    base = Path(root)
    texts = [(rel, size) for rel, size, _ in walk(root, skip=skip) if size <= MAP_FILE_LIMIT and head_text(base / rel) is not None]
    if len(texts) > LEXICAL_FILES:
        return texts, outline(texts) + left_out_text(left_out)
    shown = texts[:MAP_ENTRIES]
    lines = [f"{rel} ({size} bytes)" for rel, size in shown] or ["(no files yet)"]
    if len(texts) > len(shown):
        lines.append(f"... {len(texts) - len(shown)} more files not listed; the folder is large, so find what you need with RUN: ls <folder> or RUN: grep -rl <words> <folder>, then READ it")
    return texts, "\n".join(lines) + left_out_text(left_out)


def left_out_text(left_out: Sequence[Any]) -> str:
    """The folders (and risky files) not scanned, one line each, so the model knows they exist and can ask: risky ones first, then the rest."""
    if not left_out:
        return ""
    ordered = sorted(left_out, key=lambda x: (not x.risky, x.path))
    lines = [f"{x.path} ({x.reason})" for x in ordered[:LEFT_OUT_LINES]]
    if len(ordered) > LEFT_OUT_LINES:
        lines.append(f"... {len(ordered) - LEFT_OUT_LINES} more left out")
    return "\nLEFT OUT, not scanned or shown (they exist; look with RUN: ls only if the work needs them, and never open a secret or key unasked):\n" + "\n".join(lines)


def outline(texts: Sequence[Tuple[str, int]], depth: int = 2, limit: int = 120) -> str:
    """A large folder as an outline: the files at the top, then each folder down to ``depth`` levels with how many files were found below it. A
    flat list of hundreds of paths costs every call and still shows a sliver; the outline says where to look."""
    top = [f"{rel} ({size} bytes)" for rel, size in texts if "/" not in rel][:40]
    counts: Dict[str, int] = {}
    for rel, _ in texts:
        parts = rel.split("/")[:-1]
        for level in range(1, min(len(parts), depth) + 1):
            key = "/".join(parts[:level]) + "/"
            counts[key] = counts.get(key, 0) + 1
    folders = [f"{key} ({count} files found below)" for key, count in sorted(counts.items())][:limit]
    return "\n".join(top + folders + ["This folder is large: only its outline is shown. Find what you need with RUN: ls <folder> or "
                                      "RUN: grep -rl <words> <folder>, then READ it."])


def mentions(text: str, name: str) -> bool:
    return re.search(r"(?<![\w.-])" + re.escape(name) + r"(?!\w)", text) is not None


class View:
    """The files in view, least recently used first. A named file (one the goal or context mentions) is never evicted."""

    def __init__(self, root: str, view_chars: int, skip: Collection[str] = (), select: Optional[Callable[..., Any]] = None):
        self.root, self.view_chars = root, view_chars
        self.skip, self.select = skip, select       # the folders left out (not walked) and the selection that left them out (handed to a helper)
        self.files: "OrderedDict[str, bool]" = OrderedDict()

    def start(self, picks: Sequence[Any], goal: str = "") -> None:
        """Put the chosen files in view within ``view_chars`` in all, whoever named them: first the files the goal names, then the Folder View's other picks,
        then the files only the context names. What does not fit stays out of view (the folder map lists it as a file to READ). A named pick is never
        evicted later; the first of the others end up the most recently used, so the last go first when space is needed. A flagged pick (named inside a
        risky folder) is not shown: the caller decides, and the folder map lists it."""
        shown = [p for p in picks if not p.flagged]

        def rank(pick: Any) -> int:
            if pick.named and (mentions(goal, pick.path) or mentions(goal, pick.path.rsplit("/", 1)[-1])):
                return 0
            return 1 if not pick.named else 2
        kept: List[Any] = []
        used = 0
        for pick in sorted(shown, key=rank):
            size = self.size(pick.path)
            if used + size <= self.view_chars:
                kept.append(pick)
                used += size
        for pick in kept:
            if pick.named:
                self.files[pick.path] = True
        for pick in reversed([p for p in kept if not p.named]):
            self.files[pick.path] = False

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

    def blocks(self) -> "OrderedDict[str, str]":
        """``{path: its block of text}`` for the files in view, as they are on disk now."""
        out: "OrderedDict[str, str]" = OrderedDict()
        for rel in list(self.files):
            text = read_text(Path(self.root) / rel)
            if text is None:
                continue
            if not text.strip():
                text = "(empty file)\n"
            elif len(text) > self.view_chars:
                text = text[:self.view_chars] + f"\n[the file goes on: {len(text) - self.view_chars} more characters; use RUN: sed -n to see them]\n"
            out[rel] = f"=== {rel} ===\n{text if text.endswith(chr(10)) else text + chr(10)}"
        return out

    def render(self, start: Optional[Mapping[str, str]] = None) -> Tuple[str, List[str]]:
        """The text of the files in view as they are on disk now, and their paths. With ``start`` (the blocks shown at the start of the run, which
        the model already holds), only the files that changed or were added since are in the text; the paths are still all of them."""
        blocks = self.blocks()
        parts = [block for rel, block in blocks.items() if start is None or start.get(rel) != block]
        return "\n".join(parts) if parts else ("(none)" if start is None else NOTHING_NEW), list(blocks)


# --- the reply -------------------------------------------------------------------------------------------------------------------------

INVOKE = re.compile(r"<invoke\s+name\s*=\s*[\"']([A-Za-z_]+)[\"']\s*>(.*?)</invoke>", re.DOTALL | re.IGNORECASE)
PARAM = re.compile(r"<parameter\s+name\s*=\s*[\"']([A-Za-z_]+)[\"']\s*>(.*?)</parameter>", re.DOTALL | re.IGNORECASE)
MARKUP_TAG = re.compile(r"</?\s*(?:invoke|parameter|function_calls|antml:[a-z_]+)\b", re.IGNORECASE)
MARKUP_LINE = re.compile(r"^\s*</?\s*(?:function_calls|invoke)\b[^>]*>\s*$", re.IGNORECASE)
JSON_FENCE = re.compile(r"^\s*```\s*json\s*$", re.IGNORECASE)
ACTION_NAMES = {"run": "run", "bash": "run", "shell": "run", "read": "read", "check": "check", "delegate": "delegate", "use": "use"}
ACTION_FIELDS = {"run": ("command", "cmd", "script"), "read": ("path", "file", "file_path"), "check": ("command", "cmd"), "delegate": ("task", "subtask", "prompt"),
                 "use": ("input", "arguments", "args")}
UNMAPPED_CHARS = 120


def markup_action(name: str, params: Mapping[str, Any], tools: bool) -> Optional[Action]:
    """The action a function-call-style block means (``RUN``, ``READ``, ``CHECK``, ``DELEGATE``, ``USE``) or None when it names none."""
    kind = ACTION_NAMES.get(str(name).strip().lower())
    if kind is None or (kind == "use" and not tools):
        return None
    lowered = {str(k).lower(): v for k, v in params.items()}
    value = next((str(lowered[f]).strip("\n") for f in ACTION_FIELDS[kind] if str(lowered.get(f) or "").strip()), "")
    if kind == "use":
        tool = str(lowered.get("name") or lowered.get("tool") or "").strip()
        value = f"{tool} {value}".strip() if tool else value
    return Action(kind, value) if value.strip() else None


WRAPPER_TAGS = re.compile(r"</?\s*(?:invoke|parameter|function_calls|antml:[a-z_]+)\b[^>]*>", re.IGNORECASE)


def unwrap_protocol(body: List[str], start: int, end: int, text: str) -> str:
    """Markup that only wraps protocol lines (an ``<invoke name="RUN">`` with no parameter whose body itself starts with ``RUN:``, a heredoc and a stray
    ``</parameter>``) is that one command: the wrapper tags are dropped from the lines (in ``body``) and the plain protocol parses them. Returns the chunk's
    text again."""
    changed = False
    for found in INVOKE.finditer(text):
        inner = found.group(2)
        if PARAM.search(inner):
            continue
        first = next((line for line in WRAPPER_TAGS.sub("", inner).splitlines() if line.strip()), "")
        if not PROTOCOL_LINE.match(first):
            continue
        first_line = start + text[:found.start()].count("\n")
        last_line = start + text[:found.end()].count("\n")
        for k in range(first_line, last_line + 1):
            body[k] = WRAPPER_TAGS.sub("", body[k])
        changed = True
    return "\n".join(body[start:end]) if changed else text


def lenient_actions(body: List[str], mask: List[bool], tools: bool) -> Tuple[List[Action], str]:
    """The actions written as function-call markup (``<invoke name="RUN"><parameter name="command">..</parameter></invoke>``, with or without
    ``<function_calls>``, and a stray ``<parameter name="command">`` as a RUN) or as a JSON object (``{"action": "RUN", "command": "..."}`` on a line or in a
    fenced json block), in the lines no edit block holds. Their lines are masked so the plain protocol never reads them twice. The second value is the first
    120 characters of markup or JSON that named no action the loop knows, or ``""``."""
    actions: List[Action] = []
    unmapped = ""
    index = 0
    while index < len(body):
        if mask[index]:
            index += 1
            continue
        start = index
        while index < len(body) and not mask[index]:
            index += 1
        text = "\n".join(body[start:index])
        text = unwrap_protocol(body, start, index, text)
        spans: List[Tuple[int, int]] = []

        def line_of(offset: int) -> int:
            return start + text[:offset].count("\n")
        for found in INVOKE.finditer(text):
            spans.append(found.span())
            made = markup_action(found.group(1), {k: v for k, v in PARAM.findall(found.group(2))}, tools)
            if made is None:
                unmapped = unmapped or found.group(0).strip()[:UNMAPPED_CHARS]
                continue
            made.order = line_of(found.start())
            actions.append(made)
        for found in PARAM.finditer(text):      # a stray parameter with no opening invoke: its name says what it is
            if any(a <= found.start() < b for a, b in spans):
                continue
            spans.append(found.span())
            made = next((m for kind in ("run", "read", "delegate") for m in [markup_action(kind, {found.group(1): found.group(2)}, tools)] if m is not None), None)
            if made is None:
                unmapped = unmapped or found.group(0).strip()[:UNMAPPED_CHARS]
                continue
            made.order = line_of(found.start())
            actions.append(made)
        for a, b in spans:
            for k in range(line_of(a), line_of(b) + 1):
                mask[k] = True
        for offset in range(start, index):      # leftover wrapper tags on lines of their own
            if not mask[offset] and MARKUP_LINE.match(body[offset]):
                mask[offset] = True
        cursor = start
        while cursor < index:
            line = body[cursor]
            if mask[cursor]:
                cursor += 1
                continue
            block, end = None, cursor
            if JSON_FENCE.match(line):
                end = cursor + 1
                while end < index and not body[end].strip().startswith("```"):
                    end += 1
                block = "\n".join(body[cursor + 1:end])
            elif line.strip().startswith("{") and line.strip().endswith("}") and '"action"' in line:
                block = line.strip()
            if block is not None:
                try:
                    data = json.loads(block)
                except ValueError:
                    data = None
                items = data if isinstance(data, list) else [data]
                found_any = [i for i in items if isinstance(i, dict) and "action" in i]
                if found_any:
                    for item in found_any:
                        made = markup_action(str(item.get("action")), item, tools)
                        if made is None:
                            unmapped = unmapped or json.dumps(item)[:UNMAPPED_CHARS]
                        else:
                            made.order = cursor
                            actions.append(made)
                    for k in range(cursor, min(end, index - 1) + 1):
                        mask[k] = True
                    cursor = end
            cursor += 1
        for offset in range(start, index):      # markup still in the lines after all that: not an action the loop knows
            if not mask[offset] and MARKUP_TAG.search(body[offset]):
                unmapped = unmapped or body[offset].strip()[:UNMAPPED_CHARS]
    return actions, unmapped


READ_ONLY_COMMANDS = frozenset("ls cat head tail grep rg find wc sed stat file tree diff jq sort uniq cut du df pwd echo which type date env printenv".split())


def read_only(action: Action) -> bool:
    """Whether an action only looks: a READ, or a single command that starts with a looking command and writes nothing (no redirect, no ``sed -i``, no tee)."""
    if action.kind == "read":
        return True
    if action.kind != "run":
        return False
    text = action.text.strip()
    if ">" in text or "\n" in text or " tee " in text or re.search(r"\bsed\b.*\s-i", text):
        return False
    words = text.split()
    return bool(words) and os.path.basename(words[0]) in READ_ONLY_COMMANDS


FENCED_SHELL = re.compile(r"^\s*```\s*(bash|sh|shell|zsh)\s*$", re.IGNORECASE | re.MULTILINE)
PROTOCOL_LINE = re.compile(r"^[\s>*`#-]*(READ|RUN|CHECK|DELEGATE|USE)\s*:", re.MULTILINE)
REPORTING_STEP = re.compile(r"\b(report|reporting|deliver|delivering|check|verify|confirm|finish|finalize|final)\b")
STATE_NEXT = re.compile(r"\bnext\s*:\s*(.*?)(?=\b(?:failed|done|learned)\s*:|\Z)", re.IGNORECASE | re.DOTALL)
NOTHING_NEXT = frozenset(["", "none", "nothing", "n/a", "na", "nil", "-", "done", "complete", "completed", "finished", "nothing left", "nothing more", "nothing else",
                          "no next steps", "no further steps", "report", "reporting", "report now", "the report", "write the report", "final report", "give the report"])


def reads_as_work(text: str, reply: Reply) -> bool:
    """Whether a reply holds work and not an answer: a STATE block, action markup, a fenced shell command, a protocol line or an edit block. Such a reply is
    never taken as a final report, whatever its length (a reply of this kind ended a run as met while its own STATE said nothing was written)."""
    return bool(reply.state is not None or reply.problems or reply.unmapped or MARKUP_TAG.search(text) or FENCED_SHELL.search(text) or PROTOCOL_LINE.search(text)
                or re.search(HEAD, text, re.MULTILINE))


def next_steps(state: str) -> str:
    """What a STATE says is next (``next: ...``), or ``""`` when it names nothing that remains: absent, empty or a word such as none, done or report."""
    found = STATE_NEXT.search(state or "")
    if not found:
        return ""
    value = " ".join(found.group(1).split()).strip(" .;:-").lower()
    if value in NOTHING_NEXT or value.startswith(("none", "nothing", "no further", "no more", "no next")):
        return ""
    kept = [c.strip() for c in re.split(r",|;|\.|\bthen\b|\band\b", value) if c.strip() and not REPORTING_STEP.search(c)]
    return " ".join(found.group(1).split())[:300] if kept else ""      # a next made only of checking and reporting is the end of the work, not more work


def says_actions(text: str) -> bool:
    """Whether a text holds action markup, a protocol line, a STATE line or an edit block: raw reply text that is not an account of anything."""
    return bool(MARKUP_TAG.search(text) or PROTOCOL_LINE.search(text) or STATE_START.match(text.strip()) or re.search(r"^[\s>*`#-]*STATE\s*:", text, re.MULTILINE)
                or re.search(HEAD, text, re.MULTILINE))


def parse_reply(text: str, tools: bool = False) -> Reply:
    """The actions in a reply, in order of appearance. The report (from ``REPORT:`` to the end or to ``END REPORT``) is cut out first so that
    nothing written inside it runs. ``USE:`` lines are actions only when ``tools`` is true."""
    marker = TOOL_MARKER if tools else MARKER
    lines = text.splitlines()
    reply = Reply()
    body: List[str] = []
    index = 0
    def ends_chunk(line: str) -> bool:
        return bool(REPORT_START.match(line) or STATE_START.match(line))
    while index < len(lines):
        found = REPORT_START.match(lines[index])
        if found and reply.report is None:
            chunk = [found.group(1)]
            index += 1
            while index < len(lines) and not REPORT_END.match(lines[index]) and not STATE_START.match(lines[index]):
                chunk.append(lines[index])
                index += 1
            reply.report = "\n".join(chunk).strip()
            index += 1 if index < len(lines) and REPORT_END.match(lines[index]) else 0
            continue
        found = STATE_START.match(lines[index])
        if found and reply.state is None:
            chunk = [found.group(1)]
            index += 1
            while index < len(lines) and not STATE_END.match(lines[index]) and not REPORT_START.match(lines[index]) and not marker.match(lines[index]):
                chunk.append(lines[index])
                index += 1
            reply.state = "\n".join(chunk).strip()
            index += 1 if index < len(lines) and STATE_END.match(lines[index]) else 0
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
    made, reply.unmapped = lenient_actions(body, mask, tools)
    reply.actions.extend(made)
    fence = re.compile(r"^\s*```\s*(bash|sh|shell|zsh)\s*$", re.IGNORECASE)
    heredoc = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
    position = -1
    while position + 1 < len(body):      # a fenced shell block is one command; so is a RUN line that opens a heredoc, with its body and terminator
        position += 1
        line = body[position]
        if mask[position]:
            continue
        if fence.match(line):
            end = position + 1
            while end < len(body) and not body[end].strip().startswith("```"):
                end += 1
            if end < len(body):
                script = "\n".join(body[position + 1:end]).strip("\n")
                for k in range(position, end + 1):
                    mask[k] = True
                if script.strip():
                    reply.actions.append(Action("run", script, order=position))
                position = end
            continue
        found = marker.match(line)
        if not found:
            continue
        kind, value = found.group(1).lower(), found.group(2)
        opener = heredoc.search(value) if kind == "run" else None
        if opener:
            tag, end = opener.group(2), position + 1
            while end < len(body) and body[end].strip() != tag:
                end += 1
            if end < len(body):
                reply.actions.append(Action("run", "\n".join([value] + body[position + 1:end + 1]), order=position))
                for k in range(position, end + 1):
                    mask[k] = True
                position = end
                continue
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

def history_text(entries: Sequence[Mapping[str, Any]], budget: int = HISTORY_CHARS) -> str:
    """One compact entry per earlier call. The latest call's results are shown in full, older ones clipped to ``OLD_RESULT_CHARS``, and clipped further
    (halved, down to the labels alone) while the whole passes ``budget`` characters."""
    if not entries:
        return "Nothing yet: this is your first reply."
    old = OLD_RESULT_CHARS
    text = history_lines(entries, old)
    while len(text) > budget and old > 0:
        old = old // 2 if old > 20 else 0
        text = history_lines(entries, old)
    return text


def history_lines(entries: Sequence[Mapping[str, Any]], old_chars: int) -> str:
    lines: List[str] = []
    last_call = max((position for position, entry in enumerate(entries) if "message" not in entry), default=-1)
    for position, entry in enumerate(entries):
        if "message" in entry:
            full = position > last_call
            lines.append(MESSAGE_LINE + (str(entry["message"]) if full else clip(str(entry["message"]), max(old_chars, 40))))
            continue
        latest = position == last_call
        lines.append(f"Call {entry['call']}:" + (f" NOTE: {entry['note']}" if entry.get("note") else ""))
        for outcome in entry["outcomes"]:
            text = outcome.text if latest else (clip(outcome.text, old_chars) if old_chars else "")
            lines.append(f"  {outcome.label}: {'ok' if outcome.ok else 'FAILED'}" + (f"\n{indent(text)}" if text.strip() else ""))
        if latest and entry.get("advice"):
            lines.append(f"  {entry['advice']}")
        if latest and entry.get("reminder"):
            lines.append(f"  {entry['reminder']}")
    return "\n".join(lines)


def indent(text: str) -> str:
    return "\n".join("    " + line for line in text.rstrip().splitlines())


def build_prompt(goal: str, context: str, folder_map: str, files_text: str, entries: Sequence[Mapping[str, Any]], note: str,
                 earlier_goal: str = "", since_start: bool = False, stable: bool = False, added: Sequence[str] = (), state: str = "", left: Optional[int] = None) -> str:
    """The message of one call. With ``stable`` the goal, context, folder map and start files are in the system text: the message holds the goal's title, the
    files added to the folder since the start, the files changed or added to the view since the start, the history and the note."""
    parts = [f"GOAL:\n{goal.strip()}"]
    if earlier_goal.strip() and earlier_goal.strip() != goal.strip():
        parts.append(f"EARLIER GOAL:\n{earlier_goal.strip()}")
    if state.strip():
        parts.append("YOUR STATE (what you wrote last; rewrite it in every reply that acts" + (f"; {left} calls remain" if left is not None else "") + f"):\n{state.strip()}")
    if stable:
        if added:
            parts.append("NEW FILES IN THE FOLDER SINCE THE START (not in the map above; READ before relying on them):\n" + "\n".join(added[:MAP_ENTRIES]))
        parts += [f"{CHANGED_FILES if since_start else VIEW_FILES}\n{files_text}", f"WHAT HAS HAPPENED SO FAR:\n{history_text(entries)}"]
        if note:
            parts.append(note)
        return "\n\n".join(parts)
    if context.strip():
        parts.append(f"CONTEXT:\n{context.strip()}")
    parts += [f"FOLDER MAP (paths relative to the working folder):\n{folder_map}", f"{CHANGED_FILES if since_start else VIEW_FILES}\n{files_text}",
              f"WHAT HAS HAPPENED SO FAR:\n{history_text(entries)}"]
    if note:
        parts.append(note)
    return "\n\n".join(parts)


# --- running the actions ---------------------------------------------------------------------------------------------------------------

def path_risk(path: str) -> str:
    """Why a path outside the working folder is not to be read unasked (the Folder View's judgment of it and of the folders on its way: credentials, keys,
    backups), or ``""``. A judgment that cannot be had says nothing."""
    try:
        from hubofhubs.the_intelligence.subconscious.folder_view.judgment import path_verdict
        parts = [part for part in path.split(os.sep) if part]
        for start in range(len(parts)):      # judged from each level down: an unhelpful folder on the way (a temp folder) must not hide a risky one below it
            verdict = path_verdict(os.sep + os.sep.join(parts[:start]), "/".join(parts[start:]))
            if verdict and verdict.risky:
                return verdict.reason
    except Exception:  # noqa: BLE001 -- no judgment available: the sandbox still keeps the file read-only
        return ""
    return ""


def snapshot(root: str, skip: Collection[str] = ()) -> Dict[str, Tuple[int, float]]:
    return {rel: (size, mtime) for rel, size, mtime in walk(root, skip=skip)}


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
             tools: Optional[Mapping[str, Tool]] = None, cache_chars: int = 8000,
             select: Optional[Callable[..., Any]] = None, telling: Optional[Telling] = None,
             abandon: Optional[Callable[[int], None]] = None, system_chars: int = SYSTEM_CHARS,
             stop_now: Optional[Callable[[], bool]] = None) -> LoopResult:
    """Work ``goal`` in ``working_dir`` until a call's report is accepted, the model is blocked, ``max_calls`` model calls are spent (the
    ``counter`` is shared with helpers and counts all of them) or ``cancel()`` is true. Never raises. With ``review``, written text in which a code check
    (``unsupported``) finds a figure no source file holds, or a named file that is not in the folder, gets one more call before it is accepted: a
    reviewer that sees only the goal, the files as they are now and those findings (not the worker's reasoning) and corrects the files. Work with no
    such finding is accepted with no extra call: measured on the hard deliverables, reviewing every written text cost a call each and passed no more.

    ``state`` continues an earlier run (its history and view; the files are rendered fresh from disk; calls count from zero for this run) and
    ``save`` gets the new ``LoopState`` after every call's actions. ``inbox`` returns the messages a person sent; ``tools`` are the operations
    the model may ``USE``.

    ``select`` chooses the files put in view before the first call and leaves out the folders not worth scanning: the entry point of the Folder View
    solution, called as ``select(goal, context, root, budget_chars, file_limit=...)`` and returning its ``FolderChoice``. When none is given the hub's
    selected implementation of the solution is used (resolved by name from the records), so the choice stays swappable by metric; a caller that holds
    more evidence binds it, for instance ``functools.partial(arm.choose, trail=...)``.

    ``telling`` is the structured account for a surface (see ``Telling``): a step per action (running before a command starts, done or failed after),
    a ``message-received`` step when the inbox is drained, a helper's start and end under its parent, and the calls used so far after each model call.
    The ``emit`` strings go on as before. With a ``cancel`` a model call in flight is given up as soon as ``cancel()`` is true: the call runs on its own
    thread, ``abandon(thread id)`` may end what it started (the Claude CLI provider kills its process group), the state saved before the call is
    kept, and a later run resumes from it."""
    result = LoopResult()
    try:
        loop(result, goal, working_dir, complete, context, max_calls, depth, cancel, emit, command_timeout, environment, wrap, view_chars,
             counter if counter is not None else CallCounter(max_calls), review, state, save, inbox, tools, cache_chars, select, telling, abandon,
             system_chars, stop_now)
    except Exception as error:  # noqa: BLE001 -- the loop reports a failure, it does not raise
        result.met = False
        result.error = result.error or f"the loop failed: {type(error).__name__}: {error}"
        result.ended = result.ended or "failed"
    return result


def loop(result: LoopResult, goal: str, working_dir: str, complete, context: str, max_calls: int, depth: int, cancel, emit, command_timeout: float,
         environment, wrap, view_chars: int, counter: CallCounter, review: bool = True, state: Optional[LoopState] = None,
         save: Optional[Callable[[LoopState], None]] = None, inbox: Optional[Callable[[], Sequence[str]]] = None,
         tools: Optional[Mapping[str, Tool]] = None, cache_chars: int = 8000, select: Optional[Callable[..., Any]] = None,
         telling: Optional[Telling] = None, abandon: Optional[Callable[[int], None]] = None, system_chars: int = SYSTEM_CHARS,
         stop_now: Optional[Callable[[], bool]] = None) -> None:
    root = os.path.abspath(working_dir)
    say = emit or (lambda _text: None)
    tell = telling if telling is not None else Telling(None)
    select = select or selected_folder_view()
    chosen = select(goal, context, root, view_chars, file_limit=SNAPSHOT_FILES)
    skip = frozenset(x.path.rstrip('/') for x in chosen.left_out if not x.is_file)
    left_out = list(chosen.left_out)
    files, _ = listing(root, skip, left_out)
    view = View(root, view_chars, skip, select)
    if chosen.left_out:
        say(f"{len(chosen.left_out)} folders or files left out of the scan: {', '.join(x.path for x in chosen.left_out[:5])}")
    entries: List[Dict[str, Any]] = []
    changed: "OrderedDict[str, None]" = OrderedDict()
    seen: "OrderedDict[str, None]" = OrderedDict()
    earlier_goal = ""
    earlier_calls = 0
    state_text = ""
    repeats = Repeats()
    if state is None:
        view.start(chosen.picks, goal)
    else:
        earlier_goal = state.goal
        earlier_calls = int(state.calls)
        state_text = bounded_state(state.state)
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
    if wrap:
        system += "\n\nCommands can write inside the working folder and in /tmp, which is kept for the whole run (across a stop and a resume); everything else is read-only."
    # Everything that does not change during a run lives in the system text, in this order: the instructions, the goal, the context, the folder map as it was
    # at the start and the files in view at the start. The message then holds only a one-line title of the goal, what changed or was added since, the
    # history and the note. When the stable content does not fit ``system_chars``, files leave the view (the lowest priority first) and the map lists them
    # as files to READ; the goal and the context are always kept whole. A small run keeps all of it in the message, where it is cheaper.
    start_listing = listing(root, skip, left_out)
    start_paths = {rel for rel, _size in start_listing[0]}
    start_blocks = view.blocks()
    stable = len(goal) + len(context) + sum(len(b) for b in start_blocks.values()) + len(start_listing[1]) >= cache_chars
    goal_shown, start, start_map = goal, {}, ""
    if stable:
        system += f"\n\nGOAL (the full text; the message names it by its first line):\n{goal.strip()}"
        if context.strip():
            system += f"\n\nSTANDING CONTEXT:\n{context.strip()}"
        title = next((line.strip() for line in goal.splitlines() if line.strip()), "")
        goal_shown = clip(title, GOAL_TITLE_CHARS) + " (the full goal is in your instructions)"
        for rel in reversed(list(view.files)):      # over budget: the files used least go first (never the goal or the context)
            fixed = len(system) + len(start_listing[1]) + len(START_FILES) + sum(len(b) + 1 for b in start_blocks.values()) + 200
            if fixed <= system_chars or not start_blocks:
                break
            if rel in start_blocks:
                del start_blocks[rel]
                view.files.pop(rel, None)
        start = start_blocks
        start_map = marked(start_listing[1], list(start))
        system += f"\n\nFOLDER MAP AT THE START (paths relative to the working folder):\n{start_map}"
        if start:
            system += f"\n\n{START_FILES}\n" + "\n".join(start[rel] for rel in sorted(start))
        context = ""

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
            tell.step("message-received", message.strip(), "done", step_id=f"message-{tell.count('message')}")
        return got

    def ask(system_text: str, prompt: str) -> str:
        """One model call. With a ``cancel`` it runs on a thread of its own and is given up when ``cancel()`` turns true."""
        interrupt = stop_now or cancel      # what gives up a call in flight: a person's stop, not a wall-clock cap (that waits for the call and stops between calls)
        if interrupt is None:
            return complete(system_text, prompt)
        box: Dict[str, Any] = {}

        def go() -> None:
            try:
                box["text"] = complete(system_text, prompt)
            except BaseException as error:  # noqa: BLE001 -- handed to the caller's thread
                box["error"] = error
        worker = threading.Thread(target=go, daemon=True)
        worker.start()
        while True:
            worker.join(CANCEL_POLL_SECONDS)
            if not worker.is_alive():
                break
            if interrupt():
                if abandon is not None and worker.ident is not None:
                    try:
                        abandon(worker.ident)
                    except Exception:  # noqa: BLE001 -- a failed kill never hides the stop
                        pass
                raise Abandoned()
        if "error" in box:
            raise box["error"]
        return box.get("text", "")

    saved_at: List[Any] = [None]

    def persist(force: bool = False) -> None:
        """Hand ``save`` the state, once per call (and again when messages were added since)."""
        marker = (own_calls, len(entries))
        if save is None or (saved_at[0] == marker and not force):
            return
        saved_at[0] = marker
        try:
            save(LoopState(goal=goal, entries=[dict(e) for e in entries], view=list(view.files.items()), changed=list(changed),
                           read=list(seen), calls=earlier_calls + own_calls, state=state_text, ended=result.ended))
        except Exception:  # noqa: BLE001 -- a store that cannot write never ends a run
            pass
    last_text = ""
    idle = 0      # replies in a row that used no action
    single_reads = 0      # replies in a row that held one read-only command and nothing else
    advice = ""
    own_calls = 0
    check_passed = False
    unfinished = 0      # reports in a row refused because the STATE still listed next steps
    while True:
        if own_calls:
            persist()
        if cancel is not None and cancel():
            result.error, result.ended = "the run was cancelled", "cancelled"
            break
        if not counter.take():
            result.error, result.ended = f"the call limit ({counter.limit}) was spent before the work was finished", "call_limit"
            break
        fetch()
        own_calls += 1
        result.calls += 1
        files_text, shown = view.render(start)
        current = listing(root, skip, left_out)
        folder_map = marked(current[1], shown)
        added = sorted({rel for rel, _size in current[0]} - start_paths) if stable else []
        for rel in shown:
            seen.setdefault(rel)
        note = ""
        if counter.left() == 0:
            note = "This is your last call: finish with a REPORT now, saying what is done and what is not."
        elif counter.left() == 1:
            note = "One call remains after this one: aim to finish with a REPORT."
        try:
            message = build_prompt(goal_shown, context, folder_map, files_text, entries, note, earlier_goal, bool(start), stable, added, state_text, counter.left())
            log.info("loop %s call %d: system %d chars, message %d chars (goal %d, context %d, folder map %d, files %d, history %d)", tell.agent, own_calls,
                     len(system), len(message), len(goal_shown), len(context), len(folder_map), len(files_text), len(history_text(entries)))
            text = ask(system, message) or ""
        except Abandoned:       # stopped while the model worked: the call did not happen, the state saved before it is what a resume continues from
            own_calls -= 1
            result.calls -= 1
            result.error, result.ended = "the run was cancelled", "cancelled"
            break
        except Exception as error:  # noqa: BLE001
            result.error, result.ended = f"the model call failed: {type(error).__name__}: {error}", "model_failed"
            break
        tell.send("usage", calls=counter.used)
        reply = parse_reply(text, tools=bool(tools))
        entry: Dict[str, Any] = {"call": earlier_calls + own_calls, "note": " | ".join(reply.notes), "outcomes": [], "advice": "", "reply": text}
        result.log.append({"call": own_calls, "reply": text, "outcomes": entry["outcomes"]})
        entries.append(entry)
        late = fetch()     # a message that came in while the model worked: unseen by this reply
        if reply.actions or reply.report is not None:
            if reply.state is not None:
                state_text = bounded_state(reply.state)
            elif reply.actions and not reply.notes:
                entry["reminder"] = ("Your reply had no STATE, so your last one stays. Rewrite it in your next reply: done, learned (the facts), next, failed and not to retry. "
                                     f"{counter.left()} calls remain.")
        only = reply.actions[0] if len(reply.actions) == 1 and reply.report is None else None
        single_reads = single_reads + 1 if only is not None and read_only(only) else 0
        if single_reads >= 3:
            entry["reminder"] = (entry.get("reminder", "") + f" You have used one read-only command per reply {single_reads} times in a row. Batch: put several commands, "
                                 "and a script file written with a heredoc, in one reply; you have limited calls.").strip()
        for note_line in reply.notes:      # a NOTE adds a line to the STATE
            state_text = bounded_state(state_text + "\n" + note_line)
        if reply.notes:
            last_text = reply.notes[-1]
        if reply.report is not None:
            last_text = reply.report or last_text
        if reply.blocked:
            result.error, result.ended = f"blocked: {reply.blocked}", "blocked"
            result.report = last_text
            break
        if not reply.actions and reply.report is None:
            if own_calls == 1 and text.strip() and not reply.notes and not late and not reads_as_work(text, reply):
                result.met, result.report, result.ended = True, text.strip(), "met"
                break
            if late:
                entry["advice"] = MESSAGE_ADVICE
                continue
            idle += 1
            if idle >= 2:      # two replies in a row without an action: not met, with what the run has so far, and the saved session can be resumed
                result.error = "the model did not use the action protocol twice in a row" + (f" (markup it wrote that names no action: {reply.unmapped!r})" if reply.unmapped else "")
                result.ended = "no_action"
                result.report = last_text
                break
            entry["advice"] = (f"Your last reply held markup that could not be mapped to an action: {reply.unmapped!r}. Write the plain lines (RUN:, READ:, CHECK:, "
                               "an edit block) instead." if reply.unmapped else NO_ACTION_ADVICE)
            continue
        idle = 0
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
            step_id = tell.step(action.kind, action.text, "running" if action.kind in ("run", "use", "delegate") else "done") \
                if action.kind in ("run", "use", "delegate") else ""
            outcome = execute(action, root, view, changed, seen, result, depth, complete, context, max_calls, cancel, emit, command_timeout,
                              environment, wrap, view_chars, counter, codes, tools, tell, abandon, system_chars, repeats, stop_now)
            entry["outcomes"].append(outcome)
            tell.step(action.kind, action.text, "done" if outcome.ok else "failed", step_id=step_id, detail="" if outcome.ok else outcome.text)
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
        stuck_checks: List[str] = []
        for action in checks:
            before = snapshot(root, view.skip)
            check_id = tell.step("check", action.text)
            done = run_command(action.text, working_dir=root, timeout=command_timeout, environment=environment, wrap=wrap, limit=COMMAND_LIMIT)
            result.commands += 0 if done.refused else 1
            track(root, before, changed, view.skip)
            ok = done.code == 0 and not done.refused
            tell.step("check", action.text, "done" if ok else "failed", step_id=check_id, detail="" if ok else f"exit {done.code}")
            passed = passed and ok
            check_passed = check_passed or ok
            check_text = f"exit {done.code}\n{done.output}".strip()
            if ok:
                repeats.success("CHECK " + normalised(action.text))
            else:
                count, line = repeats.failure("CHECK " + normalised(action.text), check_text)
                if count >= 2:
                    stuck_checks.append(first_error(check_text))
                    check_text += (f"\nThis check has now failed {count} times for the same reason ({first_error(check_text)}). It cannot pass by repeating it. A REPORT is accepted "
                                   "with this check still failing if it states exactly what remains for a person and why; the run then ends not met, with your report.")
            entry["outcomes"].append(Outcome(f"CHECK {short(action.text)}", ok, check_text))
            say(f"call {own_calls}: check {'passed' if ok else 'failed'}")
        if reply.report is None:
            continue
        if late:
            entry["advice"] = MESSAGE_ADVICE
        elif checks and not passed and stuck_checks and reply.report:
            # A check that cannot pass by repeating it, and a report that says what remains: the run ends not met, with the report, so the work done is shown.
            result.met, result.partial, result.report, result.ended = False, True, reply.report, "partial"
            result.error = f"the check could not pass ({stuck_checks[0]}); the report says what remains for a person"
            break
        elif new_reads and not other_work and not checks:
            entry["advice"] = "You read files or used a tool in this reply, so your REPORT was written before seeing the result. It is in view now: report from it."
        elif not failed and next_steps(reply.state if reply.state is not None else state_text):
            remaining = next_steps(reply.state if reply.state is not None else state_text)
            unfinished += 1
            if unfinished >= 2:      # the model wrote the same kind of report again: the run ends not met with what it has, so nobody reads it as finished
                result.met, result.partial, result.report, result.ended = False, True, reply.report, "unfinished"
                result.error = f"the report was written while the STATE still listed next steps ({remaining})"
                break
            entry["advice"] = (f"Your REPORT was not accepted: your STATE still lists next steps ({remaining}). The run is not finished. Do them now, then report. "
                               "If what remains waits on a person, reply BLOCKED: <what and why> instead of REPORT.")
        elif failed:
            entry["advice"] = f"Your REPORT was not accepted because these actions failed: {'; '.join(failed)}. Fix them and report again."
        elif checks and not passed:
            entry["advice"] = "Your REPORT was not accepted because CHECK did not exit 0 (see above). Fix the cause, then report again with the CHECK."
        elif not checks and any(code != 0 for code in codes):
            entry["advice"] = "Your REPORT was not accepted because a RUN exited non-zero (see above). Fix the cause, then report again."
        else:
            result.met, result.report, result.ended = True, reply.report, "met"
            found = unsupported(root, list(changed), skip=view.skip) if review and changed else []
            if (found or (review == REVIEW_PROSE and any(prose(rel) for rel in changed))) and counter.take():
                result.calls += 1
                outcomes = reviewed(goal, context, root, view, changed, complete, found, system, start)
                result.log.append({"review": True, "outcomes": outcomes})
                say(f"review: {'no change' if not outcomes else str(len(outcomes)) + ' correction(s)'}")
            break
        last_text = reply.report or last_text
        result.report = last_text
    result.report = result.report or last_text
    result.state = state_text
    if not result.met and (not result.report.strip() or says_actions(result.report)):
        result.report = state_text      # never raw action markup: the last accepted note or report, else the working memory
    result.ended = result.ended or ("met" if result.met else "failed")
    result.changed = list(changed)
    result.read = list(seen)
    persist(force=True)


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


def unsupported(root: str, changed: Sequence[str], limit: int = 20, skip: Collection[str] = ()) -> List[str]:
    """What code alone can tell about written text, with no model: each figure in a changed prose file that appears in no other file of the folder,
    and each file it names that is not in the folder. A figure worked out from the sources is listed too; the reviewer decides."""
    written = {rel: read_text(Path(root) / rel) or "" for rel in changed if prose(rel)}
    if not written:
        return []
    paths = [rel for rel, _, _ in walk(root, skip=skip)]
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


def reviewed(goal: str, context: str, root: str, view: View, changed: "OrderedDict[str, None]", complete, found: Sequence[str] = (),
             system: str = "", start: Optional[Mapping[str, str]] = None) -> List[Outcome]:
    """One review of finished work by a call that sees the goal and the files as they are, never the worker's replies. Its edit blocks are applied to
    the files the work changed (a reviewer corrects the work, it does not widen it); any other reply changes nothing. A failure changes nothing."""
    for rel in changed:
        if read_text(Path(root) / rel) is not None:
            view.add(rel, named=True)
    files_text, shown = view.render(start)
    prompt = "\n\n".join(filter(None, [f"GOAL:\n{goal.strip()}", f"CONTEXT:\n{context.strip()}" if context.strip() else "",
                                       f"FILES WRITTEN OR CHANGED BY THE WORK: {', '.join(changed)}",
                                       f"{CHANGED_FILES if start else VIEW_FILES}\n{files_text}",
                                       ("FOUND BY A CODE CHECK (certain, not a judgment; list each under UNSUPPORTED and deal with it: keep a figure only "
                                        "where the written file shows the arithmetic from figures that are in the sources):\n" + "\n".join(found)) if found else "",
                                       REVIEW_ROLE + REVIEW_SYSTEM]))
    try:      # the same system text as the worker's calls, so the files it holds are not paid for again; the reviewer's role is in the message
        reply = parse_reply(complete(system or REVIEW_SYSTEM, prompt) or "")
    except Exception:  # noqa: BLE001 -- a review that cannot run leaves the accepted work as it is
        return []
    outcomes = []
    for action in reply.actions:
        if action.kind == "edit" and action.text.strip().lstrip("./") in changed:
            outcomes.append(apply_block(action, root)[0])
    return outcomes


def execute(action: Action, root: str, view: View, changed: "OrderedDict[str, None]", seen, result: LoopResult, depth: int, complete, context: str,
            max_calls: int, cancel, emit, command_timeout: float, environment, wrap, view_chars: int, counter: CallCounter,
            codes: List[int], tools: Optional[Mapping[str, Tool]] = None, tell: Optional[Telling] = None,
            abandon: Optional[Callable[[int], None]] = None, system_chars: int = SYSTEM_CHARS, repeats: Optional[Repeats] = None, stop_now: Optional[Callable[[], bool]] = None) -> Outcome:
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
        target = os.path.expanduser(action.text.strip())
        base = Path(root).resolve()
        try:
            path = inside(Path(root), action.text)
            rel = os.path.relpath(path, base).replace(os.sep, "/")
        except (ValueError, OSError):
            # A file outside the working folder may be read (not written), shown like any other: unless the Folder View judgment finds its path risky (a
            # credentials folder, a key file).
            path = Path(target) if os.path.isabs(target) else (base / target)
            path = Path(os.path.normpath(path))
            rel = str(path)
            risk = path_risk(str(path))
            if risk:
                return Outcome(label, False, f"not read: {risk}")
        if path.is_dir():
            return Outcome(label, False, f"{action.text!r} is a folder; list it with RUN: ls and read a file in it")
        if not path.exists():
            return Outcome(label, False, "no such file")
        if read_text(path) is None:
            return Outcome(label, False, "not a readable text file (binary, or larger than 2 MB, or not readable by this account)")
        known = rel in view.files
        view.add(rel)
        return Outcome(label, True, "already in view" if known else "added to view; its text is in view from the next reply")
    if action.kind == "run":
        label = f"RUN {short(action.text)}"
        key = "RUN " + normalised(action.text)
        refused_again = repeats.refusal(key) if repeats is not None else ""
        if refused_again:
            return Outcome(label, False, refused_again)
        before = snapshot(root, view.skip)
        done = run_command(action.text, working_dir=root, timeout=command_timeout, environment=environment, wrap=wrap, limit=COMMAND_LIMIT)
        track(root, before, changed, view.skip)
        if done.refused:
            return Outcome(label, False, f"refused: {done.refused}")
        result.commands += 1
        codes.append(done.code)
        text = ("timed out; " if done.timed_out else "") + f"exit {done.code}\n{done.output}".rstrip()
        if repeats is not None:
            text += repeats.success(key) if done.code == 0 else repeats.failure(key, text)[1]
        return Outcome(label, done.code == 0, text)
    if action.kind == "use":
        name, _, given = action.text.partition(" ")
        label = f"USE {name} {short(given)}".strip()
        tool = (tools or {}).get(name)
        if tool is None:
            return Outcome(label, False, f"there is no tool named {name!r}; the tools are: {', '.join(tools or {}) or 'none'}")
        key = "USE " + normalised(action.text)
        refused_again = repeats.refusal(key) if repeats is not None else ""
        if refused_again:
            return Outcome(label, False, refused_again.replace("command", "tool call"))
        try:
            text = clip(str(tool.run(given.strip())), TOOL_LIMIT)
            return Outcome(label, True, text + (repeats.success(key) if repeats is not None else ""))
        except Exception as error:  # noqa: BLE001 -- a failing tool is a failed action, not a failed run
            text = f"{type(error).__name__}: {error}"
            return Outcome(label, False, text + (repeats.failure(key, text)[1].replace("command", "tool call") if repeats is not None else ""))
    if action.kind == "delegate":
        label = f"DELEGATE {short(action.text)}"
        if depth <= 0:
            return Outcome(label, False, "delegation is not available here")
        helper = tell.helper(action.text) if tell is not None else None
        child = run_loop(action.text, working_dir=root, complete=complete, context=context, max_calls=max_calls, depth=depth - 1, cancel=cancel,
                         emit=emit, command_timeout=command_timeout, environment=environment, wrap=wrap, view_chars=view_chars, counter=counter,
                         review=False, tools=tools, select=view.select, telling=helper, abandon=abandon, system_chars=system_chars, stop_now=stop_now)      # the parent's review covers what its helpers wrote
        if helper is not None:
            stopped = not child.met and "cancelled" in child.error
            helper.send("agent-ended", state="met" if child.met else "stopped" if stopped else "unmet", calls=child.calls, summary=short(child.report or child.error, 100))
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


def track(root: str, before: Mapping[str, Tuple[int, float]], changed: "OrderedDict[str, None]", skip: Collection[str] = ()) -> None:
    """Add to ``changed`` every file a command created or modified (compared with the snapshot taken before it)."""
    for rel, state in snapshot(root, skip).items():
        if before.get(rel) != state:
            changed.setdefault(rel)
