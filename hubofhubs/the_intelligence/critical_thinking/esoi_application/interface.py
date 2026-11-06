"""The interface of EsoiApplying: a Protocol declared with ``@solution``, and the one port of its job, the records location. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


class RecordsSource(typing.Protocol):
    """Where the ESOI records live: the one place a consumer says whether its records are tables in memory (the default), a files tree or the rows of a
    service. ``read`` returns the subject's records as ``{table: {record id: {column: value}}}`` (tables: ``problems``, ``ideals``, ``solutions``,
    ``implementations``, ``metrics``, ``profiles``); ``apply`` carries out one normalized edit and answers ``{"status": ...}`` with ``applied``,
    ``unchanged`` (an ensure-one that found the record already there), ``proposed`` (held until a person approves, with the ``decision`` it waits on)
    or ``refused`` (with the ``reason``, plain)."""

    def read(self, subject: str) -> Mapping[str, Mapping[str, Mapping[str, Any]]]: ...

    def apply(self, edit: Mapping[str, Any]) -> Mapping[str, Any]: ...


@solution("esoi-application", kind="event", entry="apply", example={"change": {}})
@runtime_checkable
class EsoiApplying(typing.Protocol):
    """Applies a proposed change to the specs and metrics of the system as one field edit, or as one ensure-one record, or refuses it with the reason."""

    def apply(self, change: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def read(self, subject: str = "") -> Mapping[str, Mapping[str, Mapping[str, Any]]]: ...
