"""The Model Plumbing arm built on the Vendor Model Caller and the Model Tier Chooser: ``ask(prompt, tier)`` asks whichever vendor the hub
assembled, with the model the tier chooser measured best for the tier. A consumer that wants a one-question model needs no object of its own.
Standard library only."""
from typing import Any, Mapping, MutableMapping, Optional

from esoi import implementation
from esoi import Lazy

from hubofhubs.the_world.model_plumbing.vendor_model_caller.interface import ModelCalling
from hubofhubs.the_world.model_plumbing.model_tier_chooser.interface import TierSelection


class BudgetSpent(RuntimeError):
    """The goal record's budget has no model calls left."""


@implementation("model-plumbing", "via_vendor")
class ViaVendor:
    """Asks a model one question. ``tiers`` maps a tier name to a model id; a tier it does not list is looked up in the tier chooser's
    measured picks, and a name the chooser does not list is used as the model id itself. An empty tier uses ``default_tier``. ``system`` is an
    optional system prompt sent with every question. The chooser is built on first use, so a prompt that names a model never asks for it."""
    REQUIRES = ()     # asks the vendor-model-caller seat; nothing of its own

    def __init__(self, vendor: ModelCalling, chooser: Lazy[TierSelection], tiers: Optional[Mapping[str, str]] = None, default_tier: str = "",
                 system: Optional[str] = None):
        self.vendor = vendor
        self.chooser = chooser
        self.tiers = dict(tiers or {})
        self.default_tier = default_tier
        self.system = system

    def ask(self, prompt: str, tier: str = "", budget: Optional[MutableMapping[str, Any]] = None) -> str:
        if budget is not None and budget.get("model_calls") is not None:     # the goal record's budget, enforced here: one call spends one
            if budget["model_calls"] <= 0:
                raise BudgetSpent("the budget for model calls on this goal is spent")
            budget["model_calls"] -= 1
        name = tier or self.default_tier
        if not name:
            raise ValueError("ask needs a tier or a model id: pass tier=... or build the arm with default_tier")
        chosen = None if name in self.tiers else (self.chooser.choose().get(name) or {}).get("arm")
        model = self.tiers.get(name) or (chosen[1] if chosen else name)
        return self.vendor.answer([{"role": "user", "content": prompt}], model=model, system=self.system)
