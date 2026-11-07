"""The interface of ReferenceResolving: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Callable, Mapping, Optional, Sequence, runtime_checkable
from esoi import solution

#: A reference either names one candidate or the resolver abstains; there is no third outcome and no "closest".
OUTCOMES = ("match", "abstain")


@solution("resolve-a-reference", kind="event", entry="resolve",
          example={"phrase": "Ann", "candidates": [{"id": "u1", "name": "Ann Lee"}, {"id": "u2", "name": "Bo Chen"}]})
@runtime_checkable
class ReferenceResolving(typing.Protocol):
    """Says which one of a list of candidates a phrase refers to (a person for an owner's name, a goal for a draft's title, a post for a version of it): a mapping with ``outcome``
    (``match`` or ``abstain``), ``id`` (the candidate's id, empty on an abstain) and ``reason``. A candidate is a mapping with ``id`` and ``name`` and optionally ``aliases`` and
    ``text``. When the phrase does not clearly name exactly one candidate the answer is ``abstain`` and nothing downstream may act on a guess. ``ask``, when given, is the one-argument
    model call a model-judged arm uses in place of Model Plumbing. A match is always one of the candidates offered."""

    def resolve(self, phrase: str, candidates: Sequence[Mapping[str, Any]], context: Optional[Mapping[str, Any]] = None,
                ask: Optional[Callable[[str], str]] = None) -> Mapping[str, Any]: ...
