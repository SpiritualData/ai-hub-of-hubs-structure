"""The command menu: what the ``/`` menu offers for whatever is typed so far (no screen library in here).

Typing ``/`` lists every command with its one-line description, narrowing as the person types; after a command that takes an argument a consumer's ``choices`` function may
offer the choices instead (the menu then shows them). ``submit`` says whether Enter runs the row at once (a complete command) or only completes it (one that still needs an
argument). The commands are the shared driver's, the screen's own and the consumer's ``commands`` (described by the first line of each function's docstring).
Standard library and the hub only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Mapping, Optional, Sequence

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.polished.words import say

MAX_ITEMS = 40       # the menu scrolls; typing narrows it
MAX_CHOICES = 60


@dataclass
class MenuItem:
    label: str
    description: str
    completion: str
    submit: bool


Choices = Callable[[str], Sequence[MenuItem]]


def builtin_commands() -> List[MenuItem]:
    """The commands every polished screen has."""
    rows = (("/help", "help", True), ("/resume", "resume", True), ("/stop <name>", "stop", False), ("/tree", "tree", True), ("/open <name>", "open", False),
            ("/close <name>", "close", False), ("/who", "who", True), ("/clear", "clear", True), ("/quit", "quit", True))
    return [MenuItem(label, say(f"polished.command.{key}"), label.split(" ")[0] + ("" if submit else " "), submit) for label, key, submit in rows]


def work_commands() -> List[MenuItem]:
    """The commands of the interactive prompt (``ahohs work``) that run between runs."""
    return [MenuItem("/harness [name]", say("polished.command.harness"), "/harness ", False), MenuItem("/new", say("polished.command.new"), "/new", True),
            MenuItem("/session", say("polished.command.session"), "/session", True)]


def custom_commands(extra: Mapping[str, Callable[..., Any]]) -> List[MenuItem]:
    """A consumer's commands: the name, and the first line of the function's docstring as its description."""
    items = []
    for name, function in extra.items():
        doc = (getattr(function, "__doc__", "") or "").strip().splitlines()
        items.append(MenuItem("/" + name.lstrip("/"), doc[0].strip() if doc else say("polished.command.custom"), "/" + name.lstrip("/"), True))
    return items


def menu_items(text: str, commands: Sequence[MenuItem], choices: Optional[Choices] = None) -> List[MenuItem]:
    """What to show for the prompt's current text; an empty list hides the menu."""
    if not text.startswith("/") or "\n" in text:
        return []
    if " " in text:
        if choices is None:
            return []       # past the command's name and into its argument: nothing more to suggest
        try:
            return list(choices(text))[:MAX_CHOICES]
        except Exception:  # noqa: BLE001 -- a consumer's choices that raise leave the menu closed
            return []
    typed = text.strip()
    return [c for c in commands if c.label.startswith(typed)][:MAX_ITEMS]


__all__ = ["Choices", "MenuItem", "builtin_commands", "custom_commands", "menu_items"]
