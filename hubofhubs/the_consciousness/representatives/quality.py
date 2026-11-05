"""The quality profile a response is judged against: a named set of criteria, each with a weight and a target value.

What counts as a high quality response depends on the person, the situation and the goals above the request, so the profile is resolved for
each request from the Representative (the person's preferences), Guidance (criteria for this situation) and Prioritization (weights from
priorities the person implies), and falls back to the default profile. The default lists the criteria that public response-quality
recommendations and evaluations name (see the Response Quality area of the registry); it carries no weight or target, because those are fixed
before any method is scored and none has been. A profile change is a new metric version, so scores under different profiles are never mixed.
Standard library only."""
from dataclasses import dataclass, replace
from typing import Any, Mapping, Optional, Tuple


@dataclass(frozen=True)
class Criterion:
    name: str
    meaning: str
    weight: Optional[float] = None      # None: not fixed yet
    target: Optional[float] = None      # None: not fixed yet


@dataclass(frozen=True)
class QualityProfile:
    name: str
    criteria: Tuple[Criterion, ...]
    sources: Tuple[str, ...] = ("default",)     # which of default, representative, guidance, prioritization shaped it

    def criterion(self, name: str) -> Optional[Criterion]:
        return next((c for c in self.criteria if c.name == name), None)


DEFAULT_PROFILE = QualityProfile("default", (
    Criterion("helpfulness", "the response does what the request needs"),
    Criterion("faithfulness to evidence", "every claim is supported by the evidence given"),
    Criterion("groundedness", "claims point to sources a reader can check"),
    Criterion("concision", "no more words than the request needs"),
    Criterion("tone fit", "the tone suits the reader"),
    Criterion("safety", "nothing in the response is harmful or goes beyond the authority given"),
))


def layer(profile: QualityProfile, change: Any, source: str) -> QualityProfile:
    """The profile with ``change`` applied: a ``QualityProfile`` replaces criteria of the same name and adds new ones, and a mapping of
    criterion name to weight sets weights (an unknown name is added with that weight)."""
    if change is None:
        return profile
    criteria = list(profile.criteria)
    if isinstance(change, QualityProfile):
        for one in change.criteria:
            criteria = [one if c.name == one.name else c for c in criteria] if profile.criterion(one.name) else criteria + [one]
    elif isinstance(change, Mapping):
        for name, weight in change.items():
            found = profile.criterion(name)
            criteria = [replace(c, weight=weight) if c.name == name else c for c in criteria] if found else criteria + [Criterion(name, "", weight)]
    else:
        return profile
    return QualityProfile(profile.name, tuple(criteria), profile.sources + (source,))


def resolve_profile(representative: Optional[Mapping[str, Any]] = None, guidance: Optional[Mapping[str, Any]] = None,
                    priorities: Optional[Mapping[str, Any]] = None) -> QualityProfile:
    """The profile for one request: the Representative's own profile when it has one (else the default), then Guidance's criteria, then the
    weights Prioritization derived. With none of the three, the default profile."""
    own = (representative or {}).get("quality_profile")
    profile = own if isinstance(own, QualityProfile) else DEFAULT_PROFILE
    if isinstance(own, QualityProfile):
        profile = QualityProfile(own.name, own.criteria, ("representative",))
    profile = layer(profile, (guidance or {}).get("quality_criteria"), "guidance")
    profile = layer(profile, (priorities or {}).get("quality_weights"), "prioritization")
    if len(profile.sources) > 1:
        profile = QualityProfile("+".join(profile.sources), profile.criteria, profile.sources)
    return profile
