"""The hub's frame on the model's own tool loop, with sub-agents scoped to solutions, the consumer's skills and context in the frame, role tiers inside the run, a step watch and
a frame ordered for the prompt cache.

Role: ``native_tool_loop_runner`` is one lean session; it has no sub-agents (the hub's sub-agents by solution serve its text loop only), no skills or MCP, a frame of the folder's
files alone, one tier for the whole run, only spend and time ceilings while it runs, and a frame whose start changes with the goal. This arm keeps that session, tools, ceilings,
stop decision, code check and outside-folder report and adds, each behind a constructor argument and each a small piece of pure code (``solution_agents``, ``frame_sections``,
``hubofhubs.the_intelligence.nervous_system.step_watch``):

1. sub-agents scoped to solutions and no others: before the session the hub decides in code which solutions the work may delegate to and writes one Claude Code agent per
   solution (``--agents``), each with its own solution's frame, a compact report form, tools that fit it and the model of its role's tier; a hook passed with ``--settings``
   refuses any other agent and any call past ``agent_calls``; after the session the transcript is read for calls outside the list and the agents' session events. Work whose
   folder and goal are small (counts of files, of characters and of the goal, ``solution_agents.wants_agents``) is offered only the review agent (``review_small_work``), for a
   written deliverable; a folder with records of its own is offered an agent for each solution the goal concerns and for the solutions those delegate to; each run's result carries
   ``subagent_report`` (offered, ran per solution, refused);
2. the consumer's skills (``skills_dir``, a folder or a list) as a SKILLS section, and an MCP config file (``mcp_config``) passed through with strict MCP kept on;
3. a KNOWN section: the consumer's ``recall(goal)`` and the earlier investigations of the solutions in scope;
4. the sub-agents' models come from the role tier table (``solution_agent_gather``, ``solution_agent_work``, ``solution_agent_review``), resolved when the run starts;
5. a step watch: a command run a third time unchanged and sub-agent calls past the budget steer the session once each;
6. the frame is ordered for the provider's prompt cache (the same for every goal in the folder first, files in view last).

Claude Code agents cannot start agents, so a solution with children lists them by name and the top session calls a child's agent itself. An arm is this harness with a tier,
``solution_agents_native_runner@provider=anthropic,tier=balanced``; the tier is the main session's, the agents have their roles'.
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
import time
import uuid
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from esoi import implementation

from hubofhubs.the_body.internal_context.run_store.jsonl_ledger import private_directory
from hubofhubs.the_intelligence.nervous_system.step_watch import step_findings
from hubofhubs.the_world.tools.deep import ProgressEvent
from hubofhubs.the_world.tools.events import EVENT_STATUS
from hubofhubs.the_world.tools.delegated_agent_sessions import providers, solution_agents as agents
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
from hubofhubs.the_world.tools.delegated_agent_sessions.control import ControlMessage, RunControl
from hubofhubs.the_world.tools.delegated_agent_sessions.frame_sections import KNOWN_CHARS, known_section, skills_section
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import NATIVE_TOOLS, build_frame, scratch_folder
from hubofhubs.the_world.tools.delegated_agent_sessions.launch import DeepLaunchSettings
from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import NativeToolLoopRunner, SESSION_FOLDER, log
from hubofhubs.the_world.tools.delegated_agent_sessions.run_ceilings import LimitWatch, current_session_file
from hubofhubs.the_world.tools.delegated_agent_sessions.session import find_session_file
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import track
from hubofhubs.the_world.tools.delegated_agent_sessions.adaptive_native_runner import folder_facts

STEP_POLL_SECONDS = 2.0     # how often a running session's steps are looked at
MAX_STEERS = 3              # the most steering messages the step watch sends in one run


def actions_in(path: Optional[str]) -> List[Tuple[str, Any]]:
    """``[(tool name, tool input)]`` of a session record, in order (empty when it cannot be read)."""
    out: List[Tuple[str, Any]] = []
    try:
        with open(path or "", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                content = (event.get("message") or {}).get("content") if event.get("type") == "assistant" else None
                out += [(str(b.get("name") or ""), b.get("input") or {}) for b in content or [] if isinstance(b, dict) and b.get("type") == "tool_use"] if isinstance(content, list) else []
    except OSError:
        return []
    return out


class StepWatch(LimitWatch):
    """The ceilings of ``LimitWatch`` and, with them, a look at the session's own steps: a command run a third time unchanged and sub-agent calls past the budget each steer the
    session once (``step_findings``), at most ``MAX_STEERS`` times in the run. ``actions_of`` gives the tool calls so far (default: the running session's record in ``root``)."""

    def __init__(self, *args: Any, budget: int = agents.DEFAULT_AGENT_CALLS, actions_of: Optional[Callable[[], Sequence[Tuple[str, Any]]]] = None,
                 root: str = "", config_dir: Optional[str] = None, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.budget, self.actions_of, self.root, self.config_dir = int(budget), actions_of, root, config_dir
        self.reported: set = set()
        self.looked_at = 0.0

    def actions(self) -> Sequence[Tuple[str, Any]]:
        if self.actions_of is not None:
            return self.actions_of()
        return actions_in(current_session_file(self.root, self.started, self.config_dir))

    def steering(self) -> List[ControlMessage]:
        """The messages the steps call for, each finding once and no more than ``MAX_STEERS`` in all."""
        now = time.monotonic()
        if now - self.looked_at < STEP_POLL_SECONDS or len(self.reported) >= MAX_STEERS:
            return []
        self.looked_at = now
        try:
            found = step_findings(self.actions(), agent_budget=self.budget, reported=self.reported)
        except Exception:  # noqa: BLE001 -- a watch that fails never stops the run
            return []
        out: List[ControlMessage] = []
        for key, message in found[:max(MAX_STEERS - len(self.reported), 0)]:
            self.reported.add(key)
            out.append(ControlMessage(id="hub-step-" + uuid.uuid4().hex[:8], text=message))
            if self.log is not None:
                self.log.info("step watch steers the session once: %s", key.split(":", 1)[0])
        return out

    def wrap(self, control: Optional[RunControl], poll_seconds: float = 1.0) -> Optional[RunControl]:
        base = super().wrap(control, poll_seconds) or control or RunControl()

        def claim() -> List[ControlMessage]:
            return list(base.claim_inputs() or []) + self.steering()

        return RunControl(claim_inputs=claim, mark_seen=base.mark_seen, cancel_requested=base.cancel_requested, pause_requested=base.pause_requested,
                          poll_seconds=min(float(base.poll_seconds), poll_seconds), label=base.label)


@implementation("delegated-agent-sessions", "solution_agents_native_runner")
class SolutionAgentsNativeRunner(NativeToolLoopRunner):
    """One hub-framed session on the model's own tool loop with solution agents, skills, known context, a step watch and a cache-ordered frame."""

    def __init__(self, config: Optional[SubprocessConfig] = None, *, solutions: Any = None, agent_calls: int = agents.DEFAULT_AGENT_CALLS,
                 skills_dir: Union[None, str, Sequence[str]] = None, mcp_config: Optional[str] = None, recall: Optional[Callable[[str], str]] = None,
                 known_chars: int = KNOWN_CHARS, records: Any = None, hub: Any = None, review_small_work: bool = True, **kwargs: Any):
        super().__init__(config, **kwargs)
        self.review_small_work = bool(review_small_work)   # work too small for the full offer is still offered the one review agent, for a written deliverable
        self.solutions = solutions                 # a list of solution ids or specs, or a ``(goal, root)`` callable: the solutions the work may delegate to
        self.agent_calls = int(agent_calls)        # the sub-agent calls the whole run may make (0: none are offered)
        self.skills_dir = skills_dir
        self.recall, self.known_chars = recall, int(known_chars)
        self.records, self.hub = records, hub      # the working folder's records and the hub's own, a root or a network (default: found beside the folder and the package)
        if mcp_config:
            self.cfg = dataclasses.replace(self.cfg, mcp_config_path=mcp_config)     # strict MCP stays on: only this file's servers

    def model_of(self, tier: str) -> Optional[str]:
        """The model of a role's tier for this run's provider, as the CLI takes it; None when no model is chosen for it."""
        return self.cli_safe(providers.model_for(self.provider, tier))

    def prepare(self, goal: str, brief: str, preamble: str, root: str, session_key: str) -> None:
        folder = self.session_dir or private_directory(SESSION_FOLDER) or ""
        scratch = scratch_folder(folder, session_key)
        self.local.scratch = scratch
        self.local.frame_file = None
        self.local.sandboxed = False
        self.local.launcher = self.write_launcher(folder_for_launcher=scratch, root=root)
        text = brief or goal
        self.local.tools = NATIVE_TOOLS
        self.local.agents_file = self.local.settings_file = None
        self.local.solution_of = {}
        self.local.review_agent = ""
        self.local.review_stakes = {}
        scope: List[str] = []
        extras: List[str] = []
        specs: List[agents.SolutionSpec] = []
        large = scratch and self.agent_calls > 0 and agents.wants_agents(folder_facts(root, text))
        small = scratch and self.agent_calls > 0 and self.review_small_work and not large
        if large or small:
            specs, net = agents.choose_solutions(text, root, self.solutions, records=self.records, hub=self.hub) if large else agents.review_only(self.hub)
            defined = agents.agent_definitions(specs, net, self.model_of, goal=text) if specs else {}
            budget = self.agent_calls if large else min(self.agent_calls, agents.REVIEW_ONLY_CALLS)
            if defined and self.write_guard(scratch, defined, budget):
                self.local.tools = tuple(NATIVE_TOOLS) + (agents.AGENT_TOOL,)
                self.local.solution_of = {agents.agent_name(s.solution): s.solution for s in specs if agents.agent_name(s.solution) in defined}
                review = agents.review_agent(specs, defined)
                self.local.review_agent = review
                extras.append(agents.agents_note(budget, review) if large else agents.review_only_note(review, budget))
            scope = [s.solution for s in specs] if large else []
        skills = skills_section(self.skills_dir)
        if skills:
            extras.append(skills)
        known = known_section(text, recall=self.recall, solutions=scope, chars=self.known_chars)
        frame = build_frame(text, preamble or "", root, select=self.select, notes=self.notes, stable=True, extras=extras, known=known)
        if scratch:
            path = os.path.join(scratch, "hub-frame.md")
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(frame.text)
                self.local.frame_file = self.visible(path)
            except OSError as error:
                log.warning("hub frame not written (%s): the session runs without it", error)

    def visible(self, path: str) -> str:
        """The path as the session sees it: the sandbox shows the session's folder as /tmp."""
        return "/tmp/" + os.path.basename(path) if self.local.sandboxed else path

    def write_guard(self, scratch: str, defined: Dict[str, Dict[str, Any]], budget: Optional[int] = None) -> bool:
        """Write the agents file, the guard and its settings into the session's private folder; True when all are written. The agents are offered only with the guard in place.
        ``budget`` is the calls the guard allows (default ``agent_calls``)."""
        budget = self.agent_calls if budget is None else int(budget)
        names = os.path.join(scratch, "solution-agents.json"), os.path.join(scratch, "agent-guard.py"), os.path.join(scratch, "agent-guard.json")
        counter, record = os.path.join(scratch, "agent-calls.count"), os.path.join(scratch, "agent-calls.log")
        python = "python3" if self.local.sandboxed else (sys.executable or "python3")
        try:
            with open(names[0], "w", encoding="utf-8") as handle:
                json.dump(defined, handle, indent=1, sort_keys=True)
            with open(names[1], "w", encoding="utf-8") as handle:
                handle.write(agents.guard_script(sorted(defined), budget, self.visible(counter), self.visible(record)))
            with open(names[2], "w", encoding="utf-8") as handle:
                json.dump(agents.guard_settings(python, self.visible(names[1])), handle, indent=1)
            if not os.path.exists(counter):
                with open(counter, "w", encoding="utf-8") as handle:
                    handle.write("0")
        except OSError as error:
            log.warning("the sub-agent guard is not written (%s): the session runs with no sub-agents", error)
            return False
        self.local.agents_file, self.local.settings_file = self.visible(names[0]), self.visible(names[2])
        return True

    def launch_settings(self) -> DeepLaunchSettings:
        base = super().launch_settings()
        tools = getattr(self.local, "tools", None)
        return dataclasses.replace(base, tools=tuple(tools) if tools else base.tools, agents_file=getattr(self.local, "agents_file", None),
                                   settings_file=getattr(self.local, "settings_file", None))

    def new_watch(self, root: str, emit: Any) -> LimitWatch:
        return StepWatch(self.ceiling_usd, self.ceiling_seconds, self.soft_fraction, spend_of=lambda: self.spend_now(root), emit=emit, log=log, throttle=0.0,
                         budget=self.agent_calls, root=root, config_dir=getattr(self.goal_settings(), "claude_config_dir", None))

    def iterate(self, result: Any, root: str, before: Any, common: Dict[str, Any], emit: Any, cancel_check: Any) -> Any:
        result = super().iterate(result, root, before, common, emit, cancel_check)
        return self.ask_review(result, root, before, common, emit, cancel_check)

    def session_calls(self, result: Any, root: str) -> List[Dict[str, Any]]:
        """The Agent calls of the session so far, read from its record (empty when it cannot be read)."""
        try:
            found = find_session_file(result.session_id, root, getattr(self.goal_settings(), "claude_config_dir", None)) if result.session_id else None
            with open(found, encoding="utf-8", errors="replace") as handle:
                return agents.agent_calls_in(handle)
        except (OSError, TypeError):
            return []

    def ask_review(self, result: Any, root: str, before: Any, common: Dict[str, Any], emit: Any, cancel_check: Any) -> Any:
        """After the session (and the code check) reported: when the deliverable it wrote has the stakes ``agents.review_wanted`` names, the same session is resumed once with the
        request to hand it to the review agent, in the foreground, with the person's own goal. Not asked when the session already ran the review, when the run's ceilings are
        reached, or when there is no review agent. The stakes are on ``result.review_stakes``."""
        agent = getattr(self.local, "review_agent", "")
        if not (agent and result.met and result.session_id):
            return result
        files: "OrderedDict[str, None]" = OrderedDict()
        track(root, before, files)
        goal = str(getattr(self.local, "goal_text", "") or "")
        stakes = agents.review_stakes(root, list(files), goal)
        result.review_stakes = {k: v for k, v in stakes.items() if k != "paths"}         # type: ignore[attr-defined]
        if not agents.review_wanted(stakes):
            return result
        if any(c.get("agent") == agent and not c.get("failed") for c in self.session_calls(result, root)):
            return result                                                              # the session reviewed it already
        watch = getattr(self.local, "watch", None)
        if watch is not None and (getattr(watch, "softened", False) or watch.hard_reached()):
            return result
        if cancel_check is not None and cancel_check():
            return result
        message = agents.review_request(agent, stakes["paths"], goal)
        again = super(NativeToolLoopRunner, self).run_goal_once(goal=message, brief=message, context_preamble="", resume_session_id=result.session_id, **common)
        if again.session_id == result.session_id:        # the CLI's cost is the session's running total, sub-agents included: the resumed report already holds the earlier turns
            again.cost_usd = max(float(result.cost_usd or 0.0), float(again.cost_usd or 0.0))
        else:
            again.cost_usd = float(result.cost_usd or 0.0) + float(again.cost_usd or 0.0)
        again.tokens = int(result.tokens or 0) + int(again.tokens or 0)
        self.usage(again, root, emit, 1)
        again.review_stakes = result.review_stakes                                       # type: ignore[attr-defined]
        if not again.met and again.session_id == result.session_id and not again.cancelled:
            return result                                                              # a failed review turn does not undo an accepted report
        return again

    def flag_outside(self, result: Any, root: str, emit: Any) -> None:
        super().flag_outside(result, root, emit)
        self.report_agents(result, root, emit)

    def report_agents(self, result: Any, root: str, emit: Any) -> None:
        """After the session: ``result.agent_findings`` (agent calls outside the list) and ``result.solution_agent_events`` (``agent-started`` and ``agent-ended`` dicts per solution
        agent call), also emitted as status events so a consumer can show the tree. Nothing is read for a run that was offered no agents."""
        solution_of = getattr(self.local, "solution_of", None) or {}
        result.agent_findings, result.solution_agent_events = [], []        # type: ignore[attr-defined]
        result.turns = int(getattr(self.local, "used_turns", 0) or 0)          # the assistant turns of the session record, counted by ``usage``
        result.subagent_calls = 0
        result.subagent_report = agents.agent_report([], solution_of)         # type: ignore[attr-defined]
        if not solution_of:
            return
        try:
            found = find_session_file(result.session_id, root, getattr(self.goal_settings(), "claude_config_dir", None)) if result.session_id else None
            with open(found, encoding="utf-8", errors="replace") as handle:
                calls = agents.agent_calls_in(handle)
        except (OSError, TypeError):
            return
        result.subagent_calls = sum(1 for c in calls if c.get("agent") in solution_of and not c.get("failed"))      # the calls that ran; a refused one did no work
        result.subagent_report = agents.agent_report(calls, solution_of)                 # type: ignore[attr-defined]
        result.agent_findings = agents.outside_the_list(calls, solution_of)            # type: ignore[attr-defined]
        result.solution_agent_events = agents.session_events(calls, solution_of)         # type: ignore[attr-defined]
        if emit is None:
            return
        try:
            for event in result.solution_agent_events:                                   # type: ignore[attr-defined]
                emit(ProgressEvent(type=EVENT_STATUS, text=f"{event['type']}: {event.get('solution') or event['agent_id']}", data=dict(phase="solution_agent", event=event)))
            if result.agent_findings:                                                    # type: ignore[attr-defined]
                emit(ProgressEvent(type=EVENT_STATUS, text="The session called an agent outside the solution agents.", data=dict(phase="agent_outside_list", items=result.agent_findings)))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 -- a sink that fails never stops the run
            pass
