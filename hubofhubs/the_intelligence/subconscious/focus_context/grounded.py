"""The session harness that starts every run from the person's own context. It wraps any harness: before the run it gathers the notes of the configured sources
(``arms.ConfiguredFocusContext``), adds the brief after the goal (the run still shows the goal as typed) and, once the run has started, says one short line on screen
as an ordinary step ("Using 4 saved notes about garden"). Nothing found, nothing added, nothing said. A source that fails is never a failed run."""
from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Mapping, Optional

from hubofhubs.the_consciousness.ai_session_experience.session_events import RunStarted, SessionEvent, Step
from hubofhubs.the_intelligence.subconscious.focus_context.settings import ContextSettings
from hubofhubs.the_intelligence.subconscious.focus_context.sources import Provider, load_notes

STEP_ID = "focus-context"


class Grounded:
    """``Harness`` over another harness (``.harness``): the goal plus what is already known about the focus."""

    def __init__(self, harness: Any, settings: ContextSettings, provider: Optional[Provider] = None, environ: Optional[Mapping[str, str]] = None, arm: Any = None):
        self.harness, self.settings, self.provider, self.variables = harness, settings, provider, environ
        self.arm = arm          # the gathering arm; None is the one whose fast-tier judge decides relevance
        self.name, self.capabilities = harness.name, harness.capabilities
        self.last = None            # the FocusContext of the latest run, for a caller that wants to show or record it
        self.problems: list = []

    def __getattr__(self, name: str) -> Any:
        if name in ("harness", "settings", "provider", "variables", "arm"):
            raise AttributeError(name)
        return getattr(self.harness, name)

    def gather(self, goal: str):
        from hubofhubs.the_intelligence.subconscious.focus_context.arms import LlmJudgedFocusContext
        notes, self.problems = load_notes(self.settings, self.provider, self.variables)
        arm = self.arm if self.arm is not None else LlmJudgedFocusContext()
        self.last = arm.gather(goal, notes, focus=self.settings.focus, max_notes=self.settings.max_notes, budget_tokens=self.settings.budget_tokens, scope=self.settings.scope)
        if getattr(arm, "failure", ""):
            self.problems = list(self.problems) + [f"the relevance judge failed ({arm.failure}); no saved notes were added"]
        return self.last

    def start(self, goal: str, sink: Callable[[SessionEvent], None], resume_session_id: str = ""):
        try:
            found = self.gather(goal)
        except Exception:  # noqa: BLE001 -- context only enriches: a failure here is no context, never a failed run
            found = None
        if found is None or not found.brief:
            return self.harness.start(goal, sink, resume_session_id)
        said = {"done": False}

        def shown(event: SessionEvent) -> None:
            sink(replace(event, goal=goal) if isinstance(event, RunStarted) else event)
            if isinstance(event, RunStarted) and not said["done"]:
                said["done"] = True
                sink(Step(step_id=STEP_ID, kind="read", label=found.line, state="done"))
        return self.harness.start(goal + "\n\n" + found.brief, shown, resume_session_id)

    def control(self, control: Any) -> bool:
        return self.harness.control(control)


def grounded_builder(build: Callable[[str], Any], settings: Optional[ContextSettings], provider: Optional[Provider] = None,
                     environ: Optional[Mapping[str, str]] = None) -> Callable[[str], Any]:
    """``build`` with every harness it makes wrapped in ``Grounded``; ``build`` itself when there are no settings or nothing to gather from (a consumer's provider counts)."""
    if settings is None or not (settings.usable() or provider is not None):
        return build
    return lambda name: Grounded(build(name), settings, provider, environ)
