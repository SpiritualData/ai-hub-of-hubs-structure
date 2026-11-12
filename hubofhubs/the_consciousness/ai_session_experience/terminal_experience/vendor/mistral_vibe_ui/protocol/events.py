"""Event dataclasses the terminal screen consumes from its session feed. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file vibe/app_server/events.py); modified from upstream: only the event dataclasses and the AppServerEvent union are kept; wire parsing, the client projection and the session handoff, queue, retry, MCP and connector events are cut, and the server warning and error and the stats events hold plain fields instead of wire parameter types."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    AgentStatsSnapshot,
    JsonPatchOperation,
    PublicCallbackEntry,
    PublicChildSession,
    PublicHistoryEntry,
    PublicSession,
    PublicSessionState,
    PublicTurn,
)


@dataclass(frozen=True, slots=True)
class HistoryEntryAdded:
    entry: PublicHistoryEntry


@dataclass(frozen=True, slots=True)
class HistoryEntryUpdated:
    previous: PublicHistoryEntry
    entry: PublicHistoryEntry
    patch: list[JsonPatchOperation]


@dataclass(frozen=True, slots=True)
class SessionSnapshot:
    state: PublicSessionState


@dataclass(frozen=True, slots=True)
class SessionUpdated:
    previous: PublicSession
    session: PublicSession
    patch: list[JsonPatchOperation]


@dataclass(frozen=True, slots=True)
class TurnStarted:
    turn: PublicTurn


@dataclass(frozen=True, slots=True)
class TurnCompleted:
    turn: PublicTurn


@dataclass(frozen=True, slots=True)
class StatsUpdated:
    context_window: int
    stats: AgentStatsSnapshot


@dataclass(frozen=True, slots=True)
class ChildSessionUpdated:
    child_session: PublicChildSession


@dataclass(frozen=True, slots=True)
class CallbackRequested:
    callback: PublicCallbackEntry


@dataclass(frozen=True, slots=True)
class ServerWarning:
    message: str


@dataclass(frozen=True, slots=True)
class ServerError:
    message: str


AppServerEvent = (
    HistoryEntryAdded
    | HistoryEntryUpdated
    | SessionSnapshot
    | SessionUpdated
    | TurnStarted
    | TurnCompleted
    | StatsUpdated
    | ChildSessionUpdated
    | CallbackRequested
    | ServerWarning
    | ServerError
)
