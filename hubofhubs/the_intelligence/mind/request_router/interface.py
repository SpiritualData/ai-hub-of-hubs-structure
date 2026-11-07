"""The interface of RequestRouting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Optional, runtime_checkable
from esoi import solution

#: The four ways a request can go: told something, something done or changed, text written and handed back in the reply, or not yet understood.
ROUTES = ("information", "act", "draft", "clarify")


@solution("route-a-request", kind="event", entry="route", example={"request": "how many goals are open this week?"})
@runtime_checkable
class RequestRouting(typing.Protocol):
    """Decides, once and in one place, what a request asks of the system: a mapping with ``route`` (one of ``ROUTES``) and ``reason``.
    ``information`` asks to be told something (a question, a status, a count, a lookup), ``act`` asks for something to be done or changed,
    ``draft`` asks for text written and handed back in the reply, and ``clarify`` is a request that cannot be acted on yet. The optional
    ``context`` carries ``view``, the text the Mind can already see. An arm that cannot decide raises and never guesses."""

    def route(self, request: str, context: Optional[Mapping[str, Any]] = None) -> Mapping[str, Any]: ...
