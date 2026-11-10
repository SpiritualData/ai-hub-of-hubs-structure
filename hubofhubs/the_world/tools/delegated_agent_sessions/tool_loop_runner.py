"""The hub's own harness on a provider's native tool calling, as a ``DeepRunner``.

It is the hub's loop (``tool_call_loop``) with the model called through the vendor model caller's tool interface instead of a pure text completion: Anthropic
tool use with the Claude Code tool names and shapes, Gemini function calling with Google's coding-tool names, OpenAI's Responses API with ``shell`` and ``apply_patch``.
Everything around the loop is the text loop's runner (``SolutionLoopRunner``): the shared ceilings and the stop decision for every call the hub itself starts, steering,
saved sessions and resume, the solution hierarchy's worker (``as_solution_worker``), the session events. What differs is only ``engine``. The model is called with a
vendor key (``ANTHROPIC_API_KEY`` and its siblings, passed in the settings' environment mapping, never read from the process here); a Claude subscription login cannot
serve this loop because it exposes no tool-use interface to a caller, only the Claude Code CLI's own loop. An arm is this harness with a provider and a tier,
written ``native_tool_calling_loop_runner@provider=anthropic,tier=fast``. Only the Anthropic path is measured end to end; Gemini and OpenAI are written against their
documented interfaces.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional

from esoi import implementation

from hubofhubs.the_world.model_plumbing.vendor_model_caller.tool_calling import ModelTurn
from hubofhubs.the_world.tools.deep import DeepResult, ProgressEvent
from hubofhubs.the_world.tools.events import EVENT_STATUS
from hubofhubs.the_world.tools.delegated_agent_sessions import providers
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig, log
from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import CHECK_MESSAGE, outside_the_folder, worth_resuming
from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import LoopResult
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner, price
from hubofhubs.the_world.tools.delegated_agent_sessions.tool_call_loop import ToolLoopState, run_tool_loop
from hubofhubs.the_self.assembler import arm_needs as needs

DEFAULT_CALLS = 15
CACHE_WRITE_FACTOR, CACHE_READ_FACTOR = 1.25, 0.10     # Anthropic's prompt caching: a cache write costs 1.25 times the input price, a read 0.1 times


@implementation("delegated-agent-sessions", "native_tool_calling_loop_runner")
class NativeToolCallingLoopRunner(SolutionLoopRunner):
    """The hub's loop speaking the provider's native tool calls: the model's trained tool names, one transcript, the hub's frame, plan, ceilings and checks."""

    REQUIRES = (needs.ANTHROPIC_NETWORK, needs.ANTHROPIC_API, needs.ANTHROPIC_SDK, needs.WRITE_ROOT)
    PROVIDERS = ("anthropic", "gemini", "openai")
    state_class = ToolLoopState

    def __init__(self, *args: Any, vendor: Optional[Any] = None, calls: int = DEFAULT_CALLS, **kwargs: Any):
        kwargs.setdefault("provider", "anthropic")
        super().__init__(*args, **kwargs)
        self.vendor = vendor               # an injected vendor model caller with ``tool_turn`` (tests); else built from the settings' environment
        self.default_calls = int(calls)

    # --- the model ---------------------------------------------------------------------------------------------------------------

    def vendor_for(self, settings: GoalSettings) -> Any:
        """The vendor model caller for this arm's provider, with the key from the settings' environment mapping."""
        if self.vendor is not None:
            return self.vendor
        env = dict(settings.environment() or {})
        key = next((env[n] for n in providers.credential_names(self.provider) if env.get(n)), None)
        if self.provider == "anthropic":
            from hubofhubs.the_world.model_plumbing.vendor_model_caller.anthropic import AnthropicProvider
            return AnthropicProvider(api_key=key, env_name="ANTHROPIC_API_KEY")
        if self.provider == "gemini":
            from hubofhubs.the_world.model_plumbing.vendor_model_caller.gemini import GeminiProvider
            return GeminiProvider(api_key=key, env_name="GEMINI_API_KEY")
        from hubofhubs.the_world.model_plumbing.vendor_model_caller.openai import OpenAIProvider
        return OpenAIProvider(api_key=env.get("OPENAI_API_KEY"), base_url=env.get("OPENAI_BASE_URL"), env_name="OPENAI_API_KEY")

    def turn_function(self, run_model: str, settings: GoalSettings, usage: Dict[str, float]) -> Callable[[List[Dict[str, Any]], str, List[Any]], ModelTurn]:
        vendor = self.vendor_for(settings)
        per_million = price(self.provider, run_model, 1_000_000, 0) / 1_000_000

        def turn(transcript: List[Dict[str, Any]], system: str, tools: List[Any]) -> ModelTurn:
            got = vendor.tool_turn(transcript, model=run_model, system=system, tools=tools)
            plain = max(got.tokens_in - got.cache_read - got.cache_write, 0)
            usage["plain"] += plain
            usage["read"] += got.cache_read
            usage["write"] += got.cache_write
            usage["output"] += got.tokens_out
            usage["tokens"] += plain + got.tokens_out
            input_cost = per_million * (plain + CACHE_WRITE_FACTOR * got.cache_write + CACHE_READ_FACTOR * got.cache_read)
            usage["cost"] += input_cost + price(self.provider, run_model, 0, got.tokens_out)
            return got
        return turn

    # --- the loop ------------------------------------------------------------------------------------------------------------------

    def engine(self, goal: str, *, folder: str, run_model: str, settings: GoalSettings, usage: Dict[str, float], context_text: str, max_calls: int, cancel: Any,
               emit: Any, tell: Any, command_timeout: float, environment: Any, wrap: Any, state: Any, save: Any, inbox: Any, telling: Any, stop_now: Any,
               permit: Any) -> LoopResult:
        actions: List[Any] = []
        result = run_tool_loop(goal, working_dir=folder, turn=self.turn_function(run_model, settings, usage), provider=self.provider, context=context_text,
                               max_calls=max_calls, cancel=cancel, emit=tell if emit is not None else None, command_timeout=max(command_timeout, 120.0),
                               environment=environment, wrap=wrap, review=bool(self.review), state=state, save=save, inbox=inbox, telling=telling, stop_now=stop_now,
                               permit=permit, actions=actions, worth=lambda root, found: worth_resuming(root, found), check_message=CHECK_MESSAGE)
        result.outside = outside_the_folder(folder, actions, temporary=(settings.environment() or {}).get("TMPDIR", "/tmp"))   # type: ignore[attr-defined]
        if result.outside and emit is not None:   # type: ignore[attr-defined]
            try:
                emit(ProgressEvent(type=EVENT_STATUS, text="The session wrote or ran something outside the working folder.",
                                   data=dict(phase="outside_folder", items=result.outside)))   # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001 -- a sink that fails never stops the run
                pass
        return result

    def deep_result(self, result: LoopResult, usage: Mapping[str, float], why: str, model: str) -> DeepResult:
        deep = super().deep_result(result, usage, why, model)
        deep.outside_folder = list(getattr(result, "outside", []) or [])      # type: ignore[attr-defined]
        return deep

    def run_goal(self, *, max_turns: Optional[int] = None, **kwargs: Any) -> DeepResult:
        """The text loop's ``run_goal`` with this arm's own default number of model calls."""
        return super().run_goal(max_turns=max_turns or self.default_calls, **kwargs)
