"""Which model providers an agent harness can drive, and the model a (provider, tier) pair means.

An arm of Delegated Agent Sessions is a harness (an implementation class), a provider and a tier, written as an esoi variant name:
``<harness>@provider=<provider>,tier=<tier>``. Each harness class declares the providers it can drive in ``PROVIDERS`` (a tuple of
provider names, or ``ANY`` when it can drive every provider it is given credentials for). A consumer declares the providers it holds
credentials for; an arm is eligible for it only when its provider is one of them and its harness can drive that provider.

The model of a tier comes from the hub's tier chooser (``model_tier_chooser.tiers``), never from a name written here. Nothing in this
module reads the environment: ``credential_names`` says which variables carry a provider's key, and the caller decides what to pass.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Tuple

ANY = "*"   # a harness that drives any provider it is given credentials for

#: other spellings of a provider name, mapped to the tier registry's name
ALIASES = {"google": "gemini", "claude": "anthropic", "chatgpt": "openai"}

#: the environment variables that carry a provider's credentials, in the order a harness reads them
CREDENTIAL_NAMES: Dict[str, Tuple[str, ...]] = {
    "anthropic": ("ANTHROPIC_API_KEY",),
    "openai": ("OPENAI_API_KEY", "OPENAI_BASE_URL"),
    "gemini": ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_AI_API_KEY", "GOOGLE_GENERATIVE_AI_API_KEY"),
    "deepseek": ("DEEPSEEK_API_KEY",),
}


def normalise(provider: str) -> str:
    """The registry's name for ``provider`` (lowercase, aliases resolved)."""
    name = (provider or "").strip().lower()
    return ALIASES.get(name, name)


def normalise_all(providers: Optional[Iterable[str]]) -> Tuple[str, ...]:
    """The declared providers as registry names, in order, without repeats."""
    seen: Dict[str, None] = {}
    for p in providers or ():
        if normalise(p):
            seen[normalise(p)] = None
    return tuple(seen)


def providers_of(implementation: Any) -> Tuple[str, ...]:
    """The providers a harness class (or an instance, or a ``functools.partial`` of one) declares it can drive."""
    target = getattr(implementation, "func", implementation)
    declared = getattr(target, "PROVIDERS", ())
    return (ANY,) if declared == ANY else tuple(normalise(p) for p in declared)


def drives(implementation: Any, provider: str) -> bool:
    """Whether the harness can drive ``provider``."""
    declared = providers_of(implementation)
    return ANY in declared or normalise(provider) in declared


def credential_names(provider: str) -> Tuple[str, ...]:
    """The variables that carry ``provider``'s credentials (empty for a provider with none known)."""
    return CREDENTIAL_NAMES.get(normalise(provider), ())


def model_for(provider: str, tier: str, folder: Any = None) -> Optional[str]:
    """The model a session on ``provider`` runs for ``tier``: the tier chooser's pick for the tier, or None when it has none for that tier. A tier is one of the
    hub's four (``role_tiers.TIERS``, its aliases read: ``strong`` is ``quality``); ``best`` is the best tier's own arm and is never answered with another tier's model.
    A name that is not a tier but is a model the hub serves for the provider (``tiers.served_models``) is that model: a person's explicit choice."""
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers, tiers
    name = role_tiers.normalise(tier)
    if name in role_tiers.TIERS:
        arm = (tiers.choose(folder, available={normalise(provider)}).get(name) or {}).get("arm")
        return arm[1] if arm else None
    return tiers.explicit_model(normalise(provider), tier, folder)
