"""Completion protocols for the chat input. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file vibe/cli/autocompletion/base.py); modified from upstream: imports and header only."""

from __future__ import annotations

from enum import StrEnum
from typing import NamedTuple, Protocol


class CompletionResult(StrEnum):
    IGNORED = "ignored"
    HANDLED = "handled"
    SUBMIT = "submit"


class CompletionEntry(NamedTuple):
    label: str
    description: str


class CompletionView(Protocol):
    def render_completion_suggestions(
        self, suggestions: list[CompletionEntry], selected_index: int
    ) -> None: ...

    def clear_completion_suggestions(self) -> None: ...

    def replace_completion_range(
        self, start: int, end: int, replacement: str, *, suppress_update: bool = False
    ) -> None: ...


class InlineSuggestionView(Protocol):
    def show_inline_suggestion(self, suggestion: str) -> None: ...

    def clear_inline_suggestion(self) -> None: ...

    def replace_completion_range(
        self, start: int, end: int, replacement: str, *, suppress_update: bool = False
    ) -> None: ...
