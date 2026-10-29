"""ai_hub_of_hubs: the registry of AI-intelligence hubs, and the scorer that reads it together with a consumer's code.

Import it like the esoi library: with a checkout of this repository on ``PYTHONPATH`` (``../ai-hub-of-hubs-structure``), or
``pip install -e`` it, or install it from its git URL. It reads only files, makes no model call and no network request.

    from ai_hub_of_hubs import Binding, evaluate
"""
from .binding import Binding
from .measure import evaluate, check, metrics

__all__ = ["Binding", "evaluate", "check", "metrics"]
