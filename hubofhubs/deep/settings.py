"""What a consumer hands the deep runners: one frozen settings value and the two collaborators the runners call.

The runners read no environment and no process-wide state. Everything that a deployment tunes (the wall-clock cap, the liveness
review interval, the launch flags, where the worker keeps its sessions, the line the worker prints when it escalates) is a field of
``GoalSettings``; the three things that are behaviour rather than numbers are objects the consumer passes in:

* ``usage_limits``: how a subscription usage limit is told, remembered and recalled (``UsageLimits``);
* ``prompt_budget``: how the composed worker prompt is fitted to a token budget (``PromptBudget``);
* ``standing_instructions``: a callable returning the always-on instruction text a run is given (empty by default).

A consumer that wants a value re-read on every use (an environment that a test or a deployment changes while the process runs)
passes a zero-argument callable returning ``GoalSettings`` instead of a value; ``resolve_goal_settings`` accepts both.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

from .launch import DeepLaunchSettings

DEFAULT_DEEP_REVIEW_INTERVAL_SECONDS = 300.0

CHARS_PER_TOKEN = 3.5


class UsageLimits:
    """The subscription usage-limit state of the worker, as the runners need it; this base handles none (a refusal is an
    ordinary failure). A consumer passes any object with these four methods (a module of functions will do). A limit is any
    object with a ``message``."""

    def active_limit(self) -> Optional[Any]:
        """The limit the worker is known to be at right now, or None."""
        return None

    def limit_from_session_file(self, path: Any) -> Optional[Any]:
        """The limit the run's own session record states, or None."""
        return None

    def detect_usage_limit(self, text: str) -> Optional[Any]:
        """The limit a worker's error text states, or None. Called only on an error path."""
        return None

    def record(self, limit: Any) -> Any:
        """Remember ``limit`` (lane-wide, however the consumer keeps it) and return the stored one."""
        return limit


@dataclass
class NoCuts:
    """The fit of a prompt that nothing was cut from."""

    cuts: List[Any] = field(default_factory=list)
    tokens_before: int = 0
    tokens_after: int = 0


class PromptBudget:
    """Fitting the worker prompt to a token budget; this base never cuts and knows no window. A consumer passes any object with
    these members (a module of functions will do)."""

    MIN_DEEP_PROMPT_TOKEN_BUDGET = 8_000

    def resolve_deep_prompt_budget(self, configured: Optional[int] = None, *, model: Optional[str] = None) -> int:
        """The token budget for one prompt: ``configured`` or the consumer's default, capped at what ``model`` can hold."""
        return int(configured) if configured else 10 ** 9

    def estimate_tokens(self, text: Optional[str]) -> int:
        """About how many tokens ``text`` is."""
        return int(len(text or "") / CHARS_PER_TOKEN)

    def fit_deep_prompt(self, preamble: str, task_parts: List[str], *, budget_tokens: int) -> Tuple[str, List[str], Any]:
        """``(preamble, task_parts, fit)`` cut to ``budget_tokens``; ``fit`` has ``cuts``, ``tokens_before`` and ``tokens_after``."""
        return preamble, list(task_parts), NoCuts()

    def describe_cuts(self, cuts: List[Any]) -> str:
        """The cuts in plain words, for a progress line."""
        return ""

    def max_prompt_tokens_for(self, model: Optional[str]) -> int:
        """The most prompt tokens ``model`` can take beside the worker's own overhead."""
        return 10 ** 9

    def is_prompt_too_long(self, text: Optional[str]) -> bool:
        """Whether ``text`` (a worker's error) says the model refused the prompt as too long."""
        return False


def no_instructions() -> str:
    return ""


def keep_requester(env: Dict[str, str], user_id: Optional[str]) -> Dict[str, str]:
    """The default requester hook: the child's environment is left as it is."""
    return env


def empty_environment() -> Mapping[str, str]:
    return {}


@dataclass(frozen=True)
class GoalSettings:
    """Every tunable the goal runners read. The defaults are a runner that reads nothing from its host.

    deep_timeout_seconds          the OPTIONAL hard wall-clock cap on a run; None means no cap (the liveness review decides).
    deep_review_interval_seconds  seconds between liveness reviews; None turns them off.
    deep_launch                   the launch flags of the worker (``launch.DeepLaunchSettings``).
    claude_config_dir             where the worker keeps its sessions when not the default ``~/.claude``; None for the default.
    escalation_marker             the line prefix a worker prints to report the human decision it raised (``<marker> <id>``);
                                  empty means no worker escalates this way and no marker is read.
    run_id_env                    the environment name that carries a run's id into the worker's shell; empty sets none.
    standing_instructions         a callable returning the instruction text every run is given, "" for none.
    apply_requester               a hook that sets or clears the requester in a child environment (in place, returned).
    environment                   a callable returning the environment a child process starts from.
    usage_limits                  the usage-limit collaborator (``UsageLimits``).
    prompt_budget                 the prompt-budget collaborator (``PromptBudget``).
    """

    deep_timeout_seconds: Optional[float] = None
    deep_review_interval_seconds: Optional[float] = DEFAULT_DEEP_REVIEW_INTERVAL_SECONDS
    deep_launch: DeepLaunchSettings = DeepLaunchSettings()
    claude_config_dir: Optional[str] = None
    escalation_marker: str = ""
    run_id_env: str = ""
    standing_instructions: Callable[[], str] = no_instructions
    apply_requester: Callable[[Dict[str, str], Optional[str]], Dict[str, str]] = keep_requester
    environment: Callable[[], Mapping[str, str]] = empty_environment
    usage_limits: UsageLimits = field(default_factory=UsageLimits)
    prompt_budget: PromptBudget = field(default_factory=PromptBudget)


GoalSettingsSource = Union[GoalSettings, Callable[[], GoalSettings]]


def resolve_goal_settings(source: Optional[GoalSettingsSource]) -> GoalSettings:
    """The settings in force right now: a value as it is, a callable called, None the defaults."""
    if source is None:
        return GoalSettings()
    return source if isinstance(source, GoalSettings) else source()
