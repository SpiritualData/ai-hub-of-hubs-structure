"""The interface of DecisionChecking: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Mapping, Optional, runtime_checkable
from esoi import solution

#: How a check ended. ``agreed``: the views that had an opinion agreed. ``adjudicated``: they disagreed and one call decided from quoted evidence.
#: ``abstained``: they disagreed and nothing decided. ``held``: a reply with no confirmed finding. ``repaired``: only the failing spans changed.
#: ``unrepaired``: a confirmed finding could not be repaired within the budget. ``kept``: no view had an opinion, so the draft stands.
OUTCOMES = ("agreed", "majority", "adjudicated", "abstained", "held", "repaired", "unrepaired", "kept")

EXAMPLE_BINDING = {"kind": "pick", "options": [{"id": "a", "text": "Alpha"}, {"id": "b", "text": "Beta"}], "views": [], "max_calls": 4}


@solution("decision-check", kind="event", entry="check", example={"draft": "a", "binding": EXAMPLE_BINDING})
@runtime_checkable
class DecisionChecking(typing.Protocol):
    """Checks a draft decision by small independent checks, each shown only the slice of evidence it needs, and returns the checked decision.

    ``draft`` is a pick (an option id) or a reply (text). ``binding`` is a ``CheckBinding`` (or its mapping): the consumer's ``kind`` (``pick`` or ``reply``), its ``options``,
    its ``views`` (an instruction and an evidence slice each), any ``votes`` it already holds and the ``max_calls`` it allows. ``ask`` is the one-argument model call (Model Plumbing at the
    ``cheap`` tier when none is given). The result holds ``outcome`` (one of ``OUTCOMES``), ``pick`` (a pick) or ``text`` (a reply, changed only at the failing spans), ``calls`` used,
    ``agreement`` (the share of opinions that agree with the result), ``why`` and the per-view ``views`` and ``findings``. The checks run in parallel; a disagreement is decided by one call
    that sees only the disagreeing views and must quote evidence that code finds in them, or the result abstains."""

    def check(self, draft: Any, binding: Any, ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]: ...
