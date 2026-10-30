"""The retrieval port: Observation (one result of a gather step) and RetrievalAdapterBase (the read, grep and query surface).

Moved out of a consumer's core (the consumer re-exports both at the old paths). A retrieval adapter reads from some source of
truth and returns small, JSON-serializable observations; nothing here knows a consumer, a database or a file layout.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Observation:
    """One result of a gather step — a read, a grep, or a structured query.

    ``kind`` is "read" | "grep" | "query" | "error". The brain renders these into the
    planner prompt, so they stay small and JSON-serializable.
    """
    kind: str
    rel_path: Optional[str] = None
    locator: Optional[str] = None         # e.g. "lines 10-40", "heading='Metrics'"
    text: Optional[str] = None            # for read/query
    pattern: Optional[str] = None         # for grep
    scope: Optional[str] = None
    hits: List[Dict[str, Any]] = field(default_factory=list)  # for grep
    error: Optional[str] = None
    # A remark for the PLANNER only, never answer content (e.g. a composite's "not answered by"
    # refusals beside another adapter's results). The run loop turns it into a planner_only note.
    planner_note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = {"kind": self.kind}
        for k in ("rel_path", "locator", "text", "pattern", "scope", "error", "planner_note"):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        if self.hits:
            d["hits"] = self.hits
        return d


class RetrievalAdapterBase(abc.ABC):
    @abc.abstractmethod
    def read_section(self, rel_path, *, start_line=None, end_line=None, heading=None, max_bytes=None) -> Observation: ...
    @abc.abstractmethod
    def grep(self, pattern, *, scope=None, max_hits=None) -> Observation: ...

    def query(self, spec: Dict[str, Any]) -> Observation:  # optional default
        return Observation(kind="error", error="query not supported by this adapter")

    # Discovery defaults — non-abstract so existing adapters keep satisfying the ABC. An
    # adapter that can enumerate its sources/operations overrides these; one that can't
    # returns a benign "nothing to discover" Observation (never an error that stalls the loop).
    def list_sources(self) -> Observation:
        return Observation(kind="query", locator="list_sources",
                           text="No sources are enumerable for this adapter.")

    def describe_source(self, name: str, *, path: Optional[str] = None) -> Observation:
        return Observation(kind="query", locator=f"describe_source({name})",
                           text=f"No schema available for source {name!r}.")

    def list_operations(self) -> Observation:
        return Observation(kind="query", locator="list_operations",
                           text="No callable operations are advertised by this adapter.")

    def describe_operation(self, name: str) -> Observation:
        return Observation(kind="query", locator=f"describe_operation({name})",
                           text=f"No detail available for operation {name!r}.")

    # PERSISTED REFERENCE RESOLUTION (optional capability, off by default). An adapter whose content
    # can be a learned card reference overrides ``reference_type`` (to its content ``type``) and the
    # two methods below. Leaving them as-is is the structural "not supported" signal: callers check
    # ``adapter.reference_type is not None``. Non-abstract so every existing adapter keeps satisfying
    # the ABC untouched.
    reference_type: Optional[str] = None

    def make_locator(self, candidate: Any) -> Dict[str, Any]:
        """Default: unsupported — no locator. Override in an adapter that sets ``reference_type``."""
        return {}

    def resolve_reference(self, locator: Dict[str, Any], *, max_chars: int = 2000) -> Optional[str]:
        """Default: unsupported — nothing to resolve. Override in an adapter that sets
        ``reference_type`` to re-fetch fresh content for its own references. Never raises."""
        return None
