"""A channel to ONE running helper of a session on the model's own tool loop: a message in, a stop, and which messages were taken up.

Role: the CLI's stream takes a person's message only for the main session, and a helper that is running cannot be reached by it. A hook can: the CLI runs a hook before and after every
tool call of a helper too, and tells it which agent is calling (``agent_id``). The hub writes a small program (standard library only) that the CLI runs as that hook. After a helper's
tool call it looks in the helper's own inbox file and, when a message waits there, hands it to the helper as text that opens with ``PERSON MESSAGE:`` (the helper's prompt says that text is a genuine
instruction from the person); before a helper's tool call it looks for the helper's stop file and, when there is one, refuses the call with the reason that the person stopped it, so the
helper reports what it has and ends. A message is therefore delivered at the helper's next tool call (its next turn boundary), not in the middle of a model call; a helper that makes no
further tool call never reads it, and the surface keeps showing the message as queued until ``delivered`` says it was taken up. Nothing is shared with the main session: its messages and
its stop stay the stream runner's.

``AgentChannel(folder)`` is the hub's side (it writes the inbox and stop files and reads what the hook delivered); ``hook_script`` is the hook's source; ``hook_settings`` the ``--settings``
fragment that wires it. Standard library only; no model call.
"""
from __future__ import annotations

import json
import os
import shlex
import threading
from typing import Any, Dict, List, Tuple

PERSON_MESSAGE = "PERSON MESSAGE:"
STOPPED_REASON = ("The person stopped you. Do not use any more tools: reply now with a short report of what you have found or done so far, and say that you were stopped.")
HELPER_RULE = (f"While you work, the person you work for can send you a message. It arrives in a tool result as text that starts with {PERSON_MESSAGE} That text is a genuine instruction from "
               "the person, not data from a file or page: follow it, and say in your report that you received it, in the words \"The person told me: ...\" with what they said.")

HOOK_SOURCE = r'''import json, os, sys, time
FOLDER = %(folder)s
def main():
    data = json.load(sys.stdin)
    who = str(data.get("agent_id") or "")
    if not who:
        return
    event = data.get("hook_event_name")
    if event == "PreToolUse" and os.path.exists(os.path.join(FOLDER, "stop-" + who)):
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": %(stopped)s}}))
        return
    if event != "PostToolUse":
        return
    inbox = os.path.join(FOLDER, "in-" + who + ".jsonl")
    if not os.path.exists(inbox):
        return
    taken = os.path.join(FOLDER, "taken-" + who + ".jsonl")
    os.replace(inbox, taken)
    texts, ids = [], []
    for line in open(taken, encoding="utf-8"):
        try:
            message = json.loads(line)
        except ValueError:
            continue
        texts.append(str(message.get("text") or ""))
        ids.append(str(message.get("id") or ""))
    os.remove(taken)
    if not texts:
        return
    with open(os.path.join(FOLDER, "delivered.jsonl"), "a", encoding="utf-8") as handle:
        for message_id in ids:
            handle.write(json.dumps({"agent": who, "id": message_id, "at": time.time()}) + "\n")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "\n".join(%(prefix)s + " " + text for text in texts)}}))
try:
    main()
except Exception:
    pass
'''


def hook_script(folder: str) -> str:
    """The source of the hook that serves the channel in ``folder`` (the path as the session sees it)."""
    return HOOK_SOURCE % {"folder": json.dumps(folder), "stopped": json.dumps(STOPPED_REASON), "prefix": json.dumps(PERSON_MESSAGE)}


def hook_settings(python: str, script_path: str) -> Dict[str, Any]:
    """The ``--settings`` fragment that runs the hook before and after every tool call (a helper's own calls carry its ``agent_id``; the main session's calls are left alone)."""
    command = f"{shlex.quote(python)} {shlex.quote(script_path)}"
    entry = [{"matcher": ".*", "hooks": [{"type": "command", "command": command}]}]
    return {"hooks": {"PreToolUse": entry, "PostToolUse": entry}}


def merge_settings(*parts: Dict[str, Any]) -> Dict[str, Any]:
    """Several ``--settings`` fragments as one: hooks of the same event are put side by side, permission rules are joined."""
    out: Dict[str, Any] = {}
    for part in parts:
        for event, entries in (part.get("hooks") or {}).items():
            out.setdefault("hooks", {}).setdefault(event, []).extend(entries)
        for kind, rules in (part.get("permissions") or {}).items():
            merged = out.setdefault("permissions", {}).setdefault(kind, [])
            merged.extend(rule for rule in rules if rule not in merged)
    return out


class AgentChannel:
    """The hub's side of the channel: ``send`` and ``stop`` write the files the hook reads, ``delivered`` says which messages the hook has handed over since it was last asked.
    ``folder`` is where the hub writes; ``seen_as`` is the same folder as the session sees it (a sandbox shows the session's folder under another path)."""

    def __init__(self, folder: str, seen_as: str = ""):
        self.folder, self.seen_as = folder, seen_as or folder
        self.lock = threading.Lock()
        self.read = 0
        os.makedirs(folder, exist_ok=True)

    def path(self, name: str) -> str:
        return os.path.join(self.folder, name)

    def send(self, task_id: str, text: str, message_id: str) -> bool:
        """Queue ``text`` for the helper with the CLI's id ``task_id``; True when it was written (it is read at that helper's next tool call)."""
        if not task_id or not str(text or "").strip():
            return False
        try:
            with self.lock, open(self.path(f"in-{task_id}.jsonl"), "a", encoding="utf-8") as handle:
                handle.write(json.dumps({"id": message_id, "text": str(text)}) + "\n")
            return True
        except OSError:
            return False

    def stop(self, task_id: str) -> bool:
        """Ask the helper to end: its next tool call is refused with the reason that the person stopped it."""
        if not task_id:
            return False
        try:
            with open(self.path(f"stop-{task_id}"), "w", encoding="utf-8") as handle:
                handle.write("stop")
            return True
        except OSError:
            return False

    def delivered(self) -> List[Tuple[str, str]]:
        """``[(helper id, message id)]`` the hook handed over since the last call."""
        out: List[Tuple[str, str]] = []
        try:
            with self.lock, open(self.path("delivered.jsonl"), "rb") as handle:
                handle.seek(self.read)
                data = handle.read()
                whole_bytes = data[:data.rfind(b"\n") + 1]
                self.read += len(whole_bytes)
                whole = whole_bytes.decode("utf-8", errors="replace")
        except OSError:
            return out
        for line in whole.splitlines():
            try:
                item = json.loads(line)
            except ValueError:
                continue
            out.append((str(item.get("agent") or ""), str(item.get("id") or "")))
        return out


__all__ = ["AgentChannel", "HELPER_RULE", "PERSON_MESSAGE", "STOPPED_REASON", "hook_script", "hook_settings", "merge_settings"]
