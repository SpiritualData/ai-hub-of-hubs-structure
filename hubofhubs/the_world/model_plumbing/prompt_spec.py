"""Prompt specifications: the one standard way a model prompt is declared, rendered and found.

A ``PromptSpec`` carries what a prompt usually leaves implicit at its call site: a stable ``id``, the ``solution`` and
``metric`` ids that justify the call (plain strings; checking them against a consumer's records is the consumer's test),
the model ``tier``, the ``cache_layer`` where the text sits, the template's ``inputs``, the reply ``output_schema`` and
the ``template`` itself. ``writes_text`` marks a prompt that tells a model to write text a person may read; ``render`` then
always carries a no-em-dash rule.

The consumer's own collaborators are injected, never imported: ``bind_spec_class(tiers, on_render)`` returns a spec class
that validates ``tier`` against the consumer's tier names and calls ``on_render(spec_id)`` each time a spec renders (a usage
log tags the model call that follows). A ``PromptRegistry`` holds the specs of one spec class. No model call is made here
and nothing here reads the environment.
"""
from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Any, Callable, ClassVar, Dict, Mapping, Optional, Tuple, Type

# The cache layers of a layered prompt plus ``none`` for a one-shot prompt that shares no prefix with another call.
CACHE_LAYERS = ("head", "context", "tail", "none")

# A tier chosen by a configured setting, not fixed by the prompt.
CALLER_TIER = "caller"

# Appended by ``render`` to every prompt that tells a model what to write.
NO_EM_DASH_RULE = (
    "Never use em dashes; use two sentences, a comma, a colon, or parentheses instead."
)


def with_no_em_dash_rule(text: str) -> str:
    """``text`` with the no-em-dash rule appended unless it already states it (idempotent)."""
    if "em dash" in text.lower() or "em-dash" in text.lower():
        return text
    return f"{text.rstrip()}\n\n{NO_EM_DASH_RULE}"


@dataclass(frozen=True)
class PromptSpec:
    """One declared prompt. ``tiers`` and ``on_render`` are set by ``bind_spec_class``; unbound, no tier is checked."""

    id: str
    solution: str
    metric: str
    tier: str
    cache_layer: str
    template: str
    inputs: Tuple[str, ...] = ()
    output_schema: Optional[Mapping[str, Any]] = None
    writes_text: bool = True

    tiers: ClassVar[Tuple[str, ...]] = ()
    on_render: ClassVar[Optional[Callable[[str], None]]] = None

    def __post_init__(self) -> None:
        if not self.id or not self.solution or not self.metric:
            raise ValueError(f"prompt spec {self.id!r} needs an id, a solution and a metric")
        if self.tiers and self.tier not in self.tiers and self.tier != CALLER_TIER:
            raise ValueError(f"prompt spec {self.id!r}: tier {self.tier!r} is not one of "
                             f"{self.tiers + (CALLER_TIER,)}")
        if self.cache_layer not in CACHE_LAYERS:
            raise ValueError(f"prompt spec {self.id!r}: cache_layer {self.cache_layer!r} is not "
                             f"one of {CACHE_LAYERS}")

    def render(self, **values: Any) -> str:
        """The prompt text, filled with ``values`` and carrying the no-em-dash rule.

        A spec with no ``inputs`` is returned verbatim (its text may hold literal braces); a spec with inputs is filled
        with ``str.format``. Values must match ``inputs`` exactly, so a typo or a forgotten slot fails here rather than
        reaching a model.
        """
        given, wanted = set(values), set(self.inputs)
        if given != wanted:
            raise ValueError(f"prompt {self.id!r} takes {sorted(wanted)}; got {sorted(given)}")
        hook = type(self).on_render
        if hook is not None:
            hook(self.id)
        text = self.template.format(**values) if self.inputs else self.template
        return with_no_em_dash_rule(text) if self.writes_text else text


def bind_spec_class(tiers: Tuple[str, ...], on_render: Optional[Callable[[str], None]] = None,
                    name: str = "PromptSpec") -> Type[PromptSpec]:
    """A ``PromptSpec`` subclass that checks ``tier`` against ``tiers`` and calls ``on_render(spec_id)`` on every render."""
    hook = staticmethod(on_render) if on_render is not None else None
    return type(name, (PromptSpec,), {"tiers": tuple(tiers), "on_render": hook})


class PromptRegistry:
    """The specs of one spec class, found by id. An id is registered once."""

    def __init__(self, spec_class: Type[PromptSpec] = PromptSpec) -> None:
        self.spec_class = spec_class
        self.specs: Dict[str, PromptSpec] = {}

    def register(self, spec: PromptSpec) -> PromptSpec:
        """Add ``spec`` and return it; registering the same id with a different spec raises."""
        existing = self.specs.get(spec.id)
        if existing is not None and existing != spec:
            raise ValueError(f"prompt id {spec.id!r} is already registered with a different spec")
        self.specs[spec.id] = spec
        return spec

    def declare(self, spec_id: str, *, solution: str, metric: str, tier: str, cache_layer: str,
                template: str, output_schema: Optional[Mapping[str, Any]] = None,
                writes_text: bool = True) -> PromptSpec:
        """Register a spec whose ``inputs`` are read from the template's own ``{slots}``.

        The usual way to declare a prompt that already exists as a ``str.format`` template: the slots cannot drift from
        the text, and ``render`` then refuses any call that fills different ones.
        """
        slots = []
        for _, field, _, _ in string.Formatter().parse(template):
            slot = (field or "").split(".")[0].split("[")[0]
            if slot and slot not in slots:
                slots.append(slot)
        return self.register(self.spec_class(
            id=spec_id, solution=solution, metric=metric, tier=tier, cache_layer=cache_layer,
            template=template, inputs=tuple(slots), output_schema=output_schema,
            writes_text=writes_text))

    def get(self, spec_id: str) -> PromptSpec:
        """The registered spec for ``spec_id``; ``KeyError`` names the id when it is unknown."""
        try:
            return self.specs[spec_id]
        except KeyError:
            raise KeyError(f"no prompt spec registered under {spec_id!r}") from None

    def render(self, spec_id: str, **values: Any) -> str:
        """Render the registered prompt ``spec_id``."""
        return self.get(spec_id).render(**values)
