"""The hub's frame on the model's own tool loop: one lean Claude Code session with its trained tools, prepared and checked by the hub.

Role: the hub's own loop asks a model for actions in a text protocol invented here; the model is trained on its provider's tool calls, so on long
tool-heavy work it spends calls on the protocol and is less resourceful than in its native loop. This arm keeps the native loop and adds what the hub
does best. Before the session the hub picks the files that matter (Folder View), outlines the folder, names what is left out and why, and writes that
with the run's rules (a short plan, discover before asking) to a file the CLI appends to its own system prompt. ONE session runs with no settings
sources, strict MCP, a chosen tool list (its own Bash, Read, Edit, Write, Glob, Grep, WebSearch, WebFetch and task tools) and a private temporary
folder per session. After the session reports, the hub's code check of written text runs; when it finds a figure no source file holds or a file the
folder lacks, the same session is resumed once with those findings. Stop, steer and resume are the stream runner's; the session's events reach the
session contract through its stream adapter; tokens and cost are on the sibling runners' basis (plain input plus output, the CLI's own dollars).
An arm is this harness with a tier, written ``native_tool_loop_runner@provider=anthropic,tier=fast``.
"""
from __future__ import annotations

import copy
import dataclasses
import json
import os
import shlex
import shutil
import re
import threading
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from esoi import implementation

from hubofhubs.the_body.internal_context.run_store.jsonl_ledger import private_directory
from hubofhubs.the_world.tools.command_running import refusal, sandbox_wrap
from hubofhubs.the_world.tools.deep import DeepResult, ProgressEvent
from hubofhubs.the_world.tools.events import EVENT_STATUS, EVENT_TOKENS
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig, log
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import NATIVE_TOOLS, build_frame, scratch_folder
from hubofhubs.the_world.tools.delegated_agent_sessions.launch import DeepLaunchSettings
from hubofhubs.the_world.tools.delegated_agent_sessions.control import ControlMessage, RunControl
from hubofhubs.the_world.tools.delegated_agent_sessions.session import claude_project_bases, find_session_file
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import read_text, snapshot, track, unsupported, walk
from hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner import StreamJsonGoalRunner
from hubofhubs.the_self.assembler import arm_needs as needs

SESSION_FOLDER = "native-loop-sessions"
CHECK_MESSAGE = ("A code check of the files you wrote found these. It only reads the text files of the folder, so a figure you computed or read from a database, "
                 "a command's output or a web page is not a finding: keep it and say in the file where it came from. Remove or correct a figure only when you cannot "
                 "account for it, and name only files that exist. Then report again.\n")

UNLIMITED = "unlimited"        # the only way to run with no ceiling on a dimension: the caller says so, never by omission
DEFAULT_CEILING_USD = 20.0     # about 900 times the dearest hard case measured at the fast tier ($0.0225); a consumer can raise or lower it
DEFAULT_CEILING_SECONDS = 4 * 3600.0   # about 160 times the longest hard case measured (88 s)
SOFT_FRACTION = 0.8            # the share of either ceiling at which the session is asked to reach a safe stopping point
BACKSTOP_SECONDS = 120.0       # how long past the time ceiling the CLI's own wall-clock cap waits for the graceful stop
WRAP_UP_MESSAGE = ("The time or spend allowed for this run is nearly used. Reach the next natural safe stopping point: finish the step in hand, leave every "
                   "file and any store in a consistent state, do not start new work, and report what is done, what is left and how to resume.")
MAX_RESUMES = 5   # a bound on the hub's own iteration whatever an injected decision says; the person's own session is not capped by it
PERMISSION_MODES = ("skip", "acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


def default_should_continue(facts: Mapping[str, Any]) -> Dict[str, Any]:
    """The hub's default for iteration the person did not ask for (a resume after its own check): at most one, only for a code finding, never when
    a ceiling is reached. ``facts`` is plain data: ``spend_usd``, ``turns``, ``resumes``, ``findings`` (the code findings), ``changed_outcome``
    (None before a resume, else whether the last resume changed the findings), ``elapsed_seconds``, ``ceiling_usd``, ``ceiling_seconds``, ``ceiling_turns``
    (None when unlimited) and ``soft_fraction``. A resume starts new work, so it is refused once the soft share of either ceiling is used.
    Returns ``{"continue": bool, "reason": str}``; a goal-completion judgment can replace this callable and returns the same shape."""
    if not facts.get("findings"):
        return {"continue": False, "reason": "no_code_finding"}
    if int(facts.get("resumes") or 0) >= 1:
        return {"continue": False, "reason": "resume_limit"}
    usd, turns, seconds = facts.get("ceiling_usd"), facts.get("ceiling_turns"), facts.get("ceiling_seconds")
    soft = float(facts.get("soft_fraction") or SOFT_FRACTION)
    if usd is not None and float(facts.get("spend_usd") or 0.0) >= float(usd) * soft:
        return {"continue": False, "reason": "ceiling_spend"}
    if seconds is not None and float(facts.get("elapsed_seconds") or 0.0) >= float(seconds) * soft:
        return {"continue": False, "reason": "ceiling_time"}
    if turns is not None and int(facts.get("turns") or 0) >= int(turns):
        return {"continue": False, "reason": "ceiling_turns"}
    return {"continue": True, "reason": "code_finding"}


def decision_of(raw: Any) -> Tuple[bool, str]:
    """A decision as ``(continue, reason)`` from a bool, a ``(bool, reason)`` pair or a mapping with ``continue`` and ``reason``."""
    if isinstance(raw, Mapping):
        return bool(raw.get("continue")), str(raw.get("reason") or "")
    if isinstance(raw, (tuple, list)) and raw:
        return bool(raw[0]), str(raw[1]) if len(raw) > 1 else ""
    return bool(raw), "" if raw else "declined"


def session_actions(session_id: Optional[str], root: str, config_dir: Optional[str] = None) -> Tuple[int, List[Tuple[str, Any]]]:
    """``(assistant turns, [(tool name, tool input)])`` of the session's own record; ``(0, [])`` when it cannot be read."""
    if not session_id:
        return 0, []
    try:
        found = find_session_file(session_id, root, config_dir)
        if found is None:
            return 0, []
        turns, actions = 0, []
        with open(found, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get("type") != "assistant":
                    continue
                turns += 1
                content = (event.get("message") or {}).get("content")
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        actions.append((str(block.get("name") or ""), block.get("input") or {}))
        return turns, actions
    except Exception:  # noqa: BLE001 -- a record that cannot be read gives no count and no flags
        return 0, []


def outside_the_folder(root: str, actions: Sequence[Tuple[str, Any]], limit: int = 10, temporary: str = "/tmp") -> List[str]:
    """What the session wrote or ran outside the working folder, by a plain scan of its tool calls: a file written or edited beyond the folder and
    the temporary folder, and a command with an absolute, home or parent path word beyond them or one of the floor's refusals (``sudo``, ``git push``).
    A report for the caller, never a refusal."""
    folder = os.path.abspath(root)
    allowed = (folder, os.path.abspath(temporary or "/tmp"), "/tmp")
    found: List[str] = []
    for name, data in actions:
        if not isinstance(data, dict):
            continue
        if name in WRITE_TOOLS:
            target = str(data.get("file_path") or data.get("notebook_path") or "")
            place = os.path.abspath(os.path.join(folder, os.path.expanduser(target))) if target else ""
            if place and not any(place == a or place.startswith(a.rstrip("/") + "/") for a in allowed):
                found.append(f"{name} wrote {target}")
        elif name == "Bash":
            command = str(data.get("command") or "")
            reason = refusal(command, folder) if command else ""
            if reason:
                found.append(f"ran `{command[:80]}`: {reason}")
    return list(dict.fromkeys(found))[:limit]


def current_session_file(root: str, since: float, config_dir: Optional[str] = None) -> Optional[str]:
    """The record of the session the run has open in ``root``: the newest of the project's files touched since ``since`` (a monotonic start, taken
    as the last few minutes of wall time). ``None`` when there is none."""
    key = re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(root))
    horizon = time.time() - (time.monotonic() - since) - 2.0
    best: Tuple[float, Optional[str]] = (0.0, None)
    for base in claude_project_bases(root, config_dir):
        try:
            for entry in os.scandir(base / key):
                if entry.name.endswith(".jsonl") and entry.stat().st_mtime >= horizon and entry.stat().st_mtime > best[0]:
                    best = (entry.stat().st_mtime, entry.path)
        except OSError:
            continue
    return best[1]


def estimate_spend(path: Optional[str]) -> float:
    """List-price dollars of the tokens a session's record holds (input, cache writes and output; cache reads are cheap and left out), from the hub's
    price table; 0.0 for a record that cannot be read or a model the table does not price. An estimate that lets a ceiling act before the CLI reports cost."""
    if not path:
        return 0.0
    try:
        from hubofhubs.the_world.tools.delegated_agent_sessions.headless_runner import list_price
        totals: Dict[str, List[int]] = {}
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                message = event.get("message") if event.get("type") == "assistant" else None
                usage = (message or {}).get("usage") or {}
                if usage:
                    got = totals.setdefault(str(message.get("model") or ""), [0, 0])
                    got[0] += int(usage.get("input_tokens") or 0) + int(usage.get("cache_creation_input_tokens") or 0)
                    got[1] += int(usage.get("output_tokens") or 0)
        return sum(list_price("anthropic", model, tin, tout) for model, (tin, tout) in totals.items() if model)
    except Exception:  # noqa: BLE001 -- an estimate that fails is no estimate
        return 0.0


def worth_resuming(root: str, found: Sequence[str], gate: str = "text_only") -> List[str]:
    """The findings a resumed turn is worth its cost for. A named file the folder lacks is certain. A figure no source file holds is certain only when
    the code check could read every source: a folder that also holds a database, a spreadsheet or another binary file can hold the figure where the
    check cannot see it (the model computed it from there), and a resume then only re-explains a true figure. ``gate`` is ``always`` (every finding),
    ``text_only`` (named files always, figures when the folder is all text) or ``named_files`` (named files only)."""
    if gate == "always":
        return list(found)
    certain = [x for x in found if "is not in the folder" in x]
    if gate == "named_files":
        return certain
    figures = [x for x in found if x not in certain]
    opaque = any(read_text(Path(root) / rel) is None for rel, _, _ in walk(root))
    return certain + ([] if opaque else figures)


@implementation("delegated-agent-sessions", "native_tool_loop_runner")
class NativeToolLoopRunner(StreamJsonGoalRunner):
    """One hub-framed session on the model's own tool loop (Claude Code lean), with the hub's code check after it."""

    REQUIRES = (needs.CLAUDE_BINARY, needs.CLAUDE_ACCOUNT, needs.CLAUDE_CLI_BOUNDARY, needs.WRITE_ROOT)
    PROVIDERS = ("anthropic",)
    PAID = True              # every run calls a model: never run by a free (offline) metric run
    config_class = SubprocessConfig
    limit_poll_seconds = 1.0    # how often the ceilings are looked at while the session runs
    resume_gate = "text_only"   # which code findings are worth a resumed turn (see ``worth_resuming``)
    on_trial = True          # measured and ranked beside the other harnesses, not chosen for a consumer until the owner promotes it
    tools = NATIVE_TOOLS

    def __init__(self, config: Optional[SubprocessConfig] = None, *, check: bool = True, session_dir: Optional[str] = None,
                 select: Optional[Callable[..., Any]] = None, notes: str = "",
                 ceiling_usd: Union[float, str] = DEFAULT_CEILING_USD, ceiling_seconds: Union[float, str] = DEFAULT_CEILING_SECONDS,
                 ceiling_turns: Optional[int] = None, soft_fraction: float = SOFT_FRACTION, should_continue: Optional[Callable[[Mapping[str, Any]], Any]] = None,
                 permission: str = "skip", sandbox: bool = False, sandbox_network: bool = True, **kwargs: Any):
        super().__init__(config, **kwargs)
        self.check = bool(check)               # the hub's code check of written text after the session
        self.session_dir = session_dir
        self.select = select
        self.notes = notes                     # the consumer's standing text for the frame (where its skills live, its conventions)
        self.ceiling_usd = self.ceiling_of(ceiling_usd, "ceiling_usd")           # the hard limit on spend for the whole run (None only when asked for as UNLIMITED)
        self.ceiling_seconds = self.ceiling_of(ceiling_seconds, "ceiling_seconds")   # the hard limit on wall time for the whole run
        self.ceiling_turns = ceiling_turns     # an optional hard limit on turns (None: the call's own turn budget stands, nothing added)
        if not 0.0 < float(soft_fraction) < 1.0:
            raise ValueError("soft_fraction must be between 0 and 1")
        self.soft_fraction = float(soft_fraction)   # the share of either ceiling at which the session is asked to wrap up
        self.should_continue = should_continue or default_should_continue   # the one seam for the hub's own iteration: plain facts in, a decision out
        if permission not in PERMISSION_MODES:
            raise ValueError(f"permission must be one of {PERMISSION_MODES}")
        self.permission = permission           # "skip" keeps today's --dangerously-skip-permissions; any other value is the CLI's own --permission-mode
        self.sandbox = bool(sandbox)           # run the session inside the hub's bubblewrap sandbox (the folder, the session's temporary folder and the CLI's config writable)
        self.sandbox_network = bool(sandbox_network)
        self.local = threading.local()         # per call: the frame file, the temporary folder and the launcher of the run in this thread

    @staticmethod
    def ceiling_of(value: Union[float, str, None], name: str) -> Optional[float]:
        """A ceiling as a positive number, or None for the explicit ``UNLIMITED``. Omission never means unlimited: the defaults are on."""
        if value == UNLIMITED:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(f"{name} must be a positive number or UNLIMITED")
        return float(value)

    @property
    def cfg(self) -> SubprocessConfig:  # type: ignore[override]
        """The run's configuration; in a thread that holds a launcher (permission mode or sandbox) the worker program is that launcher."""
        base = self.__dict__.get("_cfg")
        local = self.__dict__.get("local")
        launcher = getattr(local, "launcher", None)
        started = getattr(local, "started", None)
        if base is None or not (launcher or started):
            return base
        mine = copy.copy(base)
        if launcher:
            mine.claude_path = launcher
            if self.permission != "skip":
                mine.skip_permissions = False
        if started is not None and self.ceiling_seconds is not None and getattr(mine, "timeout_seconds", None) is None:
            # the CLI's own wall-clock cap, a backstop a little past the time ceiling that the graceful stop should reach first
            mine.timeout_seconds = max(self.ceiling_seconds - (time.monotonic() - started), 1.0) + BACKSTOP_SECONDS
        return mine

    @cfg.setter
    def cfg(self, value: SubprocessConfig) -> None:
        self.__dict__["_cfg"] = value

    # --- launch -----------------------------------------------------------------------------------------------------------------

    def launch_settings(self) -> DeepLaunchSettings:
        base = super().launch_settings()
        return dataclasses.replace(
            base, tools=base.tools if base.tools is not None else tuple(self.tools),
            setting_sources="" if base.setting_sources is None else base.setting_sources, strict_mcp=True, exclude_dynamic_sections=True,
            append_system_prompt_file=getattr(self.local, "frame_file", None) or base.append_system_prompt_file,
            max_budget_usd=self.remaining_usd(base.max_budget_usd), max_turns=self.remaining_turns(base.max_turns))

    def remaining_usd(self, fallback: Optional[float]) -> Optional[float]:
        """The CLI's spend ceiling for this launch: the person's ceiling less what the run already spent (a resume gets the rest), else the setting's own."""
        if self.ceiling_usd is None:
            return fallback
        # the CLI's own budget flag is a backstop at the hard limit; the graceful stop, which keeps the session resumable, should reach it first
        return max(float(self.ceiling_usd) - float(getattr(self.local, "spent", 0.0) or 0.0), 0.01)

    def remaining_turns(self, fallback: Optional[int]) -> Optional[int]:
        if self.ceiling_turns is None:
            return fallback
        return max(int(self.ceiling_turns) - int(getattr(self.local, "used_turns", 0) or 0), 1)

    def build_env(self, requester_user_id: Optional[str] = None, run_id: Optional[str] = None) -> dict:
        env = super().build_env(requester_user_id, run_id)
        scratch = getattr(self.local, "scratch", "")
        if scratch:
            env["TMPDIR"] = scratch      # the run's commands keep their files here across a stop and a resume
        return env

    # --- the run ----------------------------------------------------------------------------------------------------------------

    def prepare(self, goal: str, brief: str, preamble: str, root: str, session_key: str) -> None:
        folder = self.session_dir or private_directory(SESSION_FOLDER) or ""
        scratch = scratch_folder(folder, session_key)
        self.local.scratch = scratch
        self.local.frame_file = None
        self.local.sandboxed = False
        self.local.launcher = self.write_launcher(folder_for_launcher=scratch, root=root)
        frame = build_frame(brief or goal, preamble or "", root, select=self.select, notes=self.notes)
        if scratch:
            path = os.path.join(scratch, "hub-frame.md")
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(frame.text)
                self.local.frame_file = "/tmp/hub-frame.md" if self.local.sandboxed else path   # the sandbox shows the session's folder as /tmp
            except OSError as error:
                log.warning("hub frame not written (%s): the session runs without it", error)

    def write_launcher(self, *, folder_for_launcher: str, root: str) -> str:
        """The program the CLI is started through when a permission mode or the sandbox is asked for: a small script that puts the hub's sandbox prefix
        (``sandbox_wrap``) and the mode flag before the real CLI and passes every argument on. ``""`` when neither is asked for, or the sandbox program
        is not installed (the run is then unconfined and says so in its log)."""
        if self.permission == "skip" and not self.sandbox:
            return ""
        base = self.__dict__.get("_cfg")
        real = shutil.which(base.claude_path) if base is not None else None
        if not real or not folder_for_launcher:
            return ""
        prefix: Tuple[str, ...] = ()
        if self.sandbox:
            environment = self.goal_settings().environment()     # the caller's mapping; the hub reads no process environment
            home = environment.get("HOME") or os.path.expanduser("~")
            config = [p for p in (environment.get("CLAUDE_CONFIG_DIR", ""), os.path.join(home, ".claude"), os.path.join(home, ".claude.json")) if p and os.path.exists(p)]
            prefix = sandbox_wrap(root, network=self.sandbox_network, extra_read_write=config, scratch=folder_for_launcher)
            if not prefix:
                log.warning("sandbox asked for but its program is not installed: the session runs unconfined")
            self.local.sandboxed = bool(prefix)
        mode = [] if self.permission == "skip" else ["--permission-mode", self.permission]
        if not prefix and not mode:
            return ""
        path = os.path.join(folder_for_launcher, "launch-claude.sh")
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\n" + f'[ "$1" = "--version" ] && exec {shlex.quote(real)} "$@"\n'     # a version probe needs neither the sandbox nor the mode
                             + "exec " + " ".join(shlex.quote(x) for x in [*prefix, real, *mode]) + ' "$@"\n')
            os.chmod(path, 0o700)
        except OSError as error:
            log.warning("launcher not written (%s): the session runs as configured without it", error)
            return ""
        return path

    def run_goal_once(self, *, goal: str, brief: str, model: Optional[str] = None, max_turns: Optional[int] = None,  # type: ignore[override]
                      emit: Any = None, context_preamble: Optional[str] = None, run_id: Optional[str] = None, working_dir: Optional[str] = None,
                      resume_session_id: Optional[str] = None, prompt_budget_tokens: Optional[int] = None, requester_user_id: Optional[str] = None,
                      cancel_check: Any = None, control: Any = None) -> DeepResult:
        root = os.path.abspath(self.cfg.working_dir if working_dir is None else working_dir)
        preamble = self.cfg.context_preamble if context_preamble is None else context_preamble
        key = resume_session_id or run_id or uuid.uuid4().hex
        self.local.resumed = False
        self.prepare(goal, brief, preamble, root, key)
        before = snapshot(root)
        self.local.emit = emit
        common = dict(model=model, max_turns=max_turns, emit=emit, run_id=run_id, working_dir=working_dir, prompt_budget_tokens=prompt_budget_tokens,
                      requester_user_id=requester_user_id, cancel_check=cancel_check, control=control)
        self.local.spent, self.local.used_turns = 0.0, 0
        self.local.started, self.local.softened, self.local.hard = time.monotonic(), False, ""
        self.local.estimated_at, self.local.estimate = 0.0, 0.0
        self.local.spend_before = 0.0
        common["control"] = self.limit_control(control, root)
        try:
            result = super().run_goal_once(goal=goal, brief=brief, context_preamble=context_preamble, resume_session_id=resume_session_id, **common)
            self.usage(result, root, emit, resumes=0)
            result = self.iterate(result, root, before, common, emit, cancel_check)
            self.flag_outside(result, root, emit)
            self.finish(result, root, emit)
        finally:
            self.local.started = None
        return result

    # --- the ceilings: a soft limit that asks for a safe stopping point, a hard limit that stops and keeps the session resumable ---------------

    def spend_now(self, root: str) -> float:
        """What the run has spent so far: the settled cost of finished sessions, or the running session's own record priced from the hub's table when that is more
        (the CLI reports cost only when a session ends). An estimate of tokens at list price, read at most every few seconds."""
        settled = float(getattr(self.local, "spent", 0.0) or 0.0)
        now = time.monotonic()
        if now - float(getattr(self.local, "estimated_at", 0.0) or 0.0) >= 3.0:
            self.local.estimated_at = now
            self.local.estimate = estimate_spend(current_session_file(root, getattr(self.local, "started", None) or now,
                                                                      getattr(self.goal_settings(), "claude_config_dir", None)))
        return max(settled, float(getattr(self.local, "estimate", 0.0) or 0.0))

    def limit_state(self, root: str) -> Tuple[str, str]:
        """``("ok" | "soft" | "hard", what)`` where ``what`` names the ceiling reached (``spend`` or ``time``)."""
        started = getattr(self.local, "started", None)
        if started is None:
            return "ok", ""
        reached: List[Tuple[float, str]] = []
        if self.ceiling_seconds is not None:
            reached.append(((time.monotonic() - started) / self.ceiling_seconds, "time"))
        if self.ceiling_usd is not None:
            reached.append((self.spend_now(root) / self.ceiling_usd, "spend"))
        share, what = max(reached, default=(0.0, ""))
        return ("hard" if share >= 1.0 else "soft" if share >= self.soft_fraction else "ok"), what if share >= self.soft_fraction else ""

    def limit_control(self, control: Optional[RunControl], root: str) -> Optional[RunControl]:
        """The caller's control with the ceilings added: at the soft limit the session is steered ONCE (through the control's own steer path) to reach a safe
        stopping point; at the hard limit the run is stopped the way a person's stop is, keeping the session. The caller's own messages and stop still pass."""
        if self.ceiling_usd is None and self.ceiling_seconds is None:
            return control
        mine = control or RunControl()
        local = self.local

        def claim() -> List[ControlMessage]:
            messages = list(mine.claim_inputs() or [])
            if not local.softened and not local.hard and self.limit_state(root)[0] != "ok":
                local.softened = True
                messages.append(ControlMessage(id="hub-wrap-up-" + uuid.uuid4().hex[:8], text=WRAP_UP_MESSAGE))
                log.info("native loop: the soft limit is reached; the session is asked to reach a safe stopping point")
                if getattr(local, "emit", None) is not None:
                    try:
                        local.emit(ProgressEvent(type=EVENT_STATUS, text="The soft limit is reached: the session is asked to reach a safe stopping point.",
                                                 data=dict(phase="soft_limit", ceiling_usd=self.ceiling_usd, ceiling_seconds=self.ceiling_seconds)))
                    except Exception:  # noqa: BLE001
                        pass
            return messages

        def stop() -> bool:
            if mine.cancel_requested():
                return True
            state, what = self.limit_state(root)
            if state == "hard":
                local.hard = what
            return state == "hard"

        return RunControl(claim_inputs=claim, mark_seen=mine.mark_seen, cancel_requested=stop, pause_requested=mine.pause_requested,
                          poll_seconds=min(float(mine.poll_seconds), self.limit_poll_seconds), label=mine.label)

    def finish(self, result: DeepResult, root: str, emit: Any) -> None:
        """What the caller needs to account for the run and to continue it: ``spend_usd``, ``elapsed_seconds``, ``resume_handle`` (the session id) and, when a
        ceiling shaped the run, which one in ``end_reason``: ``wrapped_up_at_soft_limit`` or ``stopped_at_hard_limit`` with what was reached."""
        elapsed = time.monotonic() - (getattr(self.local, "started", None) or time.monotonic())
        result.spend_usd = max(float(result.cost_usd or 0.0), self.spend_now(root))      # type: ignore[attr-defined]
        result.elapsed_seconds = elapsed                                                # type: ignore[attr-defined]
        result.resume_handle = result.session_id                                        # type: ignore[attr-defined]
        if getattr(self.local, "hard", ""):
            result.end_reason = f"stopped_at_hard_limit:{self.local.hard}"
        elif getattr(self.local, "softened", False):
            result.end_reason = "wrapped_up_at_soft_limit"
        if result.cancelled and getattr(self.local, "hard", ""):
            result.error = (f"The run was stopped at its hard limit ({self.local.hard}). Work already finished is kept; resume session "
                            f"{result.session_id} to continue.")

    def usage(self, result: DeepResult, root: str, emit: Any, resumes: int) -> None:
        """What the run has spent so far, kept for the next launch's ceiling and shown to a watcher as a usage event (so a person can stop it)."""
        self.local.spent = float(result.cost_usd or 0.0)
        turns, _ = session_actions(result.session_id, root, getattr(self.goal_settings(), "claude_config_dir", None))
        self.local.used_turns = turns
        if emit is not None:
            try:
                emit(ProgressEvent(type=EVENT_TOKENS, text=f"spent ${self.local.spent:.4f} in {turns} turns",
                                   data=dict(cost_usd=self.local.spent, tokens=int(result.tokens or 0), turns=turns, resumes=resumes,
                                             ceiling_usd=self.ceiling_usd, ceiling_seconds=self.ceiling_seconds, ceiling_turns=self.ceiling_turns)))
            except Exception:  # noqa: BLE001 -- a sink that fails never stops the run
                pass

    def iterate(self, result: DeepResult, root: str, before: Any, common: Dict[str, Any], emit: Any, cancel_check: Any) -> DeepResult:
        """The hub's own iteration, the part the person did not ask for: after the session reports, the code check runs, and each resume it would start is
        first put to ``should_continue`` with plain facts. A refusal ends the run with its reason in ``end_reason``; nothing else decides."""
        if not (self.check and result.met and result.session_id):
            return result
        resumes, changed_outcome, last = 0, None, None
        while True:
            files: "OrderedDict[str, None]" = OrderedDict()
            track(root, before, files)
            everything = unsupported(root, list(files))
            found = worth_resuming(root, everything, self.resume_gate)
            self.local.resumed = resumes > 0
            if last is not None:
                changed_outcome = found != last
            last = found
            if not everything:
                return result
            facts = dict(spend_usd=float(self.local.spent), turns=int(self.local.used_turns), resumes=resumes, findings=list(found),
                         unchecked_findings=[x for x in everything if x not in found], changed_outcome=changed_outcome,
                         elapsed_seconds=time.monotonic() - (getattr(self.local, "started", None) or time.monotonic()), ceiling_usd=self.ceiling_usd,
                         ceiling_seconds=self.ceiling_seconds, ceiling_turns=self.ceiling_turns, soft_fraction=self.soft_fraction)
            try:
                go, reason = decision_of(self.should_continue(facts))
            except Exception as error:  # noqa: BLE001 -- a failing decision is a refusal to iterate, never a crash
                go, reason = False, f"decision_failed:{type(error).__name__}"
            if go and resumes >= MAX_RESUMES:
                go, reason = False, "resume_cap"
            if go and cancel_check is not None and cancel_check():
                go, reason = False, "cancelled"
            if not go:
                if found or everything:
                    result.end_reason = f"resume_stopped:{reason or 'declined'}"
                return result
            log.info("native loop: the code check found %d things; resuming the session (resume %d)", len(found), resumes + 1)
            if emit is not None:
                try:
                    emit(ProgressEvent(type=EVENT_STATUS, text=f"The hub's code check found {len(found)} things; the session is resumed once more.",
                                       data=dict(phase="hub_resume", resumes=resumes + 1, reason=reason)))
                except Exception:  # noqa: BLE001
                    pass
            message = CHECK_MESSAGE + "\n".join(found)
            again = super().run_goal_once(goal=message, brief=message, context_preamble="", resume_session_id=result.session_id, **common)
            again.cost_usd = float(result.cost_usd or 0.0) + float(again.cost_usd or 0.0)
            again.tokens = int(result.tokens or 0) + int(again.tokens or 0)
            resumes += 1
            self.usage(again, root, emit, resumes)
            if not again.met and again.session_id == result.session_id and not again.cancelled:
                return result      # a failed second turn does not undo an accepted first one
            result = again
            if not result.met or not result.session_id:
                return result

    def flag_outside(self, result: DeepResult, root: str, emit: Any) -> None:
        """Report, on the result, what the session wrote or ran outside the working folder (``result.outside_folder``, a list of short lines). A report only."""
        _turns, actions = session_actions(result.session_id, root, getattr(self.goal_settings(), "claude_config_dir", None))
        result.outside_folder = outside_the_folder(root, actions, temporary=self.goal_settings().environment().get("TMPDIR", "/tmp"))    # type: ignore[attr-defined]
        if result.outside_folder and emit is not None:               # type: ignore[attr-defined]
            try:
                emit(ProgressEvent(type=EVENT_STATUS, text="The session wrote or ran something outside the working folder.",
                                   data=dict(phase="outside_folder", items=result.outside_folder)))   # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
