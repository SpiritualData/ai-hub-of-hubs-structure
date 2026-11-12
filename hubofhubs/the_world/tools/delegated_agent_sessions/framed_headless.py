"""The hub's wrapper for an open-source agent harness run headless: the same preparation and checks the Claude Code arm has, shared by every harness.

Role: an open-source harness (opencode, and any other with a headless mode) brings its own loop, tools and provider support; the hub brings what the loop lacks. ``HubWrapped``
is a mixin for a ``HeadlessCliRunner`` that adds, around the harness's one headless run:

* the hub's frame (``hub_frame.build_frame``: the files that matter in view, the folder map with what is left out and why, the run's rules) written to a private file and handed to
  the harness as its own project or system instructions (``frame_config``, one line per harness);
* the shared ceilings (``run_ceilings.LimitWatch``): spend read from the harness's own event stream while it runs, wall time, a hard limit that stops the process and keeps its session
  resumable, a soft limit after which the hub starts no iteration of its own;
* the hub's code check of written text after the run and, for each finding worth a resumed turn, Goal Completion's stop decision before the hub continues the harness's session
  (``native_runner.worth_resuming`` and ``run_ceilings.stop_aware``, the same pieces the Claude Code arm uses);
* the report of what the run wrote or ran outside the working folder (``native_runner.outside_the_folder``, from the harness's tool calls mapped to Claude Code's names);
* session events for a surface (``solution_loop.Telling``): a run start, a step per tool call, the cost and tokens.

A harness arm adds this by naming the mixin first in its bases and giving ``frame_config`` (how the harness reads project instructions) and ``tool_steps`` (how its event stream shows
tool calls). Standard library and the hub only.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple, Union

from esoi import implementation

from hubofhubs.the_world.tools.deep import DeepResult, ProgressEvent
from hubofhubs.the_world.tools.events import EVENT_STATUS
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import CANCEL_POLL_SECONDS, kill_process_group, log, stop_process_group
from hubofhubs.the_world.tools.delegated_agent_sessions.headless_runner import DEFAULT_TIMEOUT_SECONDS, OpencodeRunner, Parsed, list_price
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import build_frame
from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import CHECK_MESSAGE, outside_the_folder, worth_resuming
from hubofhubs.the_world.tools.delegated_agent_sessions.run_ceilings import (
    DEFAULT_CEILING_SECONDS, DEFAULT_CEILING_USD, MAX_RESUMES, SOFT_FRACTION, LimitWatch, ceiling_of, decision_of, soft_fraction_of, stop_aware)
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import Telling, short, snapshot, track, unsupported

#: what each harness calls its tools, mapped to the names of Claude Code's own (the shapes ``outside_the_folder`` reads)
CANONICAL = {"bash": "Bash", "shell": "Bash", "run_shell_command": "Bash", "write": "Write", "edit": "Edit", "patch": "Edit", "apply_patch": "Edit", "write_file": "Write",
             "replace": "Edit", "multiedit": "MultiEdit"}


class HubWrapped:
    """Mixin for a ``HeadlessCliRunner``: the hub's frame, ceilings, stop decision, code check, outside-folder report and session events around one headless run."""

    plan_tool = "its todo tool"        # what the harness calls its plan tool, named in the frame's rules

    def __init__(self, *args: Any, check: bool = True, notes: str = "", select: Optional[Callable[..., Any]] = None,
                 ceiling_usd: Union[float, str] = DEFAULT_CEILING_USD, ceiling_seconds: Union[float, str] = DEFAULT_CEILING_SECONDS, soft_fraction: float = SOFT_FRACTION,
                 should_continue: Optional[Callable[[Mapping[str, Any]], Any]] = None, stop_inputs: Optional[Mapping[str, Any]] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.check, self.notes, self.select = bool(check), notes, select
        self.ceiling_usd = ceiling_of(ceiling_usd, "ceiling_usd")
        self.ceiling_seconds = ceiling_of(ceiling_seconds, "ceiling_seconds")
        self.soft_fraction = soft_fraction_of(soft_fraction)
        self.should_continue = should_continue or stop_aware(stated=(stop_inputs or {}).get("stated"), policy=(stop_inputs or {}).get("policy"))
        self.local = threading.local()

    # --- the frame, as the harness's own instructions ------------------------------------------------------------------------------------------

    def frame_config(self) -> Dict[str, Any]:
        path = getattr(self.local, "frame_path", "")
        return {"instructions": [path]} if path else {}

    def prepare(self, goal: str, brief: str, preamble: str, root: str) -> None:
        scratch = tempfile.mkdtemp(prefix="hub_frame_")
        os.chmod(scratch, 0o700)
        frame = build_frame(brief or goal, preamble or "", root, select=self.select, notes=self.notes)
        text = frame.text.replace("your task tools (TaskCreate, TaskUpdate)", f"your plan tool ({self.plan_tool})")
        path = os.path.join(scratch, "hub-frame.md")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        self.local.scratch, self.local.frame_path, self.local.frame = scratch, path, frame
        self.local.raws, self.local.live = [], 0.0

    # --- the harness's process, with its spend read while it runs -------------------------------------------------------------------------------

    def spawn(self, argv: List[str], cwd: str, settings: Any) -> Any:
        sink = tempfile.TemporaryFile(mode="w+", encoding="utf-8", errors="replace")
        proc = subprocess.Popen(argv, cwd=cwd, env=self.child_environment(settings), stdin=subprocess.PIPE, stdout=sink, stderr=subprocess.STDOUT, text=True,
                                start_new_session=True)
        proc.hub_sink = sink            # type: ignore[attr-defined]
        return proc

    def spend_of(self, raw: str) -> float:
        got = super().parse(raw)         # type: ignore[misc]
        return float(got.cost_usd or list_price(self.provider, self.model or "", got.tokens_in, got.tokens_out))   # type: ignore[attr-defined]

    def wait(self, proc: Any, stdin_text: Optional[str], cancel_check: Any, started: float) -> Tuple[str, str, str]:
        try:
            if stdin_text:
                proc.stdin.write(stdin_text)
            proc.stdin.close()
        except OSError:
            pass
        settings_cap = self.goal_settings().deep_timeout_seconds                    # type: ignore[attr-defined]
        cap = self.cfg.timeout_seconds or settings_cap or DEFAULT_TIMEOUT_SECONDS      # type: ignore[attr-defined]
        watch: LimitWatch = self.local.watch
        key, ended = f"run-{id(proc)}", "exited"
        while True:
            try:
                proc.wait(timeout=CANCEL_POLL_SECONDS)
                break
            except subprocess.TimeoutExpired:
                pass
            proc.hub_sink.seek(0)
            watch.track(key, self.spend_of(proc.hub_sink.read()))
            proc.hub_sink.seek(0, 2)
            try:
                stop = bool(cancel_check()) if cancel_check is not None else False
            except Exception:  # noqa: BLE001
                stop = False
            if stop or watch.hard_reached():
                stop_process_group(proc, self.cfg.cancel_grace_seconds)        # type: ignore[attr-defined]
                ended = "cancelled"
                break
            if time.monotonic() - started > cap:
                kill_process_group(proc)
                ended = "timeout"
                break
        proc.hub_sink.seek(0)
        text = proc.hub_sink.read()
        proc.hub_sink.close()
        watch.settle(key, self.spend_of(text))
        self.local.raws.append(text)
        lines = [x for x in text.splitlines() if x.strip() and not x.lstrip().startswith("{")]
        return text, "\n".join(lines[-5:]), ended

    # --- the run -----------------------------------------------------------------------------------------------------------------------------

    def run_once(self, goal: str, brief: str, model: Optional[str], context_preamble: Optional[str], working_dir: Optional[str], cancel_check: Any) -> DeepResult:
        root = os.path.abspath(working_dir or self.cfg.working_dir)                   # type: ignore[attr-defined]
        preamble = self.cfg.context_preamble if context_preamble is None else context_preamble     # type: ignore[attr-defined]
        self.prepare(goal, brief, preamble or "", root)
        self.local.goal_text = brief or goal
        before = snapshot(root)
        watch = self.local.watch = LimitWatch(self.ceiling_usd, self.ceiling_seconds, self.soft_fraction, log=log, throttle=0.0)
        watch.__enter__()
        try:
            result = super().run_once(goal, brief, model, context_preamble, working_dir, cancel_check)      # type: ignore[misc]
            result = self.iterate(result, root, before, model, cancel_check)
            result.spend_usd = max(float(result.cost_usd or 0.0), watch.spend())        # type: ignore[attr-defined]
            result.elapsed_seconds = watch.elapsed()                                    # type: ignore[attr-defined]
            result.resume_handle = result.session_id                                    # type: ignore[attr-defined]
            if watch.hard:
                result.end_reason = watch.end_reason()
                result.error = f"The run was stopped at its hard limit ({watch.hard}). Work already finished is kept; resume session {result.session_id} to continue."
            self.report(goal, root, result)
        finally:
            watch.__exit__()
            shutil.rmtree(self.local.scratch, ignore_errors=True)
            self.local.frame_path = ""
        return result

    def resume(self, session_id: str, message: str, model: Optional[str], root: str, cancel_check: Any, started: float) -> Parsed:
        """One continuation of the harness's session with ``message``; an empty ``Parsed`` (with the problem in ``error``) when it cannot be started."""
        settings = self.goal_settings()                                                # type: ignore[attr-defined]
        run_model = (model if model and self.uses_deep_model else None) or self.model  # type: ignore[attr-defined]
        binary = self.binary()                                                         # type: ignore[attr-defined]
        found = binary if os.path.sep in binary else shutil.which(binary, path=self.child_environment(settings).get("PATH"))     # type: ignore[attr-defined]
        argv = self.continue_command(found, session_id, run_model, root, message) if found else None     # type: ignore[attr-defined]
        if not argv:
            return Parsed(error="the harness cannot continue a session")
        launched = self.launch(argv, message, root, settings, cancel_check, started, binary)    # type: ignore[attr-defined]
        if isinstance(launched, DeepResult):
            return Parsed(error=launched.error or "the continuation did not start")
        out, _err, _ended, _code = launched
        return self.parse(out or "")                                                   # type: ignore[attr-defined]

    def iterate(self, result: DeepResult, root: str, before: Any, model: Optional[str], cancel_check: Any) -> DeepResult:
        """The hub's own iteration, which the person did not ask for: after the harness reports, the code check of written text runs, and each continuation it would start is put
        to ``should_continue`` (Goal Completion's stop decision) with plain facts first. A refusal ends the run with its reason in ``end_reason``; nothing else decides."""
        if not (self.check and result.met and result.session_id):
            return result
        watch: LimitWatch = self.local.watch
        resumes, last, rounds, changed_outcome = 0, None, [], None
        while True:
            files: "OrderedDict[str, None]" = OrderedDict()
            track(root, before, files)
            everything = unsupported(root, list(files), goal=str(getattr(self.local, "goal_text", "") or ""))
            found = worth_resuming(root, everything)
            self.local.resumed = resumes > 0
            if last is not None:
                changed_outcome = found != last
            rounds.append(dict(findings=len(found), spend_usd=watch.spend(), elapsed_seconds=watch.elapsed(), changed=len(files) if last is None else int(found != last)))
            last = found
            if not everything:
                return result
            facts = dict(rounds=list(rounds), spend_usd=watch.spend(), turns=0, resumes=resumes, findings=list(found), unchecked_findings=[x for x in everything if x not in found],
                         changed_outcome=changed_outcome, elapsed_seconds=watch.elapsed(), ceiling_usd=self.ceiling_usd, ceiling_seconds=self.ceiling_seconds,
                         ceiling_turns=None, soft_fraction=self.soft_fraction)
            try:
                go, reason = decision_of(self.should_continue(facts))
            except Exception as error:  # noqa: BLE001 -- a failing decision is a refusal to iterate, never a crash
                go, reason = False, f"decision_failed:{type(error).__name__}"
            if go and resumes >= MAX_RESUMES:
                go, reason = False, "resume_cap"
            if go and (watch.softened or watch.soften() or watch.hard_reached()):
                go, reason = False, "ceiling_reached"
            if go and cancel_check is not None and cancel_check():
                go, reason = False, "cancelled"
            if not go:
                result.end_reason = f"resume_stopped:{reason or 'declined'}"
                return result
            more = self.resume(result.session_id, CHECK_MESSAGE + "\n".join(found), model, root, cancel_check, time.monotonic())
            resumes += 1
            if more.error and not more.text.strip():
                return result            # a failed continuation does not undo the accepted first report
            cost = more.cost_usd if more.cost_usd else list_price(self.provider, self.model or "", more.tokens_in, more.tokens_out)     # type: ignore[attr-defined]
            result.output = more.text.strip() or result.output
            result.tokens = int(result.tokens or 0) + more.tokens_in + more.tokens_out
            result.cost_usd = float(result.cost_usd or 0.0) + float(cost or 0.0)

    # --- the account of the run --------------------------------------------------------------------------------------------------------

    def report(self, goal: str, root: str, result: DeepResult) -> None:
        """What the run wrote or ran outside the working folder (``result.outside_folder``, a report only) and the session events for a surface."""
        steps: List[Dict[str, Any]] = []
        for raw in getattr(self.local, "raws", []):
            steps += self.tool_steps(raw)                                              # type: ignore[attr-defined]
        actions = [(CANONICAL.get(s["kind"].lower(), s["kind"]), {"command": s["input"].get("command", ""), "file_path": s["input"].get("filePath") or s["input"].get("file_path")
                                                                   or s["input"].get("path") or ""}) for s in steps if isinstance(s.get("input"), dict)]
        result.outside_folder = outside_the_folder(root, actions, temporary=self.goal_settings().environment().get("TMPDIR", "/tmp"))   # type: ignore[attr-defined]
        emit = getattr(self.local, "emit", None)
        if emit is None:
            return
        tell = Telling(lambda data: emit(ProgressEvent(type="session", data=data)), agent="main")
        tell.send("run-started", goal=short(goal, 200), harness=type(self).__name__, session_id=result.session_id or "", resumed=False)
        for index, step in enumerate(steps, 1):
            tell.step(step["kind"], step["label"], "done" if step["ok"] else "failed", step_id=f"main-step-{index}")
        tell.send("usage", cost_usd=float(result.cost_usd or 0.0) or None, tokens=int(result.tokens or 0) or None, calls=len(steps))
        if result.outside_folder:
            emit(ProgressEvent(type=EVENT_STATUS, text="The session wrote or ran something outside the working folder.", data=dict(phase="outside_folder", items=result.outside_folder)))

    def run_goal(self, *, emit: Any = None, **kwargs: Any) -> DeepResult:
        self.local.emit = emit
        return super().run_goal(emit=emit, **kwargs)                                  # type: ignore[misc]


@implementation("delegated-agent-sessions", "opencode_hub_runner")
class OpencodeHubRunner(HubWrapped, OpencodeRunner):
    """opencode run headless inside the hub's wrapper: its own loop and tools, with the hub's frame as its ``instructions``, the shared ceilings, the code check with the stop
    decision before any iteration the hub starts, the outside-folder report and session events."""

    plan_tool = "todowrite"
