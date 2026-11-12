"""The person's own context settings: one small TOML file outside any repository, read by ``ahohs work`` when it exists and ignored when it does not.

Where the file is, first found wins: the ``--context FILE`` flag, the ``AHOHS_CONTEXT`` variable, then ``$XDG_CONFIG_HOME/ahohs/context.toml`` (``~/.config/ahohs/context.toml``).
No file, no change: a person who never wrote one gets exactly the session they got before.

    [context]
    focus = "garden"            # the named focus: notes at home in it (tag focus:garden) are ranked first; ranking only, nothing is hidden by it
    max_notes = 5               # most notes in the brief (default 5)
    budget_tokens = 1500        # token budget of the notes (default 1500)
    scope = ["team:household"]  # the hard fence: a note tagged for another scope is never shown (default: none)

    [[context.sources]]
    kind = "cards"              # a folder of saved cards, one JSON file each (id, name or title, summary, content, affinity_tags, scope_tags)
    path = "~/notes/cards"
    focus = "garden"            # notes of this source with no home of their own are at home in this focus

    [[context.sources]]
    kind = "folder"             # a folder of text files (.md, .txt), each file one note
    path = "~/notes/garden"
    focus = "garden"

    [[context.sources]]
    kind = "command"            # a program that prints a JSON list of notes on standard output; it is told the focus in AHOHS_FOCUS
    command = ["python3", "~/bin/garden_notes.py"]
    focus = "garden"
    timeout = 60                # seconds (default 60)

A consumer that keeps its context somewhere of its own passes a provider function instead (``sources.load_notes(settings, provider=...)``): ``provider(focus)`` returns notes
(mappings with the card fields above), and a source that fails is a problem line, never a failed run. Standard library only."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Mapping, Optional, Tuple

DEFAULT_RELATIVE = Path("ahohs") / "context.toml"
ENVIRONMENT_KEY = "AHOHS_CONTEXT"
SOURCE_KINDS = ("cards", "folder", "command")
DEFAULT_MAX_NOTES = 5
DEFAULT_BUDGET_TOKENS = 1500
DEFAULT_TIMEOUT = 60.0


@dataclass(frozen=True)
class Source:
    """One place notes come from: a folder of ``cards``, a ``folder`` of text files or a ``command`` that prints them. ``focus`` is the home a note takes when it has none."""
    kind: str
    path: str = ""
    command: Tuple[str, ...] = ()
    focus: str = ""
    timeout: float = DEFAULT_TIMEOUT


@dataclass(frozen=True)
class ContextSettings:
    focus: str = ""
    sources: Tuple[Source, ...] = ()
    max_notes: int = DEFAULT_MAX_NOTES
    budget_tokens: int = DEFAULT_BUDGET_TOKENS
    scope: Tuple[str, ...] = ()
    origin: str = ""          # the file these settings were read from ("" when a consumer built them)

    def usable(self) -> bool:
        """True when there is something to gather from: a source, and a focus to rank by."""
        return bool(self.sources)


def settings_path(explicit: str = "", environ: Optional[Mapping[str, str]] = None) -> Optional[Path]:
    """The file to read, or None when there is none: the one named (``explicit``, then ``AHOHS_CONTEXT``) or the default place. A file that is named and missing is an error
    (``read_settings`` says so); the default place missing is just no settings."""
    environ = environ or {}
    named = (explicit or environ.get(ENVIRONMENT_KEY) or "").strip()
    if named:
        return Path(os.path.expanduser(named))
    base = environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    default = Path(base) / DEFAULT_RELATIVE
    return default if default.is_file() else None


def expand(path: str) -> str:
    return str(Path(os.path.expanduser(str(path))))


def _number(value: Any, name: str, low: float, default: float) -> float:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < low:
        raise ValueError(f"{name} must be a number of at least {low:g}")
    return float(value)


def _source(raw: Any, number: int, default_focus: str) -> Source:
    if not isinstance(raw, Mapping):
        raise ValueError(f"source {number} must be a table")
    kind = str(raw.get("kind") or "")
    if kind not in SOURCE_KINDS:
        raise ValueError(f"source {number}: kind is one of {', '.join(SOURCE_KINDS)}")
    focus = str(raw.get("focus") or default_focus)
    if kind == "command":
        command = raw.get("command")
        if not isinstance(command, (list, tuple)) or not command or not all(isinstance(part, str) and part for part in command):
            raise ValueError(f"source {number}: command is a list of words, the program first")
        words = tuple(expand(part) if part.startswith("~") else part for part in command)
        return Source(kind, command=words, focus=focus, timeout=_number(raw.get("timeout"), "timeout", 1, DEFAULT_TIMEOUT))
    if not raw.get("path"):
        raise ValueError(f"source {number}: a {kind} source needs a path")
    return Source(kind, path=expand(raw["path"]), focus=focus)


def parse_settings(data: Mapping[str, Any], origin: str = "") -> ContextSettings:
    """The settings of a parsed TOML document (the ``[context]`` table); ValueError names what is wrong in plain words."""
    table = data.get("context", data)
    if not isinstance(table, Mapping):
        raise ValueError("[context] must be a table")
    focus = str(table.get("focus") or "").strip()
    raw_sources = table.get("sources") or []
    if not isinstance(raw_sources, (list, tuple)):
        raise ValueError("sources must be a list of [[context.sources]] tables")
    sources: List[Source] = [_source(raw, number, focus) for number, raw in enumerate(raw_sources, 1)]
    scope = table.get("scope") or []
    if isinstance(scope, str):
        scope = [scope]
    if not isinstance(scope, (list, tuple)) or not all(isinstance(tag, str) for tag in scope):
        raise ValueError("scope is a list of tags such as \"team:household\"")
    return ContextSettings(focus=focus, sources=tuple(sources), max_notes=int(_number(table.get("max_notes"), "max_notes", 1, DEFAULT_MAX_NOTES)),
                           budget_tokens=int(_number(table.get("budget_tokens"), "budget_tokens", 100, DEFAULT_BUDGET_TOKENS)), scope=tuple(scope), origin=origin)


def read_settings(path: Path) -> ContextSettings:
    """Read the settings file at ``path``. A missing or unreadable file, or one that breaks the shape above, is a ValueError that says which and where."""
    import tomllib
    try:
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError:
        raise ValueError(f"the context file {path} does not exist") from None
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"the context file {path} cannot be read: {error}") from None
    try:
        return parse_settings(data, origin=str(path))
    except ValueError as error:
        raise ValueError(f"the context file {path}: {error}") from None


def replace_focus(settings: Optional[ContextSettings], focus: str = "") -> Optional[ContextSettings]:
    """The settings with the focus the person named now (``--focus``) in place of the file's; unchanged when none is named."""
    from dataclasses import replace
    return replace(settings, focus=focus.strip()) if settings is not None and focus and focus.strip() else settings


def configured(explicit: str = "", environ: Optional[Mapping[str, str]] = None) -> Optional[ContextSettings]:
    """The person's settings, or None when they wrote none (nothing changes for them). Raises ValueError for a file that is there but wrong."""
    path = settings_path(explicit, environ)
    return read_settings(path) if path is not None else None
