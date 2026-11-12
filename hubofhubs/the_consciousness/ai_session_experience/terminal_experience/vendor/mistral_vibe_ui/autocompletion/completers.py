"""Completers for the chat input: slash commands and the base classes (the file-mention completer is cut). Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file vibe/cli/autocompletion/completers.py); modified from upstream: PathCompleter (@file mentions and the file indexer) cut, imports rewritten."""

from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar

from .base import CompletionEntry
from .fuzzy import fuzzy_match


class Completer:
    def get_completions(self, text: str, cursor_pos: int) -> list[str]:
        return []

    def get_completion_items(self, text: str, cursor_pos: int) -> list[CompletionEntry]:
        return [
            CompletionEntry(completion, "")
            for completion in self.get_completions(text, cursor_pos)
        ]

    def get_replacement_range(
        self, text: str, cursor_pos: int
    ) -> tuple[int, int] | None:
        return None


class CommandCompleter(Completer):
    def __init__(self, entries: Callable[[], list[CompletionEntry]]) -> None:
        self._get_entries = entries

    def _build_lookup(
        self,
    ) -> tuple[list[str], dict[str, str], dict[str, CompletionEntry]]:
        descriptions: dict[str, str] = {}
        entry_by_alias: dict[str, CompletionEntry] = {}
        for entry in self._get_entries():
            descriptions[entry.label] = entry.description
            entry_by_alias[entry.label] = entry
        return list(descriptions.keys()), descriptions, entry_by_alias

    def _head_word(self, text: str, cursor_pos: int) -> str:
        head = text.split(" ", 1)[0]
        return head[1 : min(cursor_pos, len(head))].lower()

    _PROMOTED_BOOSTS: ClassVar[dict[str, float]] = {"/help": 2.0, "/config": 1.0}

    def _fuzzy_filter(self, aliases: list[str], search_str: str) -> list[str]:
        query = search_str[1:]
        slash_aliases = [a for a in aliases if a.startswith("/")]
        scored: list[tuple[str, float]] = []
        for alias in slash_aliases:
            boost = self._PROMOTED_BOOSTS.get(alias, 0.0)
            if not query:
                scored.append((alias, boost))
                continue
            candidate = alias[1:].lower()
            result = fuzzy_match(query, candidate)
            if result.matched:
                scored.append((alias, result.score + boost))
        scored.sort(key=lambda x: x[1], reverse=True)
        return [alias for alias, _ in scored]

    def get_completions(self, text: str, cursor_pos: int) -> list[str]:
        if not text.startswith("/"):
            return []

        aliases, _, _ = self._build_lookup()
        search_str = "/" + self._head_word(text, cursor_pos)
        return self._fuzzy_filter(aliases, search_str)

    def get_completion_items(self, text: str, cursor_pos: int) -> list[CompletionEntry]:
        if not text.startswith("/"):
            return []

        _, descriptions, entry_by_alias = self._build_lookup()
        search_str = "/" + self._head_word(text, cursor_pos)
        return [
            entry_by_alias.get(
                alias, CompletionEntry(alias, descriptions.get(alias, ""))
            )
            for alias in self._fuzzy_filter(list(entry_by_alias.keys()), search_str)
        ]

    def get_replacement_range(
        self, text: str, cursor_pos: int
    ) -> tuple[int, int] | None:
        if not text.startswith("/"):
            return None
        # Replace the whole command word, from the start up to the first
        # whitespace (space or newline), regardless of caret position. Ending at
        # the caret would corrupt the command when accepting mid-token; ending at
        # len(text) would wipe any following lines (chat input allows newlines).
        end = next((i for i, char in enumerate(text) if char.isspace()), len(text))
        return (0, end)


class MultiCompleter(Completer):
    def __init__(self, completers: list[Completer]) -> None:
        self.completers = completers

    def get_completions(self, text: str, cursor_pos: int) -> list[str]:
        all_completions = []
        for completer in self.completers:
            completions = completer.get_completions(text, cursor_pos)
            all_completions.extend(completions)

        seen = set()
        unique = []
        for comp in all_completions:
            if comp not in seen:
                seen.add(comp)
                unique.append(comp)

        return unique

    def get_replacement_range(
        self, text: str, cursor_pos: int
    ) -> tuple[int, int] | None:
        for completer in self.completers:
            range_result = completer.get_replacement_range(text, cursor_pos)
            if range_result is not None:
                return range_result
        return None
