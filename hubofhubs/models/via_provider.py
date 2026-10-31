"""The model-call arm built on the call-a-model seat: ``complete(prompt, tier)`` asks whichever provider the hub assembled for the
call-a-model seat, so a consumer that wants a one-question model needs no object of its own. Standard library only."""
from typing import Mapping, Optional

from esoi import implementation

from ..seats import ModelCalling


@implementation("model-call", "via_call_a_model")
class ViaCallAModel:
    """Asks a model one question. ``tiers`` maps a tier name to a model id; a tier it does not list is used as the model id itself,
    and an empty tier uses ``default_tier``. ``system`` is an optional system prompt sent with every question."""

    def __init__(self, provider: ModelCalling, tiers: Optional[Mapping[str, str]] = None, default_tier: str = "",
                 system: Optional[str] = None):
        self.provider = provider
        self.tiers = dict(tiers or {})
        self.default_tier = default_tier
        self.system = system

    def complete(self, prompt: str, tier: str = "") -> str:
        name = tier or self.default_tier
        if not name:
            raise ValueError("complete needs a tier or a model id: pass tier=... or build the arm with default_tier")
        return self.provider.answer([{"role": "user", "content": prompt}], model=self.tiers.get(name, name), system=self.system)
