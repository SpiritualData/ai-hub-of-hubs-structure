"""The arms of Agent Action Format: the hub's text protocol, a provider's native tool calls, and a reader that takes either.

A model's reply is run in a folder and each action gives an outcome ``{"kind", "ok", "text"}``. ``text_protocol`` reads the hub loop's protocol (``RUN:``,
``READ:``, ``CHECK:``, search and replace edit blocks) and the function-call markup a model writes when it forgets the protocol. ``native_tool_calls`` reads
a list of tool calls in the shape Claude Code's tools take (``{"name": "Bash", "input": {"command": ...}}`` and Read, Write, Edit, Glob): the format a Claude
model is trained on. ``any_format`` takes either, so a harness that drives several model families does not choose a format by habit. A path outside the
folder is refused by every arm; commands run through ``command_running.run_command``. Standard library and the hub only.
"""
from __future__ import annotations

import glob as globbing
import json
import shlex
from pathlib import Path
from typing import Any, List, Mapping, Optional

from esoi import implementation

from hubofhubs.the_world.tools.command_running import run_command
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import apply_block, parse_reply
from hubofhubs.the_world.tools.file_reading.read_files import inside

OUTPUT_LIMIT = 4000


def outcome(kind: str, ok: bool, text: str = "") -> Mapping[str, Any]:
    return {"kind": kind, "ok": bool(ok), "text": text}


def run_one(command: str, root: str, environment: Optional[Mapping[str, str]], kind: str = "run") -> Mapping[str, Any]:
    done = run_command(command, working_dir=root, environment=environment, limit=OUTPUT_LIMIT)
    return outcome(kind, done.code == 0 and not done.refused, done.output)


@implementation("agent-action-format", "text_protocol")
class TextProtocol:
    """Reads the hub loop's text protocol and the function-call markup a model writes instead of it."""
    REQUIRES = ()
    FORMATS = ("protocol", "function-markup")

    def execute(self, reply: str, working_dir: str, environment: Optional[Mapping[str, str]] = None) -> List[Mapping[str, Any]]:
        root = str(Path(working_dir).resolve())
        out: List[Mapping[str, Any]] = []
        for action in parse_reply(reply).actions:
            if action.kind in ("run", "check"):
                out.append(run_one(action.text, root, environment, action.kind))
            elif action.kind == "read":
                try:
                    out.append(outcome("read", True, inside(Path(root), action.text.strip()).read_text(encoding="utf-8", errors="replace")[:OUTPUT_LIMIT]))
                except (OSError, ValueError) as error:
                    out.append(outcome("read", False, str(error)))
            elif action.kind == "edit":
                result, _created = apply_block(action, root)
                out.append(outcome("edit", result.ok, result.text))
        return out


@implementation("agent-action-format", "native_tool_calls")
class NativeToolCalls:
    """Reads tool calls in the shape of Claude Code's tools: a JSON list (or one object) of ``{"name", "input"}``."""
    REQUIRES = ()
    FORMATS = ("native-tool-calls",)

    def execute(self, reply: str, working_dir: str, environment: Optional[Mapping[str, str]] = None) -> List[Mapping[str, Any]]:
        root = Path(working_dir).resolve()
        try:
            data = json.loads(reply)
        except ValueError:
            return []
        calls = data if isinstance(data, list) else [data]
        out: List[Mapping[str, Any]] = []
        for call in calls:
            if not isinstance(call, dict):
                continue
            name, given = str(call.get("name") or ""), call.get("input") or {}
            try:
                out.append(self.one(name, given if isinstance(given, dict) else {}, root, environment))
            except (OSError, ValueError) as error:
                out.append(outcome(name.lower() or "tool", False, str(error)))
        return out

    def one(self, name: str, given: Mapping[str, Any], root: Path, environment: Optional[Mapping[str, str]]) -> Mapping[str, Any]:
        if name == "Bash":
            return run_one(str(given.get("command") or ""), str(root), environment)
        path = str(given.get("file_path") or given.get("path") or "")
        if name == "Read":
            return outcome("read", True, inside(root, path).read_text(encoding="utf-8", errors="replace")[:OUTPUT_LIMIT])
        if name == "Write":
            target = inside(root, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(given.get("content") or ""), encoding="utf-8")
            return outcome("edit", True, f"wrote {path}")
        if name == "Edit":
            target = inside(root, path)
            text, old, new = target.read_text(encoding="utf-8"), str(given.get("old_string") or ""), str(given.get("new_string") or "")
            if not old or text.count(old) != 1:
                return outcome("edit", False, f"old_string must occur exactly once in {path}; it occurs {text.count(old) if old else 0} times")
            target.write_text(text.replace(old, new, 1), encoding="utf-8")
            return outcome("edit", True, f"edited {path}")
        if name == "Glob":
            pattern = str(given.get("pattern") or "")
            found = sorted(str(Path(p).relative_to(root)) for p in globbing.glob(str(root / pattern), recursive=True) if root in Path(p).resolve().parents)
            return outcome("read", True, "\n".join(found))
        return outcome(name.lower() or "tool", False, f"no tool named {name!r}")


@implementation("agent-action-format", "any_format")
class AnyFormat:
    """Takes native tool calls when the reply is a JSON list of them, else the text protocol: one reader for a harness that drives several model families."""
    REQUIRES = ()
    FORMATS = TextProtocol.FORMATS + NativeToolCalls.FORMATS

    def __init__(self) -> None:
        self.text, self.native = TextProtocol(), NativeToolCalls()

    def execute(self, reply: str, working_dir: str, environment: Optional[Mapping[str, str]] = None) -> List[Mapping[str, Any]]:
        body = reply.strip()
        if body.startswith(("[", "{")):
            found = self.native.execute(body, working_dir, environment)
            if found:
                return found
        return self.text.execute(reply, working_dir, environment)


@implementation("agent-action-format", "apply_patch_v4a")
class ApplyPatchV4A:
    """Reads OpenAI's tool calls: ``apply_patch`` (an operation with a V4A diff) and ``shell`` (a command as an argument list), as a JSON list or one object of ``{"name", "input"}``."""
    REQUIRES = ()
    FORMATS = ("apply-patch-v4a", "openai-shell")

    def execute(self, reply: str, working_dir: str, environment: Optional[Mapping[str, str]] = None) -> List[Mapping[str, Any]]:
        from hubofhubs.the_world.tools.agent_action_format.v4a import apply_operation
        root = str(Path(working_dir).resolve())
        try:
            data = json.loads(reply)
        except ValueError:
            return []
        out: List[Mapping[str, Any]] = []
        for call in data if isinstance(data, list) else [data]:
            if not isinstance(call, dict):
                continue
            name, given = str(call.get("name") or ""), call.get("input") or {}
            if name == "apply_patch":
                ok, text = apply_operation(root, given.get("operation", given) if isinstance(given, dict) else {})
                out.append(outcome("edit", ok, text))
            elif name == "shell":
                command = given.get("command") if isinstance(given, dict) else ""
                words = command if isinstance(command, list) else [str(command or "")]
                script = words[-1] if len(words) >= 3 and words[0] in ("bash", "sh") and words[1] in ("-c", "-lc") else " ".join(shlex.quote(str(w)) for w in words)
                out.append(run_one(script, root, environment))
            else:
                out.append(outcome(name.lower() or "tool", False, f"no tool named {name!r}"))
        return out
