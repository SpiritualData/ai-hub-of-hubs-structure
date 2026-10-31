"""Helpers for a planner's tool schema and for the closed vocabularies its fields carry."""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


def strip_schema_descriptions(schema: Any) -> Any:
    """A deep copy of ``schema`` with every ``description`` key removed.

    A schema's field descriptions are instruction, and on a provider that renders the schema into the prompt (every provider
    without native tool use) they are instruction the caller pays for on EVERY call. Only worth doing when the prompt body
    already states the same thing, which is what a compact planner profile does.
    """
    if isinstance(schema, dict):
        return {k: strip_schema_descriptions(v) for k, v in schema.items() if k != "description"}
    if isinstance(schema, list):
        return [strip_schema_descriptions(v) for v in schema]
    return schema


def compact_schema(tool: Dict[str, Any], kept_descriptions: Iterable[str] = ()) -> Dict[str, Any]:
    """The tool schema with field descriptions stripped, except those of the properties named in ``kept_descriptions``.

    A field that carries a hand-off keeps saying what it is for: with every description stripped, a cheap model can leave
    that field empty so nothing runs.
    """
    compact = strip_schema_descriptions(tool)
    full_props = (tool.get("input_schema") or {}).get("properties") or {}
    props = (compact.get("input_schema") or {}).get("properties") or {}
    for name in kept_descriptions:
        desc = (full_props.get(name) or {}).get("description")
        if desc and name in props:
            props[name]["description"] = desc
    return compact


def normalize_choice(raw: Any, allowed: Iterable[str]) -> Optional[str]:
    """``raw`` as one of ``allowed`` (stripped, lower case), or None when it is missing or not one of them: a hallucinated
    value is "not given", never a guess. Never raises."""
    if isinstance(raw, str) and raw.strip().lower() in tuple(allowed):
        return raw.strip().lower()
    return None
