"""The interface of FormAndContext: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, runtime_checkable
from esoi import solution


@solution("the-body", kind="event", entry="describe", example="")
@runtime_checkable
class FormAndContext(typing.Protocol):
    """The AI system's form and internal context: ``describe`` reports where the system's data lives (each source says whether it belongs to the
    system or to a person), where its requests come from and which enduring integrations the AI may use, each declared by the system through an
    adapter; ``record_run`` keeps the run record the flow wrote. Body also owns the configuration, environment variables, secrets and stored
    authentication the tools need."""

    def describe(self, person: str = "") -> Mapping[str, Any]: ...
    def record_run(self, run: Mapping[str, Any]) -> str: ...
