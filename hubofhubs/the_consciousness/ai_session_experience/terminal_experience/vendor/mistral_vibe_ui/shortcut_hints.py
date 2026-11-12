"""Keyboard shortcut labels for the hint lines. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file cli/textual_ui/shortcut_hints.py); modified from upstream: imports only."""

from __future__ import annotations

from rich.markup import escape
from textual.content import Content

SHORTCUT_STYLE = "b not dim $primary"


def shortcut(key: str) -> str:
    return f"[{SHORTCUT_STYLE}]{escape(key)}[/]"


def shortcut_hint(markup: str) -> Content:
    return Content.from_markup(markup)


def with_status(status: str | None, hint: Content) -> Content:
    if not status:
        return hint
    return Content(status + "  ") + hint
