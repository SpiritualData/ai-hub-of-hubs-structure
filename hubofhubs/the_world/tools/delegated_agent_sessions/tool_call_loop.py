"""The hub's own loop on a provider's native tool calling.

Role: the hub's text loop asks a pure completion for actions in a protocol invented here; a model is trained on its provider's tool calls, so that protocol costs
it calls and accuracy on long tool-heavy work. This loop keeps what the hub adds (the folder map and the files that matter in view, a short plan as working memory,
steering messages, a saved session to resume, sub-agents, ceilings, a code check before the work is accepted and the stop decision for every call the hub itself
initiates) and speaks the provider's own interface for the rest: the model is called through the vendor model caller's ``tool_turn`` with the tool names and shapes of
its dialect (``tool_box``), and each call runs in the hub's Command Execution, File Reading and File Editing.

The turn function is injected: ``turn(transcript, system, tools) -> ModelTurn`` (see ``vendor_model_caller.tool_calling``), so the loop is tested with a stub and
serves every vendor. Standard library and the hub only.
"""
from __future__ import annotations

import json
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_world.model_plumbing.vendor_model_caller.tool_calling import ModelTurn, jsonable, tool_message, user_message
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import build_frame
from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import (
    CANCEL_POLL_SECONDS, CallCounter, LoopResult, LoopState, Repeats, Telling, bounded_state, short, snapshot, track, unsupported)
from hubofhubs.the_world.tools.delegated_agent_sessions.tool_box import OPERATIONS, ToolBox, tools_for

COMPACT_AT_CHARS = 360_000      # the transcript passes this and the results of older calls shrink (about 90,000 tokens)
KEEP_RECENT = 10                # messages at the end that are never shrunk
OLD_RESULT_CHARS = 400
MAX_HELPER_DEPTH = 1
FINISH_MESSAGE = ("You stopped without a final report. Finish the work above with your tools if anything is left, then write the final report as plain text: what you "
                  "found or changed, concretely.")
PLAN_MESSAGE = "Your plan still has steps that are not completed. Finish them (or mark them cancelled with the reason), then write the final report."
CONTINUE_MESSAGE = "Your reply was cut off. Continue from where it stopped."
ENDING = ("When the work is done, reply with the final report as plain text and no tool call. Tools run in the order you call them, and several independent calls may be "
          "made in one reply.")


@dataclass
class ToolLoopState(LoopState):
    """A ``LoopState`` that also holds the transcript, so a saved session continues where it stopped."""
    transcript: List[Dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> str:
        data = json.loads(LoopState.to_json(self))
        data["transcript"] = [jsonable(m) for m in self.transcript]
        return json.dumps(data, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> "ToolLoopState":
        base = LoopState.from_json(text)
        try:
            transcript = [dict(m) for m in json.loads(text).get("transcript", [])]
        except (TypeError, ValueError, AttributeError) as error:
            raise ValueError(f"not a saved loop state: {error}") from error
        return cls(**{k: getattr(base, k) for k in ("goal", "entries", "view", "changed", "read", "calls", "state", "ended")}, transcript=transcript)


def transcript_chars(transcript: Sequence[Mapping[str, Any]]) -> int:
    return len(json.dumps([{k: v for k, v in m.items() if k != "raw"} for m in transcript], default=str))


def compact(transcript: List[Dict[str, Any]], at: int = COMPACT_AT_CHARS) -> bool:
    """Shrink the results of older tool calls (all but the last ``KEEP_RECENT`` messages) once the transcript passes ``at`` characters; what a call was and
    whether it failed stays, as does every plan the model wrote (its call inputs are never touched). True when something shrank."""
    if transcript_chars(transcript) <= at:
        return False
    shrank = False
    for message in transcript[:max(len(transcript) - KEEP_RECENT, 0)]:
        for result in message.get("results") or []:
            if len(result["text"]) > OLD_RESULT_CHARS:
                result["text"] = result["text"][:OLD_RESULT_CHARS] + f"\n[{len(result['text']) - OLD_RESULT_CHARS} characters of an earlier result left out; run the tool again if you need them]"
                shrank = True
    return shrank


def unfinished(plan: str) -> bool:
    return any(line.startswith(("[ ]", "[~]")) for line in plan.splitlines())


def run_tool_loop(goal: str, *, working_dir: str, turn: Callable[[List[Dict[str, Any]], str, List[Any]], ModelTurn], provider: str = "anthropic", context: str = "",
                  max_calls: int = 40, depth: int = MAX_HELPER_DEPTH, cancel: Optional[Callable[[], bool]] = None, emit: Optional[Callable[[str], None]] = None,
                  command_timeout: float = 120.0, environment: Optional[Mapping[str, str]] = None, wrap: Sequence[str] = (), counter: Optional[CallCounter] = None,
                  review: bool = True, state: Optional[ToolLoopState] = None, save: Optional[Callable[[ToolLoopState], None]] = None,
                  inbox: Optional[Callable[[], Sequence[str]]] = None, select: Optional[Callable[..., Any]] = None, notes: str = "", telling: Optional[Telling] = None,
                  stop_now: Optional[Callable[[], bool]] = None, permit: Optional[Callable[[str, Mapping[str, Any]], Tuple[bool, str]]] = None,
                  actions: Optional[List[Tuple[str, Any]]] = None, view_chars: int = 60_000, worth: Optional[Callable[..., List[str]]] = None,
                  check_message: str = "") -> LoopResult:
    """Work ``goal`` in ``working_dir`` until the model reports with no tool call (and the hub's checks accept it), ``max_calls`` model calls are spent (``counter`` is shared
    with the helpers) or ``cancel()`` is true. Never raises. ``state`` continues an earlier run (its transcript, plan and the paths changed and read); ``save`` gets the new
    state after every call; ``inbox`` returns the messages a person sent, shown to the model with the results of its next tools. ``permit(kind, facts) -> (go, reason)``
    is asked before each call the hub starts itself (``review``: a code finding sends the model back to its work; ``nudge``: an empty or unfinished report); a refusal
    ends the run with the report it has. ``actions`` collects ``(Claude Code tool name, input)`` of what the run wrote or ran, for the outside-the-folder report."""
    result = LoopResult()
    try:
        loop(result, goal, working_dir, turn, provider, context, max_calls, depth, cancel, emit, command_timeout, environment, wrap,
             counter if counter is not None else CallCounter(max_calls), review, state, save, inbox, select, notes, telling, stop_now, permit,
             actions if actions is not None else [], view_chars, worth, check_message)
    except Exception as error:  # noqa: BLE001 -- the loop reports a failure, it does not raise
        result.met = False
        result.error = result.error or f"the loop failed: {type(error).__name__}: {error}"
        result.ended = result.ended or "failed"
    return result


def loop(result: LoopResult, goal: str, working_dir: str, turn, provider: str, context: str, max_calls: int, depth: int, cancel, emit, command_timeout: float,
         environment, wrap, counter: CallCounter, review: bool, state: Optional[ToolLoopState], save, inbox, select, notes: str, telling: Optional[Telling], stop_now,
         permit, actions: List[Tuple[str, Any]], view_chars: int, worth, check_message: str) -> None:
    root = os.path.abspath(working_dir)
    say = emit or (lambda _text: None)
    tell = telling if telling is not None else Telling(None)
    tools = tools_for(provider, delegate=depth > 0)
    plan_name = next((t.name for t in tools if OPERATIONS[t.name][0] == "plan"), "your plan tool")
    frame = build_frame(goal, context, root, select=select, view_chars=view_chars, notes=notes)
    system = frame.text.replace("your task tools (TaskCreate, TaskUpdate)", f"your plan tool ({plan_name})") + "\n\n" + ENDING
    plan = {"text": state.state if state else ""}
    changed: "OrderedDict[str, None]" = OrderedDict((rel, None) for rel in (state.changed if state else []))
    seen: "OrderedDict[str, None]" = OrderedDict((rel, None) for rel in (state.read if state else []))
    before = snapshot(root)
    transcript: List[Dict[str, Any]] = [dict(m) for m in state.transcript] if state is not None and state.transcript else []
    first = f"GOAL:\n{goal.strip()}" + (f"\n\nSTANDING CONTEXT:\n{context.strip()}" if context.strip() else "")
    if transcript:
        first = ("The work is continued. The files in the system notes are current as of now, and the files may have changed since your last turn.\n"
                 + (f"Your plan so far:\n{plan['text']}\n\n" if plan["text"].strip() else "") + first)
    transcript.append(user_message(first))
    repeats = Repeats()

    def set_plan(text: str) -> None:
        plan["text"] = bounded_state(text)

    helpers = [0]

    def delegate(prompt: str) -> str:
        helpers[0] += 1
        child = Telling.helper(tell, prompt) if hasattr(Telling, "helper") else tell
        sub = LoopResult()
        loop(sub, prompt, root, turn, provider, context, max_calls, depth - 1, cancel, emit, command_timeout, environment, wrap, counter, False, None, None, None, select, notes,
             child, stop_now, permit, actions, view_chars, worth, check_message)
        for rel in sub.changed:
            changed.setdefault(rel)
        return (sub.report or "(no report)") + ("" if sub.met else f"\n(the helper did not finish: {sub.error})")

    box = ToolBox(root, environment=environment, wrap=wrap, command_timeout=command_timeout, plan=set_plan, delegate=delegate if depth > 0 else None)
    own_calls = 0
    nudges = {"finish": 0, "plan": 0}
    resumes = 0
    rounds: List[Dict[str, Any]] = []
    last_text = ""
    pending_steer: List[str] = []

    def persist() -> None:
        if save is None:
            return
        try:
            save(ToolLoopState(goal=goal, entries=[], view=[], changed=list(changed), read=list(seen), calls=(state.calls if state else 0) + own_calls, state=plan["text"],
                               ended=result.ended, transcript=transcript))
        except Exception:  # noqa: BLE001 -- a store that cannot write never ends a run
            pass

    def messages() -> List[str]:
        if inbox is None:
            return []
        try:
            got = [str(m).strip() for m in (inbox() or []) if str(m).strip()]
        except Exception:  # noqa: BLE001
            return []
        for text in got:
            tell.step("message-received", text, "done", step_id=f"message-{tell.count('message')}")
        return got

    def ask() -> ModelTurn:
        """One model call; with a ``cancel`` it runs on a thread of its own and is given up as soon as a person's stop arrives."""
        interrupt = stop_now or cancel
        if interrupt is None:
            return turn(transcript, system, tools)
        box_: Dict[str, Any] = {}

        def go() -> None:
            try:
                box_["turn"] = turn(transcript, system, tools)
            except BaseException as error:  # noqa: BLE001 -- handed to the caller's thread
                box_["error"] = error
        worker = threading.Thread(target=go, daemon=True)
        worker.start()
        while worker.is_alive():
            worker.join(CANCEL_POLL_SECONDS)
            if worker.is_alive() and interrupt():
                raise InterruptedError("the run was stopped while a model call was in flight")
        if "error" in box_:
            raise box_["error"]
        return box_["turn"]

    def allowed(kind: str) -> Tuple[bool, str]:
        if permit is None:
            return True, ""
        try:
            go, why = permit(kind, {"rounds": [dict(r) for r in rounds], "calls": own_calls, "resumes": resumes})
        except Exception as error:  # noqa: BLE001
            return False, f"decision_failed:{type(error).__name__}"
        return bool(go), why or "declined"

    while True:
        if own_calls:
            persist()
        if cancel is not None and cancel():
            result.error, result.ended = "the run was cancelled", "cancelled"
            break
        if not counter.take():
            result.error, result.ended = f"the call limit ({counter.limit}) was spent before the work was finished", "call_limit"
            break
        compact(transcript)
        pending_steer.extend(messages())
        own_calls += 1
        result.calls += 1
        try:
            got = ask()
        except InterruptedError:
            own_calls -= 1
            result.calls -= 1
            result.error, result.ended = "the run was cancelled", "cancelled"
            break
        except Exception as error:  # noqa: BLE001
            result.error, result.ended = f"the model call failed: {type(error).__name__}: {error}", "model_failed"
            break
        tell.send("usage", calls=counter.used)
        transcript.append(got.as_message())
        result.log.append({"call": own_calls, "reply": got.text, "tools": [c.name for c in got.calls]})
        last_text = got.text.strip() or last_text
        if got.calls:
            results = []
            for call in got.calls:
                operation = OPERATIONS.get(call.name, ("", {}))[0]
                label = str(call.args.get("command") or call.args.get("file_path") or call.args.get("path") or call.args.get("pattern") or call.args.get("prompt") or call.name)
                key = f"{call.name} {json.dumps(call.args, sort_keys=True, default=str)}"
                step = tell.step(operation or call.name, label, "running", step_id=f"{tell.agent}-call-{own_calls}-{call.id}")
                refused = repeats.refusal(key) if operation == "bash" else ""
                done = box.run(call.name, call.args) if not refused else None
                text, failed = (refused, True) if done is None else (done.text, done.error)
                if done is not None:
                    if operation == "bash":
                        text += repeats.failure(key, done.text)[1] if failed else repeats.success(key)
                    if done.action:
                        actions.append(done.action)
                    for rel in done.wrote:
                        changed.setdefault(rel)
                    for rel in done.read:
                        seen.setdefault(rel)
                tell.step(operation or call.name, label, "failed" if failed else "done", step_id=step, detail=text if failed else "")
                say(f"call {own_calls}: {call.name} {'failed' if failed else 'ok'}")
                results.append({"id": call.id, "name": call.name, "text": text, "error": failed})
            track(root, before, changed)
            if pending_steer and results:
                results[-1]["text"] += "\n\n[Message from the person, follow it: " + " | ".join(pending_steer) + "]"
                pending_steer.clear()
            transcript.append(tool_message(results))
            continue
        if got.finish in ("max_tokens", "length", "MAX_TOKENS") and own_calls < max_calls:
            transcript.append(user_message(CONTINUE_MESSAGE))
            continue
        if pending_steer:        # a message arrived while the model worked and its report did not see it
            transcript.append(user_message("A message from the person arrived: " + " | ".join(pending_steer) + "\nAnswer it, then report again."))
            pending_steer.clear()
            continue
        # The model reported with no tool call: the hub decides whether that is accepted. Each refusal below is iteration the person did not ask for.
        report = got.text.strip()
        track(root, before, changed)
        refusal_text, kind = "", ""
        if not report:
            refusal_text, kind = FINISH_MESSAGE if nudges["finish"] == 0 else "", "nudge"
            nudges["finish"] += 1
        elif unfinished(plan["text"]) and nudges["plan"] == 0:
            refusal_text, kind = PLAN_MESSAGE, "nudge"
            nudges["plan"] += 1
        elif review and changed:
            found = (worth or (lambda root_, found_: found_))(root, unsupported(root, list(changed)))
            if found and resumes < 1:
                refusal_text, kind = (check_message or "A code check of the files you wrote found these:\n") + "\n".join(found), "review"
                rounds.append(dict(findings=len(found), spend_usd=0.0, elapsed_seconds=0.0, changed=len(changed)))
        if refusal_text:
            go, why = allowed(kind)
            if go and counter.left() > 0:
                resumes += 1 if kind == "review" else 0
                tell.step("hub-iteration", f"{kind}: {short(refusal_text, 80)}", "done", step_id=f"{tell.agent}-hub-{own_calls}")
                transcript.append(user_message(refusal_text))
                continue
            result.end_reason = f"resume_stopped:{why}" if not go else ""      # type: ignore[attr-defined]
        result.met = bool(report)
        result.report = report or last_text
        result.ended = "met" if report else "no_action"
        if not report:
            result.error = "the model ended without a final report"
        break
    result.report = result.report or last_text
    result.state = plan["text"]
    result.ended = result.ended or ("met" if result.met else "failed")
    result.changed = list(changed)
    result.read = list(seen)
    persist()
