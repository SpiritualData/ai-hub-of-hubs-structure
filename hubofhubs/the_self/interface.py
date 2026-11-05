"""The interface of SelfAnswering: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution


@solution("the-self", kind="event", entry="respond", example={"request": "what is the latest Rust version?", "person": ""})
@runtime_checkable
class SelfAnswering(typing.Protocol):
    """The Self responds to a request as the whole: Consciousness represents the person, Body says where the data lives, Intelligence processes the
    request with the person's authority, World's tools do the outside work, the run is recorded and Integrity audits it, and Consciousness learns
    from feedback. ``respond`` returns a ``Result`` whose ``steps`` say, for every part, whether it ran, was skipped or has no arm yet; no answer is
    made up when a part is missing. ``serve`` takes the waiting requests in through Consciousness and responds to each; ``act_unasked`` responds to
    what Proactivity says is due, most important first as Prioritization orders it. ``cancelled`` stops the request, down to a running agent session. ``coverage`` and ``health`` report the assembly
    and whether the system stays generic."""

    def respond(self, request: str, person: str = "", feedback: Optional[Mapping[str, Any]] = None,
                cancelled: Optional[Callable[[], bool]] = None) -> Any: ...
    def serve(self, person: str = "") -> Sequence[Any]: ...
    def act_unasked(self, schedules: Sequence[Mapping[str, Any]], now: str = "", person: str = "", candidates: Sequence[Mapping[str, Any]] = (),
                    stated: Optional[Mapping[str, Any]] = None, events: Sequence[Mapping[str, Any]] = ()) -> Sequence[Any]: ...
    def coverage(self) -> Mapping[str, Any]: ...
    def health(self) -> Mapping[str, Any]: ...
