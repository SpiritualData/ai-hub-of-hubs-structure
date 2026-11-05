"""The interface of ModelCalling: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import runtime_checkable
from esoi import solution
from hubofhubs.the_world.model_plumbing.model import ModelProvider


@solution("vendor-model-caller", kind="event", entry="answer", example={"messages": [{"role": "user", "content": "Reply with the single word: ok"}], "model": "claude-haiku"})
@runtime_checkable
class ModelCalling(ModelProvider, typing.Protocol):
    """Plans, answers and lists models for one vendor (or, as the router, for several). External system: the hub ships arms over
    the vendor SDKs (extras ``anthropic``, ``gemini``, ``openai``) and a router; the consumer passes keys and settings as arguments."""
