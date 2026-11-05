"""Which provider serves a model id, and the newest live model of a family. A bare family name (``sonnet``, ``claude-opus``,
``gemini-flash-lite``, ``gpt-mini``) names no release; anything containing a digit is a pinned release and passes through."""
import re
from typing import Collection, Dict, Iterable, List, Mapping, Optional, Tuple

VENDOR_PREFIXES = ("claude", "gemini", "gpt")
NOISE_TOKENS = {"preview", "latest", "exp", "experimental"}      # suffixes marking a build of the same family

# The first matching prefix of a lower-case model id names its provider. Data, not branches: a new vendor is one entry.
MODEL_PREFIX_PROVIDERS: Mapping[str, str] = {
    "claude": "anthropic", "gemini": "gemini", "models/": "gemini", "gpt": "openai", "deepseek": "deepseek",
}


def provider_name_for_model(model: str, available: Optional[Collection[str]] = None,
                            prefixes: Mapping[str, str] = MODEL_PREFIX_PROVIDERS) -> Optional[str]:
    """The provider the first matching prefix names, or None; with ``available``, None also when that provider is not among them."""
    low = (model or "").lower()
    for prefix, name in prefixes.items():
        if low.startswith(prefix):
            return name if available is None or name in available else None
    return None


def split_tokens(model_id: str) -> Tuple[List[str], Tuple[int, ...]]:
    """(family words, version numbers) of an id. Single letters (the "o" in gpt-4o) are not family words."""
    low = (model_id or "").strip().lower()
    if low.startswith("models/"):
        low = low[len("models/"):]
    parts = re.findall(r"\d+|[a-z]+", low)
    return [p for p in parts if p.isalpha() and len(p) > 1 and p not in NOISE_TOKENS], tuple(int(p) for p in parts if p.isdigit())


def is_family_name(name: Optional[str]) -> bool:
    low = (name or "").strip().lower()
    return bool(low) and not re.search(r"\d", low)


def newest_in_family(name: Optional[str], live_models: Iterable[str]) -> Optional[str]:
    """The newest live id whose family equals ``name``, or None (not a family name, or no match)."""
    if not is_family_name(name):
        return None
    want, _ = split_tokens(name)
    best: Optional[Tuple[Tuple[int, ...], str]] = None
    for mid in live_models:
        words, nums = split_tokens(mid)
        if not want or not words:
            continue
        shapes = [words] + ([words[1:]] if words[0] in VENDOR_PREFIXES else [])    # "sonnet" also names claude-sonnet-*
        if want in shapes and (best is None or nums > best[0]):
            best = (nums, mid)
    return best[1] if best else None


def resolve_model_name(model: str, live_models: Iterable[str]) -> str:
    """``model`` itself unless it is a family name with a live match."""
    return newest_in_family(model, live_models) or model
