"""Shared constants of the terminal screen, including the colour palette. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file cli/textual_ui/constants.py); modified from upstream: imports only."""

from __future__ import annotations

from enum import StrEnum

# Value persisted for the unpinned "default" model state. Mirrors the schema's
# ``UNPINNED_ACTIVE_MODEL`` sentinel; kept UI-side so the textual layer stays
# free of ``vibe.core`` imports (see tests/cli/textual_ui/test_app_server_boundary).
UNPINNED_ACTIVE_MODEL = ""


class MistralColors(StrEnum):
    RED = "#E10500"
    ORANGE_DARK = "#FA500F"
    ORANGE = "#FF8205"
    ORANGE_LIGHT = "#FFAF00"
    YELLOW = "#FFD800"
