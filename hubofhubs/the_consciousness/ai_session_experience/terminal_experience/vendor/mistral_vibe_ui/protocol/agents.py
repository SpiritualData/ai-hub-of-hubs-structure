"""Agent safety and agent type enums for the session feed. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file vibe/agents/__init__.py); modified from upstream: imports only (the module is placed at protocol/agents.py)."""

from __future__ import annotations

from enum import StrEnum, auto

__all__ = ["AgentSafety", "AgentType"]


class AgentSafety(StrEnum):
    SAFE = auto()
    NEUTRAL = auto()
    DESTRUCTIVE = auto()
    SMART = auto()
    YOLO = auto()


class AgentType(StrEnum):
    AGENT = auto()
    SUBAGENT = auto()
