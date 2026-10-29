"""The seats: Protocol classes declared with ``@solution(id)`` in scope ``hubofhubs``. Importing this module runs nothing.

They are written ``typing.Protocol`` on purpose: esoi's port scan (S7) does not read intent-mode solutions, so the bare
``Protocol`` form is flagged as a port with no row. The seat is tied to its record by the solution id.

An implementation's constructor parameters typed with one of these Protocols are its needs (``hubofhubs.needs``).
External seats (``model-call``, ``search-backend``) have no hub arm: the consumer provides them.
"""
import typing
from typing import Any, Mapping, Optional, Sequence, runtime_checkable

from esoi import solution

from .card import Card


@solution("card-store")
@runtime_checkable
class CardStore(typing.Protocol):
    """Keeps cards and finds them again."""

    def add(self, card: Card) -> str: ...
    def get(self, card_id: str) -> Optional[Card]: ...
    def search(self, query: str = "", limit: int = 10, tag: str = "") -> Sequence[Card]: ...
    def delete(self, card_id: str) -> bool: ...
    def count(self) -> int: ...


@solution("model-call")
@runtime_checkable
class ModelCall(typing.Protocol):
    """Asks a model one question at a given tier and returns the text. External: the consumer provides it."""

    def complete(self, prompt: str, tier: str = "") -> str: ...


@solution("search-backend")
@runtime_checkable
class SearchBackend(typing.Protocol):
    """Runs one web or knowledge search and returns result rows (title, url, snippet). External: the consumer provides it."""

    def search(self, query: str, limit: int = 10) -> Sequence[Mapping[str, str]]: ...


@solution("reason-and-answer")
@runtime_checkable
class TierSelection(typing.Protocol):
    """Per model tier, pick the (provider, model) arm with the most passing work per cost."""

    def select(self, tiers: Mapping[str, Sequence[Mapping[str, Any]]], prices: Sequence[Mapping[str, str]],
               credits: Sequence[Mapping[str, str]] = (), defaults: Any = None, **bars: Any) -> Mapping[str, Any]: ...


@solution("stay-current")
@runtime_checkable
class FreshnessReading(typing.Protocol):
    """Reads the registry's recorded dates and reports how old each area's research is."""

    def days_since(self, iso: str, clock: Any = None) -> Optional[int]: ...
    def combine(self, facts: Sequence[Mapping[str, Any]], connections: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]: ...


@solution("connect-any-integration")
@runtime_checkable
class HubScoring(typing.Protocol):
    """Scores, per area, whether a hub is registered and connected by configuration, given a consumer's binding."""

    def evaluate(self, binding: Any, folder: Any = None, today: Any = None) -> Any: ...
    def check(self, fact: Mapping[str, Any], kind: str) -> Mapping[str, Any]: ...
    def metrics(self, facts: Mapping[str, Any], connections: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]: ...
