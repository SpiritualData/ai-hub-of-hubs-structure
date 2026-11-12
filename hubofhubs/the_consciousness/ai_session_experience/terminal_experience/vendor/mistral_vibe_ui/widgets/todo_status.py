"""The todo status row shown above the chat input. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file cli/textual_ui/widgets/todo_status.py); modified from upstream: imports only."""

from __future__ import annotations

from textual import events
from textual.message import Message

from .collapsible import ClickWithoutDragMixin
from .no_markup_static import NoMarkupStatic

TODO_STATUS_ROW_ID = "todo-status-row"


# CSS caps this at one row: it sits above the input, which growing would shift.
class TodoStatusRow(ClickWithoutDragMixin, NoMarkupStatic):
    class Activated(Message):
        pass

    def __init__(self) -> None:
        super().__init__("", id=TODO_STATUS_ROW_ID)
        self.display = False

    def set_summary(self, summary: str | None) -> None:
        self.display = summary is not None
        if summary is not None:
            self.update(summary)

    def on_click(self, event: events.Click) -> None:
        if self._click_is_passive(event):
            return
        event.stop()
        self.post_message(self.Activated())
