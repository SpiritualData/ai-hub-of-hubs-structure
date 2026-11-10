"""Agent harnesses other than Claude Code, run headless behind the same runner contract: Codex CLI and opencode.

Each is a ``DeepRunner``: it takes a goal and a brief, runs the harness's own non-interactive JSON mode once in the working folder,
reads its event stream for the final message, tokens and cost, and returns a ``DeepResult`` (met when the harness exited cleanly with
a final message, never raising). An instance is one arm: a harness, the provider it drives and a tier, whose model comes from the
hub's tier chooser (``providers.model_for``). The prompt is the same one the Claude Code runners send (``compose_goal_prompt``), with the
working folder named, since these harnesses do not assume their working directory holds the files the task names.

Every deployment value comes from ``SubprocessConfig`` (working folder, wall-clock cap, permission policy, extra PATH folders) and
``GoalSettings`` (the child environment, the escalation marker, the standing instructions). Nothing here reads ``os.environ``.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional

from esoi import implementation

from hubofhubs.the_world.tools.deep import DeepResult, DeepRunnerBase, LAUNCH_MISSING_PROGRAM, LAUNCH_PERMISSION_DENIED
from hubofhubs.the_world.tools.delegated_agent_sessions import providers
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import (
    CANCEL_POLL_SECONDS, SubprocessConfig, compose_goal_prompt, extract_escalation_id, kill_process_group, log, stop_process_group)
from hubofhubs.the_world.tools.delegated_agent_sessions.settings import (
    GoalSettings, GoalSettingsSource, resolve_goal_settings, with_instructions_pack)
from hubofhubs.the_self.assembler import arm_needs as needs

DEFAULT_TIER = "fast"
DEFAULT_TIMEOUT_SECONDS = 1800.0   # a run with no configured cap still ends; the Claude Code runners have a liveness review instead
ARGUMENT_LIMIT = 100_000           # longer prompts go in a file: one argument may not exceed 128 KiB on Linux
CONTINUE_MESSAGE = ("You stopped before writing your final report. Finish the task above using your tools, then write the final report: "
                    "what you found or changed, concretely.")


@dataclass
class Parsed:
    """What a harness's event stream says about one run."""
    text: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Optional[float] = None   # the harness's own figure, when it reports one
    session_id: Optional[str] = None
    error: str = ""


def json_lines(raw: str) -> Iterable[Dict[str, Any]]:
    """Every line of ``raw`` that is a JSON object; other lines (warnings a harness prints) are skipped."""
    for line in (raw or "").splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                yield event


def list_price(provider: str, model: str, tokens_in: int, tokens_out: int) -> float:
    """The list price of the tokens from the hub's price table, 0.0 when the model is not priced."""
    from hubofhubs.the_world.learning.research_freshness_reader import registry
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import tiers
    got = tiers.list_cost(registry.read("tier_prices.csv"), providers.normalise(provider), model, tokens_in, tokens_out)
    return float(got or 0.0)


class HeadlessCliRunner(DeepRunnerBase):
    """One arm of a headless agent harness. Subclasses say how to call it (``command``) and how to read its events (``parse``)."""

    PROVIDERS: Any = ()
    PAID = True   # every run calls a model through the harness: never run by a free (offline) metric run
    binary_name = ""
    config_class = SubprocessConfig

    def __init__(self, config: Optional[SubprocessConfig] = None, *, root: str = "", provider: str = "", tier: str = DEFAULT_TIER,
                 settings: Optional[GoalSettingsSource] = None, model_for: Optional[Callable[[str, str], Optional[str]]] = None,
                 instructions: str = ""):
        if config is None:
            if not root:
                raise ValueError("no config: pass config=, or root=, the one folder the harness runs in")
            config = SubprocessConfig(working_dir=root, claude_path="")
        declared = providers.providers_of(type(self))
        self.provider = providers.normalise(provider) or (declared[0] if declared and declared[0] != providers.ANY else "")
        if not self.provider or not providers.drives(type(self), self.provider):
            raise ValueError(f"{type(self).__name__} cannot drive the provider {provider!r} (it drives {', '.join(declared) or 'none'})")
        self.cfg = config
        self.tier = tier or DEFAULT_TIER
        self.settings_source = settings
        self.instructions = instructions   # the instructions pack this arm adds to every run, "" for none
        self.model = (model_for or providers.model_for)(self.provider, self.tier)
        # The deep-model ladder names Claude models; a harness on another provider runs its own tier's model, so a goal loop must not
        # announce or climb that ladder for it.
        self.uses_deep_model = self.provider == "anthropic"

    # --- what a subclass provides ------------------------------------------------------------------------------------------------

    def command(self, binary: str, prompt: str, model: str, working_dir: str, prompt_file: Optional[str]) -> List[str]:
        raise NotImplementedError

    def parse(self, raw: str) -> Parsed:
        raise NotImplementedError

    def harness_environment(self, env: Dict[str, str]) -> Dict[str, str]:
        """Changes to the child environment this harness needs (the names its provider SDK reads); ``env`` is changed and returned."""
        return env

    # --- shared --------------------------------------------------------------------------------------------------------------------

    def goal_settings(self) -> GoalSettings:
        return resolve_goal_settings(self.settings_source)

    def binary(self) -> str:
        configured = (self.cfg.claude_path or "").strip()
        return configured if configured and os.path.basename(configured) != "claude" else self.binary_name

    def child_environment(self, settings: GoalSettings) -> Dict[str, str]:
        env = dict(settings.environment())
        if self.cfg.extra_path_dirs:
            env["PATH"] = os.pathsep.join(list(self.cfg.extra_path_dirs) + [env.get("PATH", "")])
        return self.harness_environment(env)

    def prompt_for(self, goal: str, brief: str, preamble: str, working_dir: str, settings: GoalSettings) -> str:
        body = compose_goal_prompt(goal, brief, preamble=preamble, model=self.model, settings=with_instructions_pack(settings, self.instructions))
        return (f"WORKING FOLDER: {working_dir}\nEvery file the task names is in this folder; read and write files by their path "
                f"relative to it, and stay inside it. Nobody answers questions during this run: use your tools to list and read what "
                f"you need, then finish with your report.\n\n{body}")

    def run_goal(self, *, goal: str, brief: str, model: Optional[str] = None, max_turns: Optional[int] = None,
                 emit: Optional[Callable[..., None]] = None, context_preamble: Optional[str] = None, run_id: Optional[str] = None,
                 working_dir: Optional[str] = None, cancel_check: Optional[Callable[[], bool]] = None, **ignored: Any) -> DeepResult:
        """Run the goal once. ``model`` is used only when this arm drives the provider the deep-model ladder names; otherwise the arm's
        own tier model runs. ``max_turns`` is not a flag these harnesses take; the wall-clock cap bounds the run. Never raises."""
        try:
            return self.run_once(goal, brief, model, context_preamble, working_dir, cancel_check)
        except Exception as e:  # noqa: BLE001 -- the DeepRunner port never raises
            log.error("%s failed unexpectedly: %s: %s", type(self).__name__, type(e).__name__, e, exc_info=True)
            return DeepResult(met=False, error=f"The deep worker failed unexpectedly: {type(e).__name__}: {e}")

    def run_once(self, goal, brief, model, context_preamble, working_dir, cancel_check) -> DeepResult:
        settings = self.goal_settings()
        run_model = (model if model and self.uses_deep_model else None) or self.model
        if not run_model:
            return DeepResult(met=False, launch_failed=True,
                              error=f"no {self.tier} model is chosen for the provider {self.provider} in the tier registry")
        cwd = os.path.abspath(working_dir or self.cfg.working_dir)
        preamble = self.cfg.context_preamble if context_preamble is None else context_preamble
        prompt = self.prompt_for(goal, brief, preamble or "", cwd, settings)
        binary = self.binary()
        found = binary if os.path.sep in binary else shutil.which(binary, path=self.child_environment(settings).get("PATH"))
        if not found:
            return DeepResult(met=False, launch_failed=True, launch_problem=LAUNCH_MISSING_PROGRAM,
                              error=f"the {binary!r} program is not installed or not on the PATH")
        started = time.monotonic()
        with tempfile.TemporaryDirectory(prefix="harness_prompt_") as spare:
            prompt_file = None
            if len(prompt) > ARGUMENT_LIMIT:
                prompt_file = os.path.join(spare, "task.md")
                with open(prompt_file, "w", encoding="utf-8") as handle:
                    handle.write(prompt)
            argv = self.command(found, prompt, run_model, cwd, prompt_file)
            launched = self.launch(argv, prompt, cwd, settings, cancel_check, started, binary)
        if isinstance(launched, DeepResult):
            return launched
        out, err, ended, returncode = launched
        parsed = self.parse(out or "")
        # A weak model can end its turn on a tool call with no report. One continuation of the same session asks for the report, so
        # the work it already did is kept; a harness with no way to continue a session leaves the result as it is.
        nudge = self.continue_command(found, parsed.session_id, run_model, cwd) if (
            ended == "exited" and returncode == 0 and not parsed.error and not parsed.text.strip() and parsed.session_id) else None
        if nudge:
            again = self.launch(nudge, CONTINUE_MESSAGE, cwd, settings, cancel_check, started, binary)
            if not isinstance(again, DeepResult):
                out2, err, ended, returncode = again
                more = self.parse(out2 or "")
                parsed = Parsed(text=more.text, tokens_in=parsed.tokens_in + more.tokens_in, tokens_out=parsed.tokens_out + more.tokens_out,
                                cost_usd=(parsed.cost_usd or 0.0) + (more.cost_usd or 0.0) if (parsed.cost_usd or more.cost_usd) else None,
                                session_id=more.session_id or parsed.session_id, error=more.error)
        proc_returncode = returncode
        tokens = parsed.tokens_in + parsed.tokens_out
        cost = parsed.cost_usd if parsed.cost_usd else list_price(self.provider, run_model, parsed.tokens_in, parsed.tokens_out)
        text = parsed.text.strip()
        common = dict(output=text, tokens=tokens, cost_usd=cost, session_id=parsed.session_id, resolved_model=run_model)
        if ended == "cancelled":
            return DeepResult(met=False, cancelled=True, error="The run was stopped on request.", **common)
        if ended == "timeout":
            return DeepResult(met=False, error="The run passed its time limit and was stopped.", **common)
        problem = parsed.error or ("" if proc_returncode == 0 else ((err or "").strip().splitlines() or [f"exit {proc_returncode}"])[-1])
        if problem and tokens == 0 and not text:
            return DeepResult(met=False, launch_failed=True, error=f"The harness did not start the work: {problem}"[:500], **common)
        decision_id = extract_escalation_id(text, settings.escalation_marker)
        if decision_id:
            return DeepResult(met=False, decision_id=decision_id, **common)
        if problem:
            return DeepResult(met=False, error=problem[:500], **common)
        if not text:
            return DeepResult(met=False, error="The harness ended without a final message.", **common)
        return DeepResult(met=True, **common)

    def continue_command(self, binary: str, session_id: str, model: str, working_dir: str, message: str = CONTINUE_MESSAGE) -> Optional[List[str]]:
        """The command that continues session ``session_id`` with one more message (``message``, or read from stdin when it ends with ``-``), or
        None when the harness cannot continue a session headless."""
        return None

    def frame_config(self) -> Dict[str, Any]:
        """The harness's own configuration that carries the hub's frame as its project instructions (a wrapper arm overrides this); empty for a bare arm."""
        return {}

    def tool_steps(self, raw: str) -> List[Dict[str, Any]]:
        """The tool calls an event stream shows, as ``{"kind", "label", "ok"}`` (empty when the harness's stream is not read for them)."""
        return []

    def spawn(self, argv: List[str], cwd: str, settings: GoalSettings) -> Any:
        """Start one harness process."""
        return subprocess.Popen(argv, cwd=cwd, env=self.child_environment(settings), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)

    def launch(self, argv, prompt, cwd, settings, cancel_check, started, binary):
        """Run one harness command: ``(stdout, stderr, how it ended, exit code)``, or a ``DeepResult`` when it could not start."""
        stdin_text = prompt if argv and argv[-1] == "-" else None
        try:
            proc = self.spawn(argv, cwd, settings)
        except FileNotFoundError:
            return DeepResult(met=False, launch_failed=True, launch_problem=LAUNCH_MISSING_PROGRAM,
                              error=f"the {binary!r} program is not installed or not on the PATH")
        except PermissionError:
            return DeepResult(met=False, launch_failed=True, launch_problem=LAUNCH_PERMISSION_DENIED,
                              error=f"the {binary!r} program cannot be run (permission denied)")
        out, err, ended = self.wait(proc, stdin_text, cancel_check, started)
        return out, err, ended, proc.returncode

    def wait(self, proc, stdin_text, cancel_check, started):
        """``(stdout, stderr, how it ended)``: ``exited``, ``timeout`` or ``cancelled``."""
        cap = self.cfg.timeout_seconds if self.cfg.timeout_seconds else (self.goal_settings().deep_timeout_seconds or DEFAULT_TIMEOUT_SECONDS)
        pending = stdin_text if stdin_text is not None else ""
        while True:
            try:
                out, err = proc.communicate(input=pending, timeout=CANCEL_POLL_SECONDS)
                return out, err, "exited"
            except subprocess.TimeoutExpired:
                pending = None
            if cancel_check is not None:
                try:
                    stop = bool(cancel_check())
                except Exception:  # noqa: BLE001
                    stop = False
                if stop:
                    stop_process_group(proc, self.cfg.cancel_grace_seconds)
                    out, err = proc.communicate()
                    return out, err, "cancelled"
            if time.monotonic() - started > cap:
                kill_process_group(proc)
                out, err = proc.communicate()
                return out, err, "timeout"


@implementation("delegated-agent-sessions", "codex_cli_runner")
class CodexCliRunner(HeadlessCliRunner):
    """Codex CLI (``codex exec --json``): OpenAI's terminal agent, run once per goal with the prompt on stdin."""

    REQUIRES = (needs.CODEX_BINARY, needs.OPENAI_API, needs.OPENAI_KEY, needs.OPENAI_NETWORK, needs.CLAUDE_CLI_BOUNDARY, needs.WRITE_ROOT)
    PROVIDERS = ("openai",)
    binary_name = "codex"

    def command(self, binary, prompt, model, working_dir, prompt_file):
        policy = ["--dangerously-bypass-approvals-and-sandbox"] if self.cfg.skip_permissions else ["--sandbox", "workspace-write"]
        return [binary, "exec", "--json", "--skip-git-repo-check", *policy, "-C", working_dir, "-m", model, "-"]

    def continue_command(self, binary, session_id, model, working_dir, message=CONTINUE_MESSAGE):
        policy = ["--dangerously-bypass-approvals-and-sandbox"] if self.cfg.skip_permissions else ["--sandbox", "workspace-write"]
        return [binary, "exec", "resume", "--json", "--skip-git-repo-check", *policy, "-m", model, session_id, "-"]

    def parse(self, raw):
        got = Parsed()
        for event in json_lines(raw):
            kind = event.get("type", "")
            if kind == "thread.started":
                got.session_id = event.get("thread_id") or got.session_id
            elif kind == "item.completed" and (event.get("item") or {}).get("type") == "agent_message":
                got.text = str(event["item"].get("text") or "")   # the last agent message is the report
            elif kind == "turn.completed":
                usage = event.get("usage") or {}
                got.tokens_in += int(usage.get("input_tokens") or 0)
                got.tokens_out += int(usage.get("output_tokens") or 0)
            elif kind in ("turn.failed", "error"):
                got.error = str((event.get("error") or {}).get("message") or event.get("message") or kind)
        return got


#: the provider id opencode uses for each registry provider name
OPENCODE_PROVIDER = {"gemini": "google"}

#: what opencode may do without asking: edits and commands inside the folder; anything outside it still asks, and a headless run refuses
OPENCODE_PERMISSIONS = json.dumps({"permission": {"edit": "allow", "bash": "allow", "webfetch": "allow"}})


@implementation("delegated-agent-sessions", "opencode_runner")
class OpencodeRunner(HeadlessCliRunner):
    """opencode (``opencode run --format json``): an open agent harness that drives any provider it holds a key for."""

    REQUIRES = (needs.OPENCODE_BINARY, needs.HARNESS_PROVIDER_KEY, needs.CLAUDE_CLI_BOUNDARY, needs.WRITE_ROOT)
    PROVIDERS = providers.ANY
    binary_name = "opencode"

    def command(self, binary, prompt, model, working_dir, prompt_file):
        target = f"{OPENCODE_PROVIDER.get(self.provider, self.provider)}/{model}"
        message = ["-f", prompt_file, "--", "Carry out the task in the attached file."] if prompt_file else ["--", prompt]
        return [binary, "run", "--format", "json", "--dir", working_dir, "-m", target, *message]

    def continue_command(self, binary, session_id, model, working_dir, message=CONTINUE_MESSAGE):
        target = f"{OPENCODE_PROVIDER.get(self.provider, self.provider)}/{model}"
        return [binary, "run", "--format", "json", "--dir", working_dir, "-m", target, "--session", session_id, "--", message]

    def harness_environment(self, env):
        config: Dict[str, Any] = json.loads(OPENCODE_PERMISSIONS) if self.cfg.skip_permissions else {}
        config.update(self.frame_config())      # a wrapper arm adds the hub's frame as opencode's own ``instructions``
        if config:
            env.setdefault("OPENCODE_CONFIG_CONTENT", json.dumps(config))
        if self.provider == "gemini" and not env.get("GOOGLE_GENERATIVE_AI_API_KEY"):
            key = next((env[n] for n in providers.credential_names("gemini") if env.get(n)), "")
            if key:
                env["GOOGLE_GENERATIVE_AI_API_KEY"] = key
        return env

    def tool_steps(self, raw):
        steps = []
        for event in json_lines(raw):
            part = event.get("part") or {}
            if event.get("type") == "tool_use" and part.get("type") == "tool":
                state = part.get("state") or {}
                data = state.get("input") or {}
                steps.append({"kind": str(part.get("tool") or "tool"), "ok": state.get("status") == "completed",
                              "label": str(data.get("command") or data.get("filePath") or data.get("pattern") or part.get("tool") or "")[:200], "input": data})
        return steps

    def parse(self, raw):
        got = Parsed(cost_usd=0.0)
        texts: List[str] = []
        for event in json_lines(raw):
            got.session_id = event.get("sessionID") or got.session_id
            part = event.get("part") or {}
            kind = event.get("type", "")
            if kind == "text" and part.get("text"):
                texts.append(str(part["text"]))
            elif kind == "step_finish":
                tokens = part.get("tokens") or {}
                got.tokens_in += int(tokens.get("input") or 0)
                got.tokens_out += int(tokens.get("output") or 0) + int(tokens.get("reasoning") or 0)
                got.cost_usd = (got.cost_usd or 0.0) + float(part.get("cost") or 0.0)
            elif kind == "error":
                error = event.get("error") or {}
                got.error = str((error.get("data") or {}).get("message") or error.get("message") or error.get("name") or "error")
        got.text = "\n\n".join(t.strip() for t in texts if t.strip())
        return got
