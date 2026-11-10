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

import dataclasses
import os
import threading
import uuid
from collections import OrderedDict
from typing import Any, Callable, Dict, Optional

from esoi import implementation

from hubofhubs.the_body.internal_context.run_store.jsonl_ledger import private_directory
from hubofhubs.the_world.tools.deep import DeepResult
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig, log
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import NATIVE_TOOLS, build_frame, scratch_folder
from hubofhubs.the_world.tools.delegated_agent_sessions.launch import DeepLaunchSettings
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import snapshot, track, unsupported
from hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner import StreamJsonGoalRunner
from hubofhubs.the_self.assembler import arm_needs as needs

SESSION_FOLDER = "native-loop-sessions"
CHECK_MESSAGE = ("A code check of the files you wrote found these. It only reads the text files of the folder, so a figure you computed or read from a database, "
                 "a command's output or a web page is not a finding: keep it and say in the file where it came from. Remove or correct a figure only when you cannot "
                 "account for it, and name only files that exist. Then report again.\n")


@implementation("delegated-agent-sessions", "native_tool_loop_runner")
class NativeToolLoopRunner(StreamJsonGoalRunner):
    """One hub-framed session on the model's own tool loop (Claude Code lean), with the hub's code check after it."""

    REQUIRES = (needs.CLAUDE_BINARY, needs.CLAUDE_ACCOUNT, needs.CLAUDE_CLI_BOUNDARY, needs.WRITE_ROOT)
    PROVIDERS = ("anthropic",)
    PAID = True              # every run calls a model: never run by a free (offline) metric run
    config_class = SubprocessConfig
    on_trial = True          # measured and ranked beside the other harnesses, not chosen for a consumer until the owner promotes it
    tools = NATIVE_TOOLS

    def __init__(self, config: Optional[SubprocessConfig] = None, *, check: bool = True, session_dir: Optional[str] = None,
                 select: Optional[Callable[..., Any]] = None, notes: str = "", **kwargs: Any):
        super().__init__(config, **kwargs)
        self.check = bool(check)               # the hub's code check of written text after the session
        self.session_dir = session_dir
        self.select = select
        self.notes = notes                     # the consumer's standing text for the frame (where its skills live, its conventions)
        self.local = threading.local()         # per call: the frame file and the temporary folder of the run in this thread

    # --- launch -----------------------------------------------------------------------------------------------------------------

    def launch_settings(self) -> DeepLaunchSettings:
        base = super().launch_settings()
        return dataclasses.replace(
            base, tools=base.tools if base.tools is not None else tuple(self.tools),
            setting_sources="" if base.setting_sources is None else base.setting_sources, strict_mcp=True, exclude_dynamic_sections=True,
            append_system_prompt_file=getattr(self.local, "frame_file", None) or base.append_system_prompt_file)

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
        frame = build_frame(brief or goal, preamble or "", root, select=self.select, notes=self.notes)
        if scratch:
            path = os.path.join(scratch, "hub-frame.md")
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(frame.text)
                self.local.frame_file = path
            except OSError as error:
                log.warning("hub frame not written (%s): the session runs without it", error)

    def run_goal_once(self, *, goal: str, brief: str, model: Optional[str] = None, max_turns: Optional[int] = None,  # type: ignore[override]
                      emit: Any = None, context_preamble: Optional[str] = None, run_id: Optional[str] = None, working_dir: Optional[str] = None,
                      resume_session_id: Optional[str] = None, prompt_budget_tokens: Optional[int] = None, requester_user_id: Optional[str] = None,
                      cancel_check: Any = None, control: Any = None) -> DeepResult:
        root = os.path.abspath(self.cfg.working_dir if working_dir is None else working_dir)
        preamble = self.cfg.context_preamble if context_preamble is None else context_preamble
        key = resume_session_id or run_id or uuid.uuid4().hex
        self.prepare(goal, brief, preamble, root, key)
        before = snapshot(root)
        common = dict(model=model, max_turns=max_turns, emit=emit, run_id=run_id, working_dir=working_dir, prompt_budget_tokens=prompt_budget_tokens,
                      requester_user_id=requester_user_id, cancel_check=cancel_check, control=control)
        result = super().run_goal_once(goal=goal, brief=brief, context_preamble=context_preamble, resume_session_id=resume_session_id, **common)
        if not (self.check and result.met and result.session_id):
            return result
        changed: "OrderedDict[str, None]" = OrderedDict()
        track(root, before, changed)
        found = unsupported(root, list(changed))
        if not found:
            return result
        log.info("native loop: the code check found %d things; resuming the session once", len(found))
        message = CHECK_MESSAGE + "\n".join(found)
        again = super().run_goal_once(goal=message, brief=message, context_preamble="", resume_session_id=result.session_id, **common)
        again.cost_usd = float(result.cost_usd or 0.0) + float(again.cost_usd or 0.0)
        again.tokens = int(result.tokens or 0) + int(again.tokens or 0)
        if not again.met and again.session_id == result.session_id and not again.cancelled:
            return result      # a failed second turn does not undo an accepted first one
        return again
