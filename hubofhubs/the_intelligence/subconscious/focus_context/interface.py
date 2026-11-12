"""The interface of FocusContexting: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Mapping, Sequence, runtime_checkable
from esoi import solution
from hubofhubs.the_intelligence.subconscious.focus_context.brief import FocusContext


@solution("focus-context", kind="event", entry="gather", example={"request": "what do my notes say about tomatoes?", "focus": "garden", "notes": [
    {"id": "n1", "title": "Tomatoes", "text": "Plant tomatoes after the last frost.", "affinity_tags": ["focus:garden"]}]})
@runtime_checkable
class FocusContexting(typing.Protocol):
    """Chooses, before a piece of work starts, the saved notes the person already has about their focus (a named home such as a hobby, a practice or a project) that bear on
    the request, and writes the brief the harness is given and the one line the person reads. ``notes`` are mappings with the card fields (``id``, ``title`` or ``name``,
    ``summary``, ``text``, ``affinity_tags``, ``scope_tags``, ``overview``, ``timestamp``) the caller read from the sources the person configured. Notes at home in the focus
    are ranked first (soft, ranking only); a note whose ``scope_tags`` do not meet ``scope`` is never shown (a hard fence). Returns a ``FocusContext``; it reads nothing
    itself and writes nothing."""

    def gather(self, request: str, notes: Sequence[Mapping[str, Any]], focus: str = "", max_notes: int = 5, budget_tokens: int = 1500,
               scope: Sequence[str] = ()) -> FocusContext: ...
