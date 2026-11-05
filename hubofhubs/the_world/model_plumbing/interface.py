"""The interface of ModelPlumbing: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Any, Optional, runtime_checkable
from esoi import solution


@solution("model-plumbing", kind="event", entry="ask", example={"prompt": "Reply with the single word: ok", "tier": "cheap"})
@runtime_checkable
class ModelPlumbing(typing.Protocol):
    """Asks a model for the answer to a prompt at a tier, using the model the tier chooser measured best for that tier, through the vendor the
    hub assembled. Also enforces the goal record's budget on the calls it makes: ``budget`` is the record's mutable ``budget`` mapping, and a call spends one of its ``model_calls``."""

    def ask(self, prompt: str, tier: str = "", budget: Optional[Any] = None) -> str: ...
