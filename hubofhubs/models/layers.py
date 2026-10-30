"""Prompt-layer helpers shared by the providers that render a cacheable prefix. A layer block is ``{"text": str, "cache": bool}``."""
from typing import Any, Dict, List

LayerBlock = Dict[str, Any]
MAX_CACHE_BREAKPOINTS = 4      # Anthropic allows at most four cache_control markers per request
LAYER_SEPARATOR = "\n\n"       # a blank line, so a leading subset of layers joins to a true byte-prefix of the whole


def join_layers(*parts: str) -> str:
    """Join non-empty layer strings in order; empty parts are dropped so a missing layer never doubles the separator."""
    return LAYER_SEPARATOR.join(p for p in parts if p)


def blocks_to_prompt(blocks: List[LayerBlock]) -> str:
    """Flatten ordered layer blocks into one plain string (the shape for a provider with no cache support)."""
    return join_layers(*[str(b.get("text") or "") for b in (blocks or [])])


def cache_control_indices(blocks: List[LayerBlock], *, max_breakpoints: int = MAX_CACHE_BREAKPOINTS) -> List[int]:
    """Indices of the ``cache=True`` blocks that carry a breakpoint; past the cap the LAST ones are kept, since a breakpoint
    caches everything up to its block."""
    candidates = [i for i, b in enumerate(blocks or []) if b.get("cache")]
    return candidates[-max_breakpoints:] if len(candidates) > max_breakpoints else candidates
