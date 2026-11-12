"""Status line shown while the conversation history is compacted. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file cli/textual_ui/widgets/compact.py); modified from upstream: imports only."""

from __future__ import annotations

from .status_message import StatusMessage


class CompactMessage(StatusMessage):
    def __init__(self) -> None:
        super().__init__()
        self.add_class("compact-message")
        self.error_message: str | None = None

    def get_content(self) -> str:
        if self._is_spinning:
            return "Compacting conversation history..."

        if self.error_message:
            return f"Error: {self.error_message}"

        return "Compaction completed."

    def set_complete(self) -> None:
        self.stop_spinning(success=True)

    def set_error(self, error_message: str) -> None:
        self.error_message = error_message
        self.stop_spinning(success=False)
