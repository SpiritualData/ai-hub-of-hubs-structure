"""Static text widgets that never parse markup. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file cli/textual_ui/widgets/no_markup_static.py); modified from upstream: imports only."""

from __future__ import annotations

from typing import Any

from textual.visual import VisualType
from textual.widgets import Static


class NoMarkupStatic(Static):
    def __init__(self, content: VisualType = "", **kwargs: Any) -> None:
        super().__init__(content, markup=False, **kwargs)


class NonSelectableStatic(NoMarkupStatic):
    @property
    def text_selection(self) -> None:
        return None

    @text_selection.setter
    def text_selection(self, value: Any) -> None:
        pass

    def get_selection(self, selection: Any) -> None:
        return None
