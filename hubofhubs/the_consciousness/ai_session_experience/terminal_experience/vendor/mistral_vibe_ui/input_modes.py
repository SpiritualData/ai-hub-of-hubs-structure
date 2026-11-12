"""Chat-input mode characters. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file vibe/cli/input_modes.py); modified from upstream: imports and header only."""

from __future__ import annotations

from typing import Literal

# The single source of truth for chat-input modes. `>` is the default prompt
# mode; the rest are entered by starting a line with their prefix character
# (slash-command, bash, teleport).
InputMode = Literal["!", "/", ">", "&"]
DEFAULT_MODE: Literal[">"] = ">"
