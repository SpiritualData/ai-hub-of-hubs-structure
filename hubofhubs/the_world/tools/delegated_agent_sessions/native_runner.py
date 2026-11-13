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
import sys
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
from hubofhubs.the_world.tools.delegated_agent_sessions import answer_check, general_helper as helpers, providers
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig, log
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import NATIVE_TOOLS, build_frame, scratch_folder
from hubofhubs.the_world.tools.delegated_agent_sessions.launch import DeepLaunchSettings
from hubofhubs.the_world.tools.delegated_agent_sessions.control import ControlMessage, RunControl
from hubofhubs.the_world.tools.delegated_agent_sessions.run_ceilings import (   # the ceilings are shared with the other runners; the names stay importable from here
    BACKSTOP_SECONDS, DEFAULT_CEILING_SECONDS, DEFAULT_CEILING_USD, MAX_RESUMES, SOFT_FRACTION, UNLIMITED, WRAP_UP_MESSAGE, LimitWatch, active_watch, ceiling_of,
    current_session_file, decision_of, default_should_continue, estimate_spend, session_spend, soft_fraction_of, stop_aware)
from hubofhubs.the_world.tools.delegated_agent_sessions.session import find_session_file, resolve_session_file
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import read_text, snapshot, track, walk
from hubofhubs.the_world.tools.delegated_agent_sessions.code_check import NO_SOURCE, NOT_IN_FOLDER, unsupported
from hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner import StreamJsonGoalRunner
from hubofhubs.the_self.assembler import arm_needs as needs

SESSION_FOLDER = "native-loop-sessions"
#: Commands that only read (no flag of theirs writes), allowed by rule when the permission mode asks before running a command. ``find`` is here with its running and deleting flags denied.
READ_ONLY_COMMANDS = ("ls", "cat", "head", "tail", "wc", "grep", "rg", "find", "sort", "uniq", "cut", "tr", "pwd", "file", "stat", "du", "tree", "basename", "dirname", "diff", "echo", "date")
READ_ONLY_DENIED = ("Bash(find:*-exec*)", "Bash(find:*-execdir*)", "Bash(find:*-ok*)", "Bash(find:*-delete*)", "Bash(find:*-fprint*)")
CHECK_MESSAGE = ("A code check of the files you wrote found these. It only reads the text files of the folder, so a figure you computed or read from a database, "
                 "a command's output or a web page is not a finding: keep it and say in the file where it came from. Remove or correct a figure only when you cannot "
                 "account for it, and name only files that exist. Then report again.\n")

PERMISSION_MODES = ("skip", "acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


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


def worth_resuming(root: str, found: Sequence[str], gate: str = "text_only") -> List[str]:
    """The findings a resumed turn is worth its cost for. A named file the folder lacks is certain. A figure no source file holds is certain only when
    the code check could read every source: a folder that also holds a database, a spreadsheet or another binary file can hold the figure where the
    check cannot see it (the model computed it from there), and a resume then only re-explains a true figure. ``gate`` is ``always`` (every finding),
    ``text_only`` (named files always, figures when the folder is all text) or ``named_files`` (named files only)."""
    if gate == "always":
        return list(found)
    certain = [x for x in found if NOT_IN_FOLDER in x]
    if gate == "named_files":
        return certain
    figures = [x for x in found if NO_SOURCE in x]          # a total or count the check could not verify is not certain: a person or a reviewer decides, the session is not resumed for it
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
    tools = NATIVE_TOOLS
    by_task_id = True           # ``steer_agent`` and ``stop_agent`` name a helper by the CLI's task id (the stream's task lines tell it), not by the id of the call that started it

    def __init__(self, config: Optional[SubprocessConfig] = None, *, check: bool = True, session_dir: Optional[str] = None,
                 select: Optional[Callable[..., Any]] = None, notes: str = "",
                 ceiling_usd: Union[float, str] = DEFAULT_CEILING_USD, ceiling_seconds: Union[float, str] = DEFAULT_CEILING_SECONDS,
                 ceiling_turns: Optional[int] = None, soft_fraction: float = SOFT_FRACTION, should_continue: Optional[Callable[[Mapping[str, Any]], Any]] = None,
                 stop_inputs: Optional[Mapping[str, Any]] = None, permission: str = "skip", sandbox: bool = False, sandbox_network: bool = True,
                 helper_calls: Optional[int] = None, check_answer: bool = True, **kwargs: Any):
        super().__init__(config, ceiling_usd=ceiling_usd, ceiling_seconds=ceiling_seconds, soft_fraction=soft_fraction, **kwargs)   # the ceilings are the stream runner's (run_ceilings)
        self.check = bool(check)               # the hub's code check of written text after the session
        self.session_dir = session_dir
        self.select = select
        self.notes = notes                     # the consumer's standing text for the frame (where its skills live, its conventions)
        self.ceiling_turns = ceiling_turns     # an optional hard limit on turns (None: the call's own turn budget stands, nothing added)
        # The one seam for the hub's own iteration: plain facts in, a decision out. The default asks Goal Completion's stop decision (resolved by name from the
        # records, with what the person stated and the policy as ``stop_inputs``), and keeps ``default_should_continue`` as the fallback when none is assembled.
        self.should_continue = should_continue or stop_aware(stated=(stop_inputs or {}).get("stated"), policy=(stop_inputs or {}).get("policy"))
        if permission not in PERMISSION_MODES:
            raise ValueError(f"permission must be one of {PERMISSION_MODES}")
        self.permission = permission           # "skip" keeps today's --dangerously-skip-permissions; any other value is the CLI's own --permission-mode
        self.sandbox = bool(sandbox)           # run the session inside the hub's bubblewrap sandbox (the folder, the session's temporary folder and the CLI's config writable)
        self.sandbox_network = bool(sandbox_network)
        self.local = threading.local()         # per call: the frame file, the temporary folder and the launcher of the run in this thread
        self.helper_calls = helpers.DEFAULT_CALLS if helper_calls is None else int(helper_calls)    # the general sub-agent calls the whole run may make (0: none is offered)
        self.live: Any = None                  # (the run's folder, when it started) of the latest run, for what is asked of it from another thread (a helper's cost)
        self.check_answer = bool(check_answer)  # the answer check after the session (one fast-tier call; a resume on a fail)
        self.run_context: Any = None           # the ``RunContext`` a wrapper attached for the run about to start (the person's words, the saved notes), or None
        self.run_notes = ""                    # the saved-notes block of this run, carried by the helpers' brief
        self.original_input = ""           # the person's first message of the session, verbatim (``answer_check``, the stop decision's goal, the helpers' brief)
        self.answer_asker: Any = None           # the answer check's model call (None: built from the hub's Claude CLI provider on the answer check role's tier); tests inject one
        self.channel: Any = None               # the channel to the running helpers of the latest run (messages in, a stop), set when helpers are offered

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
            base, tools=base.tools if base.tools is not None else tuple(getattr(self.local, "tools", None) or self.tools),
            agents_file=getattr(self.local, "agents_file", None) or base.agents_file, settings_file=getattr(self.local, "settings_file", None) or base.settings_file,
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
        self.local.tools, self.local.agents_file, self.local.settings_file = tuple(self.tools), None, None
        note = self.offer_helpers(scratch, {}, self.helper_calls)
        self.allow_read_only(scratch)
        frame = build_frame(brief or goal, preamble or "", root, select=self.select, notes=self.notes, extras=(note,) if note else ())
        if scratch:
            path = os.path.join(scratch, "hub-frame.md")
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(frame.text)
                self.local.frame_file = "/tmp/hub-frame.md" if self.local.sandboxed else path   # the sandbox shows the session's folder as /tmp
            except OSError as error:
                log.warning("hub frame not written (%s): the session runs without it", error)

    def allow_read_only(self, scratch: str) -> None:
        """In a permission mode that asks before a command (``acceptEdits``), nobody is there to answer in a headless session, so the CLI refuses every command it cannot prove harmless, a
        quoted ``find`` or a ``grep`` with a pattern included. Looking around the person's own folder is what a run starts with, so the read-only commands of ``READ_ONLY_COMMANDS`` are
        allowed by rule (the ``deny`` rules keep ``find`` from running or deleting anything). Anything else, a loop or a command that writes, is still refused and listed."""
        if self.permission == "skip" or not scratch:
            return
        rules = {"permissions": {"allow": [f"Bash({name}:*)" for name in READ_ONLY_COMMANDS], "deny": list(READ_ONLY_DENIED)}}
        real = os.path.join(scratch, "agent-guard.json" if self.local.settings_file else "permission-rules.json")
        try:
            base: Dict[str, Any] = {}
            if self.local.settings_file and os.path.exists(real):
                with open(real, encoding="utf-8") as handle:
                    base = json.load(handle)
            with open(real, "w", encoding="utf-8") as handle:
                json.dump(helpers.agent_channel.merge_settings(base, rules), handle, indent=1)
            self.local.settings_file = self.visible(real)
        except (OSError, ValueError) as error:
            log.warning("read-only command rules not written (%s): commands the CLI cannot check are refused", error)

    def model_of(self, tier: str) -> Optional[str]:
        """The model of a role's tier for this run's provider, as the CLI takes it; None when no model is chosen for it."""
        return self.cli_safe(providers.model_for(self.provider, tier))

    def visible(self, path: str) -> str:
        """The path as the session sees it: the sandbox shows the session's folder as /tmp."""
        return "/tmp/" + os.path.basename(path) if getattr(self.local, "sandboxed", False) else path

    def offer_helpers(self, scratch: str, defined: Dict[str, Dict[str, Any]], budget: int) -> str:
        """Offer the general sub-agent (and the ``defined`` agents of an arm that has its own) to this run: writes the agents, the guard and the channel hook, adds the Agent tool and sets
        ``self.channel``. Returns the frame's note, or ``""`` when nothing is offered (no budget, no folder to write in, or the sub-agent role's tier has no model chosen)."""
        self.channel = None
        offered = dict(defined)
        if budget > 0 and scratch:
            try:
                offered.update(helpers.helper_definition(helpers.sub_agent_model(self.model_of, self.tier), self.original_input, self.run_notes))
            except (KeyError, ValueError) as error:
                log.warning("no tier for the sub-agent role (%s): no general sub-agent is offered", error)
        if not offered or budget <= 0 or not scratch:
            return ""
        python = "python3" if getattr(self.local, "sandboxed", False) else (sys.executable or "python3")
        written = helpers.write_offer(scratch, self.visible, python, offered, budget)
        if written is None:
            log.warning("the sub-agent guard is not written: the session runs with no sub-agents")
            return ""
        self.local.agents_file, self.local.settings_file, self.channel = written
        self.local.tools = tuple(self.tools) + (helpers.agents.AGENT_TOOL,)
        return helpers.helper_note(budget) if helpers.HELPER in offered else ""

    def steer_agent(self, task_id: str, text: str, message_id: str = "") -> bool:
        """Queue a message for the helper the CLI calls ``task_id``: it reads it at its next tool call (``agent_channel``). False when no helper is offered to this run."""
        channel = self.channel
        return bool(channel is not None and channel.send(task_id, text, message_id or uuid.uuid4().hex[:8]))

    def stop_agent(self, task_id: str) -> bool:
        """End one helper. The CLI's own ``stop_task`` stops it at once, a command it runs included; as a fallback its next tool call is refused with the reason that the person stopped it, so it
        reports what it has. Its own helpers are stopped by the caller, which knows the tree."""
        channel = self.channel
        soft = bool(channel is not None and channel.stop(task_id))        # the fallback: the helper's next tool call is refused
        hard = self.stop_task(task_id)                                    # the CLI's own stop of that task: a helper in a long command ends at once
        return soft or hard

    def agent_cost(self, task_id: str) -> Optional[float]:
        """What one helper cost, priced from its own transcript (``subagents/agent-<task id>.jsonl`` beside the session's record) on the hub's table, the same estimate the ceilings use; None
        when the record cannot be found. The CLI reports one cost for the whole session, the helpers' included."""
        live = self.live_session
        if not live:
            return None
        try:
            record = resolve_session_file(live[0], live[1], getattr(self.goal_settings(), "claude_config_dir", None))
            path = os.path.join(os.path.splitext(record)[0], "subagents", f"agent-{task_id}.jsonl") if record else ""
            return round(estimate_spend(path), 6) if path and os.path.exists(path) else None
        except Exception:  # noqa: BLE001 -- a figure that cannot be found is no figure
            return None

    def delivered_messages(self) -> List[Tuple[str, str]]:
        """``[(task id, message id)]`` the helpers have read since this was last asked."""
        channel = self.channel
        return channel.delivered() if channel is not None else []

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
        given = self.run_context                           # what a wrapper told this runner apart from the goal text (``run_context``): the person's words, the saved notes
        if resume_session_id is None or not self.original_input:
            self.original_input = (given.original if given is not None and given.original else "") or brief or goal    # the person's first message, verbatim: the reference of the stop decision, the helpers' brief and the answer check
        self.run_notes = given.notes if given is not None else ""
        self.local.hub_resumes = 0
        self.prepare(goal, brief, preamble, root, key)
        before = snapshot(root)
        self.local.emit = emit
        if resume_session_id is None:
            self.local.goal_text = brief or goal            # the person's own words: the code check reads the places they name
        common = dict(model=model, max_turns=max_turns, emit=emit, run_id=run_id, working_dir=working_dir, prompt_budget_tokens=prompt_budget_tokens,
                      requester_user_id=requester_user_id, cancel_check=cancel_check, control=control)
        self.local.spent, self.local.used_turns = 0.0, 0
        self.local.estimated_at, self.local.estimate = 0.0, 0.0
        self.local.spend_before = 0.0
        self.local.watch = active_watch()                  # the run_goal that called this has started the ceilings and wrapped the control
        owned = self.local.watch is None
        if owned:                                          # called directly: this run starts them
            self.local.watch = self.new_watch(root, emit)
            self.local.watch.__enter__()
            common["control"] = self.local.watch.wrap(control, self.limit_poll_seconds)
        self.local.started = self.local.watch.started
        self.live = (root, self.local.started)
        try:
            result = super().run_goal_once(goal=goal, brief=brief, context_preamble=context_preamble, resume_session_id=resume_session_id, **common)
            self.usage(result, root, emit, resumes=0)
            result = self.iterate(result, root, before, common, emit, cancel_check)
            result = self.answer_round(result, root, common, emit, cancel_check)
            self.flag_outside(result, root, emit)
            self.finish(result, root, emit)
        finally:
            self.local.started = None
            if owned:
                self.local.watch.__exit__()
        return result

    # --- the ceilings: a soft limit that asks for a safe stopping point, a hard limit that stops and keeps the session resumable ---------------

    def spend_now(self, root: str) -> float:
        """What the run has spent so far: the settled cost of finished sessions, or the running session's own record priced from the hub's table when that is more
        (the CLI reports cost only when a session ends). An estimate of tokens at list price, read at most every few seconds."""
        settled = float(getattr(self.local, "spent", 0.0) or 0.0)
        now = time.monotonic()
        if now - float(getattr(self.local, "estimated_at", 0.0) or 0.0) >= 3.0:
            self.local.estimated_at = now
            watch = getattr(self.local, "watch", None)
            self.local.estimate = session_spend(root, getattr(watch, "session_id", ""), getattr(self.goal_settings(), "claude_config_dir", None))      # this run's own session, by id
        return max(settled, float(getattr(self.local, "estimate", 0.0) or 0.0))

    def new_watch(self, root: str, emit: Any) -> LimitWatch:
        """The run's ceilings, priced from this runner's own spend (``spend_now`` keeps its own pace, so the watch asks every time)."""
        return LimitWatch(self.ceiling_usd, self.ceiling_seconds, self.soft_fraction, spend_of=lambda: self.spend_now(root), emit=emit, log=log, throttle=0.0)

    def finish(self, result: DeepResult, root: str, emit: Any) -> None:
        """What the caller needs to account for the run and to continue it: ``spend_usd``, ``elapsed_seconds``, ``resume_handle`` (the session id) and, when a
        ceiling shaped the run, which one in ``end_reason``: ``wrapped_up_at_soft_limit`` or ``stopped_at_hard_limit`` with what was reached."""
        elapsed = self.local.watch.elapsed()
        result.spend_usd = max(float(result.cost_usd or 0.0), self.spend_now(root))      # type: ignore[attr-defined]
        result.elapsed_seconds = elapsed                                                # type: ignore[attr-defined]
        result.resume_handle = result.session_id                                        # type: ignore[attr-defined]
        watch = self.local.watch
        if watch.hard or watch.softened:
            result.end_reason = watch.end_reason()
        if result.cancelled and watch.hard:
            result.error = (f"The run was stopped at its hard limit ({watch.hard}). Work already finished is kept; resume session "
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
        resumes, changed_outcome, last, rounds = 0, None, None, []
        while True:
            files: "OrderedDict[str, None]" = OrderedDict()
            track(root, before, files)
            everything = unsupported(root, list(files), goal=str(getattr(self.local, "goal_text", "") or ""))
            found = worth_resuming(root, everything, self.resume_gate)
            self.local.resumed = resumes > 0
            if last is not None:
                changed_outcome = found != last
            rounds.append(dict(findings=len(found), spend_usd=float(self.local.spent), elapsed_seconds=self.local.watch.elapsed(),
                               changed=len(files) if last is None else int(found != last)))
            last = found
            if not everything:
                return result
            facts = dict(goal=self.original_input, rounds=list(rounds), spend_usd=float(self.local.spent), turns=int(self.local.used_turns), resumes=resumes, findings=list(found),
                         unchecked_findings=[x for x in everything if x not in found], changed_outcome=changed_outcome,
                         elapsed_seconds=self.local.watch.elapsed(), ceiling_usd=self.ceiling_usd,
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
            # The CLI's reported cost is the session's running total: a resumed session starts from the cost stored with it, so its report already holds the
            # earlier turn. Adding the two counts the first turn twice. A continuation that started a fresh session (the old one was gone) is a new total.
            if again.session_id == result.session_id:
                again.cost_usd = max(float(result.cost_usd or 0.0), float(again.cost_usd or 0.0))
            else:
                again.cost_usd = float(result.cost_usd or 0.0) + float(again.cost_usd or 0.0)
            again.tokens = int(result.tokens or 0) + int(again.tokens or 0)
            resumes += 1
            self.local.hub_resumes = resumes
            self.usage(again, root, emit, resumes)
            if not again.met and again.session_id == result.session_id and not again.cancelled:
                return result      # a failed second turn does not undo an accepted first one
            result = again
            if not result.met or not result.session_id:
                return result

    def answer_round(self, result: DeepResult, root: str, common: Dict[str, Any], emit: Any, cancel_check: Any) -> DeepResult:
        """The answer check (``answer_check``): the final answer is held to the person's first message, verbatim, and on a fail the same session is resumed once with a steer built
        from it. The resume limit, the ceilings and a cancel apply as for the code check's resumes. The record is ``result.answer_check``."""
        original = str(self.original_input or "").strip()
        if not (self.check and self.check_answer and result.met and result.session_id and str(result.output or "").strip() and original):
            return result
        ask = self.answer_asker
        if ask is None:
            try:
                ask = answer_check.answer_ask(self.model_of, self.tier, claude_path=self.__dict__["_cfg"].claude_path or "claude")
            except Exception as error:  # noqa: BLE001 -- a check that cannot be set up is no opinion
                log.warning("answer check not set up (%s): the answer stands", error)
                ask = None
        watch = self.local.watch
        taken: Dict[str, Any] = {}

        def allowed() -> str:
            if int(getattr(self.local, "hub_resumes", 0) or 0) >= MAX_RESUMES:
                return "resume_cap"
            if watch.softened or watch.hard_reached():
                return "ceiling_reached"
            return "cancelled" if cancel_check is not None and cancel_check() else ""

        def tell(phase: str, text: str, data: Mapping[str, Any]) -> None:
            if emit is not None:
                try:
                    emit(ProgressEvent(type=EVENT_STATUS, text=text, data=dict(data, phase=phase)))
                except Exception:  # noqa: BLE001 -- a sink that fails never stops the run
                    pass

        def resume(message: str) -> Optional[str]:
            again = super(NativeToolLoopRunner, self).run_goal_once(goal=message, brief=message, context_preamble="", resume_session_id=result.session_id, **common)
            if again.session_id == result.session_id:        # the CLI's cost is the session's running total: the resumed report already holds the earlier turns
                again.cost_usd = max(float(result.cost_usd or 0.0), float(again.cost_usd or 0.0))
            else:
                again.cost_usd = float(result.cost_usd or 0.0) + float(again.cost_usd or 0.0)
            again.tokens = int(result.tokens or 0) + int(again.tokens or 0)
            self.local.hub_resumes = int(getattr(self.local, "hub_resumes", 0) or 0) + 1
            self.usage(again, root, emit, int(self.local.hub_resumes))
            if not again.met and again.session_id == result.session_id and not again.cancelled:
                return None      # a failed second turn does not undo an accepted first one
            taken["again"] = again
            return again.output or ""

        record = answer_check.run_round(original, str(result.output), ask, resume, allowed=allowed, emit=tell)
        if "again" in taken and record["answer"] != result.output:
            result = taken["again"]
        result.answer_check = record                         # type: ignore[attr-defined]
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
