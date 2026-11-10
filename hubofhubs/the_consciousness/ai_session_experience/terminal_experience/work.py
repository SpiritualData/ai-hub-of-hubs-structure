"""``ahohs work``: a goal run on a real harness in the live terminal, and the prompt that goes on from it.

``WorkTerminal`` is the whole interactive command and knows no harness: it is handed ``build(name)`` (a function from a harness name to a ``Harness`` of the session
contract) and the names it may offer. Given a goal it runs it in the live terminal (``LiveSession.attend``); given none it asks for one. When a run ends, a typed line is the
follow-up: it continues the same session. ``/harness NAME`` switches the harness between runs (the contract is harness-neutral, but a session belongs to the harness that
made it, so the next run starts a new session on the new harness with a short recap of the earlier run behind it). A consumer supplies only a binding: its ``build``, its extra
slash commands (``commands``), extra header segments (``segments``) and panels (``panels``), a front door for lines that are not goals (``front_door``, reached with
``/ask``), and the ``records`` the structure view reads. ``harness_builder`` is the hub's own ``build``: the harnesses of Delegated Agent Sessions by plain name, with the
ceilings, the tier and the folder, and the hub's own choice of default. Standard library and the hub only; the environment is handed in, never read.
"""
from __future__ import annotations

import inspect
import io
import time
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, TextIO, Tuple

from hubofhubs.the_consciousness.ai_session_experience.session_events import Finished, Harness
from hubofhubs.the_consciousness.ai_session_experience.session_harnesses import Briefed, Framed, Limited, LoopHarness, StreamHarness
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionReport, SessionView

#: the names a person types, and the harness of Delegated Agent Sessions each one is
HARNESSES = {"native": "native_tool_loop_runner", "stream": "stream_json_goal_runner", "loop": "solution_loop_runner"}
DEFAULT_PROVIDERS = ("anthropic",)
PERMISSIONS = ("acceptEdits", "skip")
#: which of the Claude CLI's setting sources a session loads (``--setting-sources``): the folder's own, never the person's user-level settings and their hooks, unless asked (``user,project``)
DEFAULT_SETTING_SOURCES = "project"
KEPT_ENVIRONMENT = ("HOME", "PATH", "USER", "LOGNAME", "LANG", "LC_ALL", "TERM", "TMPDIR", "SHELL", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "XDG_RUNTIME_DIR")
HELPER_NOTE = "When you hand work to a helper, begin its description with [{solution}] (the solution it serves), for example: [{solution}] check the plan."
INTRO = "Type a goal and press Enter; it runs in this folder. /help lists commands."
COMMAND_HELP = ("/harness [name]  show or switch the harness (a new session starts, with a recap of the last run)",
                "/new             start a new session on the same harness",
                "/session         show the session id",
                "/help            list commands and keys",
                "/quit            leave (Ctrl-D too)")
WIDTH = 17


def child_environment(environ: Mapping[str, str]) -> Dict[str, str]:
    """The environment a worker starts from: the login, path, language and temporary-folder names only, so no API key in the person's shell silently replaces the subscription login."""
    return {name: str(environ[name]) for name in KEPT_ENVIRONMENT if name in environ}


def seconds_of(text: Any) -> Optional[float]:
    """A duration as seconds: ``90s``, ``30m``, ``2h`` or a bare number of minutes; ``unlimited`` is None (the explicit way to run with no ceiling)."""
    word = str(text).strip().lower()
    if word == "unlimited":
        return None
    unit = {"s": 1.0, "m": 60.0, "h": 3600.0}.get(word[-1:], 0.0)
    try:
        value = float(word[:-1] if unit else word) * (unit or 60.0)
    except ValueError:
        raise ValueError(f"a time ceiling is like 90s, 30m, 2h or unlimited, not {text!r}") from None
    if value <= 0:
        raise ValueError("a time ceiling must be above zero (or unlimited)")
    return value


def dollars_of(text: Any) -> Optional[float]:
    """A spend ceiling in dollars (``5`` or ``$5``); ``unlimited`` is None."""
    word = str(text).strip().lower().lstrip("$")
    if word == "unlimited":
        return None
    try:
        value = float(word)
    except ValueError:
        raise ValueError(f"a spend ceiling is a number of dollars or unlimited, not {text!r}") from None
    if value <= 0:
        raise ValueError("a spend ceiling must be above zero (or unlimited)")
    return value


def default_harness(declared: Sequence[str] = DEFAULT_PROVIDERS) -> Tuple[str, str]:
    """``(name, why)``: the hub's own pick for ordinary work (Delegated Agent Sessions' measured choice among the arms the person can run), when that arm can take a message
    while it works; otherwise the steerable ``stream`` harness, with the reason said."""
    from hubofhubs.the_world.tools.delegated_agent_sessions import arm_choice
    chosen = arm_choice.choose_agent_arm(declared)
    if chosen is not None:
        for name, implementation in HARNESSES.items():
            if chosen.harness == implementation:
                return name, f"the hub's pick: {chosen.arm} ({chosen.basis})"
        return "stream", f"the hub's pick, {chosen.harness}, cannot take a message while it works, so the steerable stream harness is used"
    return "stream", "the hub has no measured pick for the arms you can run; the steerable stream harness is used"


def harness_builder(*, folder: str, tier: str = "balanced", ceiling_usd: Any = None, ceiling_seconds: Any = None, permission: str = "acceptEdits",
                    environ: Optional[Mapping[str, str]] = None, solution: str = "", milestone: str = "", provider: str = "anthropic",
                    stop_inputs: Optional[Callable[[], Mapping[str, Any]]] = None, setting_sources: str = DEFAULT_SETTING_SOURCES) -> Callable[[str], Harness]:
    """``build(name)`` for the hub's own harnesses. ``ceiling_usd`` and ``ceiling_seconds`` are numbers, ``"unlimited"`` or None for the runners' defaults. ``permission`` is
    ``acceptEdits`` (the run may read and change files; a command is refused and listed as blocked) or ``skip`` (no permission checks, as the hub's own sessions run).
    ``solution`` and ``milestone`` frame the run (its header, the structure view and the closing report name them). ``stop_inputs`` gives, at each build, the stated stop limits and
    the policy of the Representative in force (``{"stated": ..., "policy": ...}``) that the runners that iterate on their own hand to Goal Completion's stop decision."""
    from hubofhubs.the_world.tools.delegated_agent_sessions import providers
    from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
    from hubofhubs.the_world.tools.delegated_agent_sessions.run_ceilings import (
        DEFAULT_CEILING_SECONDS, DEFAULT_CEILING_USD, UNLIMITED, ceiling_of, current_session_file, estimate_spend)
    from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings
    if permission not in PERMISSIONS:
        raise ValueError(f"permission is one of {', '.join(PERMISSIONS)}")
    if providers.model_for(provider, tier) is None:
        raise ValueError(f"no model is chosen for the tier {tier!r}; the tiers are fast, balanced, quality and best")
    usd = DEFAULT_CEILING_USD if ceiling_usd is None else (UNLIMITED if ceiling_usd == UNLIMITED else ceiling_usd)
    seconds = DEFAULT_CEILING_SECONDS if ceiling_seconds is None else (UNLIMITED if ceiling_seconds == UNLIMITED else ceiling_seconds)
    shown_usd, shown_seconds = ceiling_of(usd, "ceiling_usd"), ceiling_of(seconds, "ceiling_seconds")
    child = child_environment(environ or {})
    from hubofhubs.the_world.tools.delegated_agent_sessions.launch import DeepLaunchSettings
    settings = GoalSettings(environment=lambda: dict(child), deep_launch=DeepLaunchSettings(setting_sources=setting_sources))

    def build(name: str) -> Harness:
        if name not in HARNESSES:
            raise ValueError(f"no harness named {name!r}; choose one of {', '.join(HARNESSES)}")
        edits = ["Read", "Glob", "Grep", "Edit", "Write", "MultiEdit", "NotebookEdit", "WebSearch", "WebFetch", "TodoWrite", "Task", "Agent"]
        if name == "loop":
            from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop_runner import SolutionLoopRunner
            runner = SolutionLoopRunner(root=folder, provider=provider, tier=tier, settings=settings, ceiling_usd=usd, ceiling_seconds=seconds,
                                      stop_inputs=stop_inputs() if stop_inputs else None)
            inner: Any = LoopHarness(runner, working_dir=folder)
        elif name == "native":
            from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import NativeToolLoopRunner
            runner = NativeToolLoopRunner(SubprocessConfig(working_dir=folder), provider=provider, tier=tier, settings=settings, ceiling_usd=usd, ceiling_seconds=seconds,
                                          stop_inputs=stop_inputs() if stop_inputs else None, permission="skip" if permission == "skip" else "acceptEdits")
            inner = StreamHarness(runner, root=folder)
        else:
            from hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner import StreamJsonGoalRunner
            config = SubprocessConfig(working_dir=folder, skip_permissions=permission == "skip", allowed_tools=None if permission == "skip" else edits)
            runner = StreamJsonGoalRunner(config, provider=provider, tier=tier, settings=settings, ceiling_usd=usd, ceiling_seconds=seconds)
            inner = StreamHarness(runner, root=folder)
        inner.name = name
        config_dir = settings.claude_config_dir
        # the runners of the Claude CLI forward every raw stream line as a progress event, so no file is tailed for the steps
        harness: Any = Limited(inner, ceiling_usd=shown_usd, ceiling_seconds=shown_seconds,
                               spend_now=None if name == "loop" else (lambda since: estimate_spend(current_session_file(folder, since, config_dir))))
        if solution:
            harness = Framed(harness, solution=solution, milestone=milestone)
            harness = Briefed(harness, HELPER_NOTE.format(solution=solution))
        return harness
    return build


def terminal_arm(named: str = "", environ: Optional[Mapping[str, str]] = None) -> Tuple[Any, str, str]:
    """``(arm, its name, why)``: the Terminal Experience arm that draws the session. A name the person gave is kept; otherwise the selected arm, and when its library or
    program is missing the best-measured arm that can run stands in (``availability``), with the reason."""
    from esoi import AssemblyConfig
    from hubofhubs.the_self.assembler.availability import stand_ins
    from hubofhubs.the_self.assembler.resolution import HUB
    env = dict(environ or {})
    chosen, found = stand_ins(HUB, env, {"terminal-session": named} if named else None)
    name = chosen.get("terminal-session") or HUB.pick("terminal-session", None, AssemblyConfig(selections={}, consumer_environ=env)).name.split("@")[0]
    why = "chosen by you" if named else "the hub's selected terminal"
    for row in found:
        if row.solution == "terminal-session":
            why = f"{row.arm} stands in for {row.selected} ({row.reason})"
    return HUB.load("terminal-session", name)(), name, why


def recap_of(report: SessionReport) -> str:
    """A short account of the run that just ended, for the first goal on another harness (which cannot resume this harness's session)."""
    done = report.final
    if done is None:
        return ""
    files = report.view.changed()
    return ("Earlier in this conversation, on another harness: the goal was " + repr(report.view.goal) + f"; it ended {done.outcome}."
            + (f" Report: {done.report.strip()[:600]}" if done.report.strip() else "") + (f" Files changed: {', '.join(files[:20])}." if files else ""))


class WorkTerminal:
    """The interactive command. ``build(name)`` gives a harness; ``names`` are the harnesses a person may switch among; ``lines`` (an iterator of typed lines) replaces the
    terminal's own line input for a script or a pipe; ``keys`` is the key source of a live run (``TtyKeys`` on a terminal)."""

    def __init__(self, build: Callable[[str], Harness], out: TextIO, *, names: Sequence[str] = tuple(HARNESSES), harness: str = "", keys: Any = None,
                 lines: Optional[Iterable[str]] = None, records: Any = None, commands: Optional[Mapping[str, Callable[[str], Optional[str]]]] = None,
                 segments: Sequence[Callable[[SessionView], str]] = (), panels: Sequence[Callable[[SessionView], List[str]]] = (),
                 front_door: Optional[Callable[[str], Any]] = None, command: str = "ahohs work", live: Optional[bool] = None, width: int = 0, tick: float = 0.02,
                 clock: Callable[[], float] = time.monotonic, prompt: str = "> ", why: str = "", once: bool = False,
                 represent: Optional[Callable[[str], Mapping[str, Any]]] = None, people: Sequence[str] = (), person: str = "", arm: Any = None,
                 reader: Optional[Callable[[str], Optional[str]]] = None, structure_watch: Optional[Callable[..., List[str]]] = None):
        self.build, self.out, self.names, self.keys = build, out, tuple(names), keys
        self.lines: Optional[Iterator[str]] = iter(lines) if lines is not None else None
        self.records, self.segments, self.panels, self.front_door = records, segments, panels, front_door
        self.extra = dict(commands or {})
        self.command, self.live, self.width, self.tick, self.clock, self.prompt = command, live, width, tick, clock, prompt
        self.name = harness or (self.names[0] if self.names else "")
        self.why = why
        self.once = once      # run the goal given and leave (a pipe or a script that gave a goal and no follow-ups)
        self.represent, self.people, self.person = represent, tuple(people), person       # the Representatives entry (the hub's front door), the people a binding lists, who is acted for now
        self.arm = arm if arm is not None else LiveSession()        # the Terminal Experience arm that draws a run (``attend``); the standard-library one by default
        self.reader = reader                                         # reads one typed line at the prompt (an arm with its own input line gives it); None: ``input()``
        self.structure_watch = structure_watch                      # ``hook(files, summary)`` -> lines: the structure watch at the end of a run (None: off)
        self.harnesses: Dict[str, Harness] = {}
        self.session = ""
        self.recap = ""
        self.last: Optional[SessionReport] = None
        self.reports: List[SessionReport] = []

    # --- lines ---------------------------------------------------------------------------------------------------------------------

    def say(self, text: str) -> None:
        self.out.write(text + "\n")
        self.out.flush()

    def read(self, prompt: str) -> Optional[str]:
        """The next typed line, or None at the end of input."""
        if self.lines is not None:
            self.out.write(prompt)
            self.out.flush()
            try:
                text = next(self.lines)
            except StopIteration:
                self.out.write("\n")
                return None
            self.out.write(text.rstrip("\n") + "\n") if not getattr(self.out, "isatty", lambda: False)() else None
            return text.rstrip("\n")
        if self.reader is not None:
            return self.reader(prompt)
        try:
            import readline  # noqa: F401  (line editing and history for input(), where the platform has it)
        except ImportError:
            pass
        try:
            return input(prompt)
        except (EOFError, KeyboardInterrupt):
            self.out.write("\n")
            return None

    def authority(self) -> Tuple[Optional[Mapping[str, Any]], Optional[Mapping[str, Any]]]:
        """``(representative, stop limits)`` of the person acted for, through the hub's own Representatives; ``(None, None)`` when no person is named (nothing extra is shown and the
        hub's default applies)."""
        if self.represent is None or not self.person:
            return None, None
        from hubofhubs.the_consciousness.representatives.stop_limits import resolve_stop_limits
        found = self.represent(self.person)
        return found, resolve_stop_limits(found)

    def stop_inputs(self) -> Dict[str, Any]:
        limits = self.authority()[1] or {}
        return {"stated": limits.get("stated") or {}, "policy": limits.get("policy") or {}}

    def as_person(self, name: str) -> None:
        if not name:
            if not self.people:
                self.say("no representatives are listed; the hub's default applies")
            for each in self.people:
                self.say(("* " if each == self.person else "  ") + each)
            return
        if self.people and name not in self.people:
            self.say(f"no representative named {name!r}; choose one of {', '.join(self.people)}")
            return
        self.person = name
        self.harnesses.clear()          # the stop limits of the new representative reach the next run's harness; the session goes on
        self.say(f"now acting for {name}; the next run uses their authority")

    # --- commands --------------------------------------------------------------------------------------------------------------------

    def harness(self) -> Harness:
        if self.name not in self.harnesses:
            self.harnesses[self.name] = self.build(self.name)
        return self.harnesses[self.name]

    def switch(self, name: str) -> None:
        if name == self.name:
            self.say(f"already on {name}")
            return
        if name not in self.names:
            self.say(f"no harness named {name!r}; choose one of {', '.join(self.names)}")
            return
        try:
            self.harnesses.setdefault(name, self.build(name))
        except Exception as error:  # noqa: BLE001 -- a harness that cannot be built is said, and the session stays where it was
            self.say(f"cannot use {name}: {error}")
            return
        if self.last is not None:
            self.recap = recap_of(self.last)
        self.name, self.session = name, ""
        self.say(f"harness is now {name}: the next goal starts a new session" + (", with a recap of the last run" if self.recap else ""))

    def command_of(self, text: str) -> bool:
        """Handle a slash command; True when it was one (and so is not a goal)."""
        word, _, rest = text[1:].partition(" ")
        word, rest = word.lower(), rest.strip()
        if word in ("quit", "exit", "q"):
            raise EOFError
        if word == "harness":
            if rest:
                self.switch(rest)
            else:
                self.say(f"harness: {self.name}" + (f" ({self.why})" if self.why else "") + f"; available: {', '.join(self.names)}")
        elif word == "as":
            self.as_person(rest)
        elif word == "who":
            from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import hub_lines
            found, limits = self.authority()
            for row in hub_lines.authority_lines(found, limits) or ["No representative is named: the hub's default applies."]:
                self.say(row)
        elif word == "new":
            self.session, self.recap = "", ""
            self.say("a new session starts with the next goal")
        elif word == "session":
            self.say(f"session: {self.session or '(none yet)'} on {self.name}")
        elif word in ("help", "keys"):
            for row in COMMAND_HELP + (("/as [name]       list or switch who the AI acts for", "/who             show the authority in force") if self.represent or self.people else ()) + tuple(f"/{name:<16}(this build's own command)" for name in self.extra) + (("/ask <text>      send a line to the front door instead of the run",) if self.front_door else ()):
                self.say(row)
            self.say("While a run works: Esc stops it, type + Enter steers it, Tab shows the structure, ? lists the keys.")
        elif word in self.extra:
            try:
                said = self.extra[word](rest)
            except Exception as error:  # noqa: BLE001 -- a consumer's command that raises is shown, never fatal
                said = f"/{word} failed: {type(error).__name__}: {error}"
            if said:
                self.say(str(said))
        elif word == "ask" and self.front_door is not None:
            answer = self.front_door(rest)
            self.say(str(getattr(answer, "answer", answer) or "").strip())
        else:
            self.say(f"unknown command /{word}; /help lists them")
        return True

    # --- the loop --------------------------------------------------------------------------------------------------------------------

    def run(self, goal: str = "", resume: str = "") -> int:
        self.session = resume
        first = True
        while True:
            if not goal:
                if first:
                    self.say(INTRO)
                first = False
                text = self.read(self.prompt)
                if text is None:
                    return 0
                goal = text.strip()
                if not goal:
                    continue
            first = False
            try:
                if goal.startswith("/"):
                    self.command_of(goal)
                    goal = ""
                    continue
            except EOFError:
                return 0
            self.work(goal)
            goal = ""
            if self.once:
                return 0 if self.last is None or self.last.final is None or self.last.final.outcome != "failed" else 1
            if self.last is not None and self.last.final is not None and self.last.final.outcome == "failed" and self.lines is None and not self.interactive():
                return 1

    def interactive(self) -> bool:
        return bool(getattr(self.out, "isatty", lambda: False)())

    def work(self, goal: str) -> None:
        harness = self.harness()
        base = harness
        while hasattr(base, "harness") and not isinstance(base, Briefed):
            base = base.harness
        if isinstance(base, Briefed):
            base.note = (base.note.split("\n\nEarlier in this conversation")[0] + ("\n\n" + self.recap if self.recap else "")).strip()
        elif self.recap:
            goal = goal + "\n\n" + self.recap
        authority = self.authority()
        wanted = dict(resume_session_id=self.session, tick=self.tick, live=self.live, width=self.width, records=self.records, commands=self.extra, segments=self.segments,
                      panels=self.panels, command=self.command, representative=authority[0], stop_limits=authority[1])
        accepted = inspect.signature(self.arm.attend).parameters       # an arm that takes fewer options (the line REPL) is handed only those
        report = self.arm.attend(harness, goal, self.out, self.keys, **{name: value for name, value in wanted.items() if name in accepted})
        self.last = report
        self.reports.append(report)
        self.recap = ""
        if self.structure_watch is not None:
            for line in self.structure_watch(report.view.changed(), goal):
                self.say(line)
        if report.final is not None and report.final.session_id:
            self.session = report.final.session_id


__all__ = ["HARNESSES", "WorkTerminal", "terminal_arm", "child_environment", "default_harness", "dollars_of", "harness_builder", "recap_of", "seconds_of"]
