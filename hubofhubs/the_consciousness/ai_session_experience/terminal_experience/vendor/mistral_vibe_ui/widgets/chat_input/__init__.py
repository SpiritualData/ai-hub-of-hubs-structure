"""The input of the vendored Vibe screen (text area with history, completion popup, container, sub-agent list). Vendored from Mistral Vibe v2.26.1 (Apache-2.0,
vibe/cli/textual_ui/widgets/chat_input/__init__.py); modified from upstream: imports only."""
from __future__ import annotations

from .body import ChatInputBody
from .container import ChatInputContainer
from .text_area import ChatTextArea

__all__ = ["ChatInputBody", "ChatInputContainer", "ChatTextArea"]
