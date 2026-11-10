"""The tools a model is trained on, per vendor, and what they do in the hub.

A model does best in the tool names and argument shapes it was trained on, so each provider gets its own set (a dialect): for a Claude model the Claude Code tools
(``Bash``, ``Read``, ``Edit``, ``Write``, ``Glob``, ``Grep``, ``TodoWrite``, ``Task``), for a Gemini model the names of Google's own coding tools (``run_shell_command``,
``read_file``, ``replace``, ``write_file``, ``glob``, ``grep_search``, ``list_directory``, ``write_todos``, ``invoke_agent``), for an OpenAI model ``shell`` (the command as an
argument list), the built-in ``apply_patch`` and ``update_plan``. Whatever the dialect, a call becomes one of a few operations that the hub's own solutions
carry out: ``bash`` is Command Execution (``run_command``, the refusal floor and the sandbox prefix), ``read`` and ``list`` are File Reading, ``write``, ``edit`` and
``patch`` are File Editing (the tolerant search and replace matcher, the V4A patch of Agent Action Format), ``plan`` is the loop's working memory and ``delegate`` is a
sub-agent started by the loop. Every file path stays inside the working folder. Standard library and the hub only.
"""
from __future__ import annotations

import glob as globbing
import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_world.model_plumbing.vendor_model_caller.tool_calling import BUILTIN_APPLY_PATCH, ToolSpec
from hubofhubs.the_world.tools.agent_action_format.v4a import apply_operation
from hubofhubs.the_world.tools.command_running import clip, run_command
from hubofhubs.the_world.tools.file_editing.editblock import apply_edit, find_similar_lines
from hubofhubs.the_world.tools.file_reading.read_files import inside

READ_LINES = 2000
READ_CHARS = 40_000
OUTPUT_CHARS = 20_000
DEFAULT_TIMEOUT = 120.0
MAX_TIMEOUT = 600.0


def obj(properties: Mapping[str, Any], required: Sequence[str] = ()) -> Dict[str, Any]:
    return {"type": "object", "properties": dict(properties), "required": list(required)}


STR, INT, BOOL = {"type": "string"}, {"type": "integer"}, {"type": "boolean"}


def described(kind: Mapping[str, Any], text: str) -> Dict[str, Any]:
    return dict(kind, description=text)


CLAUDE_TOOLS: List[ToolSpec] = [
    ToolSpec("Bash", "Executes a bash command in the working folder and returns its output (stdout and stderr merged) and exit code. Use it to run programs, tests and "
             "scripts and to inspect the folder. Quote paths with spaces. A command that runs too long is stopped at its timeout.",
             obj({"command": described(STR, "The command to execute"), "description": described(STR, "A short description of what the command does"),
                  "timeout": described(INT, "Optional timeout in milliseconds (up to 600000)")}, ["command"])),
    ToolSpec("Read", "Reads a file from the folder. Returns its lines numbered. Reads up to 2000 lines from the start unless offset and limit are given.",
             obj({"file_path": described(STR, "The path of the file to read, absolute or relative to the working folder"),
                  "offset": described(INT, "The line number to start reading from"), "limit": described(INT, "The number of lines to read")}, ["file_path"])),
    ToolSpec("Edit", "Replaces text in a file. old_string must match the file exactly and be unique unless replace_all is true. Read the file before editing it.",
             obj({"file_path": described(STR, "The path of the file to modify"), "old_string": described(STR, "The text to replace"),
                  "new_string": described(STR, "The text to replace it with"), "replace_all": described(BOOL, "Replace every occurrence (default false)")},
                 ["file_path", "old_string", "new_string"])),
    ToolSpec("Write", "Writes a file, creating it (and its folders) or replacing its whole content.",
             obj({"file_path": described(STR, "The path of the file to write"), "content": described(STR, "The content to write")}, ["file_path", "content"])),
    ToolSpec("Glob", "Finds files by a glob pattern such as **/*.py. Returns matching paths, newest first.",
             obj({"pattern": described(STR, "The glob pattern"), "path": described(STR, "The folder to search in (default: the working folder)")}, ["pattern"])),
    ToolSpec("Grep", "Searches file contents with a regular expression. Returns matching lines as path:line:text, or only file names with output_mode files_with_matches.",
             obj({"pattern": described(STR, "The regular expression"), "path": described(STR, "The file or folder to search"), "glob": described(STR, "Only files matching this glob"),
                  "output_mode": {"type": "string", "enum": ["content", "files_with_matches", "count"]}, "-i": described(BOOL, "Ignore case")}, ["pattern"])),
    ToolSpec("TodoWrite", "Keeps the short plan of the work: the full list of steps, each pending, in_progress or completed. Send the whole list every time; finish every step before the final report.",
             obj({"todos": {"type": "array", "items": obj({"content": STR, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}, "activeForm": STR},
                                                          ["content", "status"])}}, ["todos"])),
    ToolSpec("Task", "Hands one separate part of the work to a helper that starts fresh in the same folder and returns its short report. Give it everything it needs in the prompt.",
             obj({"description": described(STR, "A short name for the part"), "prompt": described(STR, "The task for the helper")}, ["description", "prompt"])),
]

GEMINI_TOOLS: List[ToolSpec] = [
    ToolSpec("run_shell_command", "Runs a shell command in the working folder and returns its output and exit code.",
             obj({"command": described(STR, "The command to run"), "description": described(STR, "A short description of the command")}, ["command"])),
    ToolSpec("read_file", "Reads a text file; start_line and end_line (1-based) select a range.",
             obj({"file_path": STR, "start_line": INT, "end_line": INT}, ["file_path"])),
    ToolSpec("write_file", "Writes a file, creating it or replacing its whole content.", obj({"file_path": STR, "content": STR}, ["file_path", "content"])),
    ToolSpec("replace", "Replaces text in a file. old_string must match exactly and be unique unless allow_multiple is true.",
             obj({"file_path": STR, "instruction": described(STR, "What the change does"), "old_string": STR, "new_string": STR, "allow_multiple": BOOL},
                 ["file_path", "old_string", "new_string"])),
    ToolSpec("glob", "Finds files by a glob pattern.", obj({"pattern": STR, "dir_path": STR}, ["pattern"])),
    ToolSpec("grep_search", "Searches file contents with a regular expression.", obj({"pattern": STR, "dir_path": STR, "include_pattern": STR}, ["pattern"])),
    ToolSpec("list_directory", "Lists the files and folders of a directory.", obj({"dir_path": STR}, ["dir_path"])),
    ToolSpec("write_todos", "Keeps the short plan of the work: the full list of steps with their status.",
             obj({"todos": {"type": "array", "items": obj({"description": STR, "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "cancelled"]}},
                                                          ["description", "status"])}}, ["todos"])),
    ToolSpec("invoke_agent", "Hands one separate part of the work to a helper that starts fresh in the same folder and returns its short report.",
             obj({"agent_name": STR, "prompt": STR}, ["prompt"])),
]

OPENAI_TOOLS: List[ToolSpec] = [
    ToolSpec("shell", "Runs a shell command in the working folder. The command is an argument list, for example [\"bash\", \"-lc\", \"ls -la\"].",
             obj({"command": {"type": "array", "items": STR}, "workdir": STR, "timeout_ms": INT}, ["command"])),
    ToolSpec("apply_patch", builtin=BUILTIN_APPLY_PATCH),
    ToolSpec("update_plan", "Keeps the short plan of the work: the full list of steps with their status.",
             obj({"explanation": STR, "plan": {"type": "array", "items": obj({"step": STR, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}},
                                                                          ["step", "status"])}}, ["plan"])),
    ToolSpec("delegate", "Hands one separate part of the work to a helper that starts fresh in the same folder and returns its short report.", obj({"prompt": STR}, ["prompt"])),
]

DIALECTS: Dict[str, List[ToolSpec]] = {"anthropic": CLAUDE_TOOLS, "gemini": GEMINI_TOOLS, "openai": OPENAI_TOOLS}

#: (operation, {canonical argument: this dialect's argument name}) of each tool name; the canonical arguments are command, path, offset, limit, text, old, new, all,
#: pattern, folder, include, items, prompt
OPERATIONS: Dict[str, Tuple[str, Dict[str, str]]] = {
    "Bash": ("bash", {"command": "command", "timeout": "timeout"}), "Read": ("read", {"path": "file_path", "offset": "offset", "limit": "limit"}),
    "Edit": ("edit", {"path": "file_path", "old": "old_string", "new": "new_string", "all": "replace_all"}), "Write": ("write", {"path": "file_path", "text": "content"}),
    "Glob": ("glob", {"pattern": "pattern", "folder": "path"}), "Grep": ("grep", {"pattern": "pattern", "folder": "path", "include": "glob", "mode": "output_mode", "nocase": "-i"}),
    "TodoWrite": ("plan", {"items": "todos"}), "Task": ("delegate", {"prompt": "prompt"}),
    "run_shell_command": ("bash", {"command": "command"}), "read_file": ("read", {"path": "file_path", "start": "start_line", "end": "end_line"}),
    "write_file": ("write", {"path": "file_path", "text": "content"}), "replace": ("edit", {"path": "file_path", "old": "old_string", "new": "new_string", "all": "allow_multiple"}),
    "grep_search": ("grep", {"pattern": "pattern", "folder": "dir_path", "include": "include_pattern"}), "list_directory": ("list", {"folder": "dir_path"}),
    "write_todos": ("plan", {"items": "todos"}), "invoke_agent": ("delegate", {"prompt": "prompt"}),
    "shell": ("bash", {"command": "command", "timeout": "timeout_ms"}), "apply_patch": ("patch", {}), "update_plan": ("plan", {"items": "plan"}), "delegate": ("delegate", {"prompt": "prompt"}),
}
OPERATIONS["glob"] = ("glob", {"pattern": "pattern", "folder": "dir_path"})

#: what each operation is called in the shapes Claude Code's own tools take, so one scan of a run's actions (what it wrote or ran outside the folder) serves every dialect
CANONICAL_NAME = {"bash": "Bash", "write": "Write", "edit": "Edit", "patch": "Write"}


def tools_for(provider: str, *, delegate: bool = True) -> List[ToolSpec]:
    """The tool set of a provider's dialect (the sub-agent tool left out when ``delegate`` is false: a helper at the depth limit cannot start another)."""
    chosen = DIALECTS.get(provider) or CLAUDE_TOOLS
    return [t for t in chosen if delegate or OPERATIONS[t.name][0] != "delegate"]


@dataclass
class Executed:
    text: str
    error: bool = False
    action: Optional[Tuple[str, Dict[str, Any]]] = None   # (Claude Code tool name, input) for the scan of what the run touched outside the folder
    wrote: List[str] = field(default_factory=list)       # paths written, relative to the folder
    read: List[str] = field(default_factory=list)


def numbered(text: str, first: int = 1) -> str:
    return "\n".join(f"{index:6}\t{line}" for index, line in enumerate(text.split("\n"), first))


class ToolBox:
    """Carries out the tool calls of one run in ``root``. ``environment`` and ``wrap`` are what Command Execution takes (the child environment and the sandbox
    prefix); ``plan`` receives the model's list of steps as text (the loop's working memory); ``delegate`` runs a sub-agent on a prompt and returns its report."""

    def __init__(self, root: str, *, environment: Optional[Mapping[str, str]] = None, wrap: Sequence[str] = (), command_timeout: float = DEFAULT_TIMEOUT,
                 plan: Optional[Callable[[str], None]] = None, delegate: Optional[Callable[[str], str]] = None):
        self.root = os.path.abspath(root)
        self.environment, self.wrap, self.command_timeout = environment, tuple(wrap), float(command_timeout)
        self.plan, self.delegate = plan, delegate
        self.commands = 0

    def run(self, name: str, args: Mapping[str, Any]) -> Executed:
        """The result of one call. Never raises: a bad argument or a refused command is an error result the model reads."""
        entry = OPERATIONS.get(name)
        if entry is None:
            return Executed(f"Error: no tool named {name!r}.", True)
        operation, names = entry
        given = {canonical: args.get(own) for canonical, own in names.items() if args.get(own) is not None}
        try:
            return getattr(self, "do_" + operation)(given if operation != "patch" else dict(args))
        except (OSError, ValueError, KeyError) as error:
            return Executed(f"Error: {error}", True)

    def path(self, text: Any) -> Tuple[Path, str]:
        raw = str(text or "")
        if not raw:
            raise ValueError("a path is required")
        base = Path(self.root)
        target = inside(base, os.path.relpath(raw, self.root) if os.path.isabs(raw) else raw)
        return target, target.relative_to(base.resolve()).as_posix() if target != base.resolve() else "."

    # --- Command Execution ------------------------------------------------------------------------------------------------------------

    def do_bash(self, given: Mapping[str, Any]) -> Executed:
        command = given.get("command")
        if isinstance(command, list):     # the argument list OpenAI's shell takes
            words = [str(w) for w in command]
            command = words[-1] if len(words) >= 3 and words[0] in ("bash", "sh") and words[1] in ("-c", "-lc") else " ".join(shlex.quote(w) for w in words)
        command = str(command or "").strip()
        if not command:
            return Executed("Error: a command is required.", True)
        seconds = float(given.get("timeout") or 0) / 1000.0 if given.get("timeout") else self.command_timeout
        done = run_command(command, working_dir=self.root, timeout=max(1.0, min(seconds, MAX_TIMEOUT)), environment=self.environment, wrap=self.wrap, limit=OUTPUT_CHARS)
        if not done.refused:
            self.commands += 1
        body = done.output.strip() or "(no output)"
        text = body if done.code == 0 else f"Exit code {done.code}\n{body}"
        return Executed(text, bool(done.refused) or done.code != 0, ("Bash", {"command": command}))

    # --- File Reading ---------------------------------------------------------------------------------------------------------------------

    def do_read(self, given: Mapping[str, Any]) -> Executed:
        target, rel = self.path(given.get("path"))
        if target.is_dir():
            return Executed(f"Error: {rel} is a folder; use a listing or Bash ls.", True)
        if not target.is_file():
            return Executed(f"Error: file not found: {rel}", True)
        data = target.read_bytes()
        if b"\0" in data[:4096]:
            return Executed(f"Error: {rel} is a binary file ({len(data)} bytes); use a command to inspect it.", True)
        lines = data.decode("utf-8", errors="replace").split("\n")
        if lines and lines[-1] == "":
            lines = lines[:-1]
        start = max(int(given.get("offset") or given.get("start") or 1), 1)
        end = int(given["end"]) if given.get("end") else start - 1 + int(given.get("limit") or READ_LINES)
        chosen = lines[start - 1:min(end, start - 1 + READ_LINES)]
        text = numbered("\n".join(chosen), start)
        note = f"\n[showing lines {start}-{start + len(chosen) - 1} of {len(lines)}]" if len(chosen) < len(lines) else ""
        return Executed(clip(text, READ_CHARS) + note if chosen else "(the file is empty)" + note, False, None, [], [rel])

    def do_list(self, given: Mapping[str, Any]) -> Executed:
        target, rel = self.path(given.get("folder") or ".")
        if not target.is_dir():
            return Executed(f"Error: {rel} is not a folder", True)
        return Executed("\n".join(sorted(p.name + ("/" if p.is_dir() else "") for p in target.iterdir())) or "(empty)")

    def do_glob(self, given: Mapping[str, Any]) -> Executed:
        base, _ = self.path(given.get("folder") or ".")
        found = [p for p in globbing.glob(str(base / str(given.get("pattern") or "*")), recursive=True) if os.path.isfile(p) and ".git" not in Path(p).parts]
        found.sort(key=lambda p: -os.path.getmtime(p))
        return Executed("\n".join(os.path.relpath(p, self.root) for p in found[:500]) or "No files found")

    def do_grep(self, given: Mapping[str, Any]) -> Executed:
        _target, rel = self.path(given.get("folder") or ".")
        flags = "-rnE" + ("i" if given.get("nocase") else "") + {"files_with_matches": "l", "count": "c"}.get(str(given.get("mode") or ""), "")
        include = f"--include={shlex.quote(str(given['include']))} " if given.get("include") else ""
        command = f"grep {flags} {include}--exclude-dir=.git -e {shlex.quote(str(given.get('pattern') or ''))} -- {shlex.quote(rel)}"
        done = run_command(command, working_dir=self.root, timeout=30.0, environment=self.environment, wrap=self.wrap, limit=OUTPUT_CHARS)
        return Executed(done.output.strip() or "No matches found")

    # --- File Editing -----------------------------------------------------------------------------------------------------------------------

    def do_write(self, given: Mapping[str, Any]) -> Executed:
        target, rel = self.path(given.get("path"))
        if target.is_dir():
            return Executed(f"Error: {rel} is a folder", True)
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        target.write_text(str(given.get("text") or ""), encoding="utf-8")
        return Executed(f"The file {rel} has been {'updated' if existed else 'created'}.", False, ("Write", {"file_path": rel}), [rel])

    def do_edit(self, given: Mapping[str, Any]) -> Executed:
        target, rel = self.path(given.get("path"))
        old, new = str(given.get("old") or ""), str(given.get("new") if given.get("new") is not None else "")
        if not target.is_file():
            return Executed(f"Error: file not found: {rel}", True)
        text = target.read_text(encoding="utf-8")
        if not old:
            return Executed("Error: old_string is empty; use the write tool to replace a whole file.", True)
        count = text.count(old)
        if count > 1 and not given.get("all"):
            return Executed(f"Error: old_string occurs {count} times in {rel}; add surrounding lines to make it unique, or replace all occurrences.", True)
        if count >= 1:
            updated = text.replace(old, new) if given.get("all") else text.replace(old, new, 1)
        else:
            updated = apply_edit(text, old, new, fname=rel)      # File Editing's tolerant matcher: indentation and blank-line differences
            if updated is None:
                close = find_similar_lines(old, text)
                return Executed(f"Error: old_string was not found in {rel}." + (f" Closest lines:\n{close}" if close else " Read the file again."), True)
        target.write_text(updated, encoding="utf-8")
        return Executed(f"The file {rel} has been edited.", False, ("Edit", {"file_path": rel}), [rel])

    def do_patch(self, given: Mapping[str, Any]) -> Executed:
        operation = given.get("operation") if isinstance(given.get("operation"), dict) else given
        ok, text = apply_operation(self.root, operation)
        path = str(operation.get("path") or "")
        return Executed(text, not ok, ("Write", {"file_path": path}) if ok else None, [path] if ok else [])

    # --- the loop's own -----------------------------------------------------------------------------------------------------------------------

    def do_plan(self, given: Mapping[str, Any]) -> Executed:
        marks = {"completed": "[x]", "in_progress": "[~]", "cancelled": "[-]"}
        lines = []
        for item in given.get("items") or []:
            if isinstance(item, Mapping):
                lines.append(f"{marks.get(str(item.get('status')), '[ ]')} {item.get('content') or item.get('description') or item.get('step') or ''}")
        if self.plan is not None:
            self.plan("\n".join(lines))
        return Executed("The plan has been updated.")

    def do_delegate(self, given: Mapping[str, Any]) -> Executed:
        if self.delegate is None:
            return Executed("Error: no helper can be started here; do the part yourself.", True)
        return Executed(self.delegate(str(given.get("prompt") or "")) or "(the helper reported nothing)")
