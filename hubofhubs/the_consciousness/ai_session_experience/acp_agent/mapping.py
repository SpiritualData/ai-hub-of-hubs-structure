"""The hub's session events as Agent Client Protocol updates, and the protocol's answers as the hub's controls. Pure functions and one small state holder: no protocol library,
no thread, no stream, so every mapping is tested on plain dicts. The wire shapes are those of https://agentclientprotocol.com/protocol/overview (``session/update`` with
``sessionUpdate`` of ``agent_message_chunk``, ``tool_call``, ``tool_call_update`` and ``plan``; ``session/request_permission``; stop reasons).

What each event becomes:

* ``RunStarted``: one message with the solution, the milestone and the frame the work serves, and the metric before; a plan with the milestone and the metric as entries.
* ``Step``: a tool call (kind mapped: read, edit, run and check are ``read``, ``edit``, ``execute``, ``execute``; tool and delegate are ``other``), updated in place by its step id,
  its state mapped to ``in_progress``, ``completed`` or ``failed`` (a blocked step is ``failed`` and its title says it was refused, with the reason). A step of a helper is titled with the helper.
  ``message-received`` (the harness took up a message the person sent) is a message line.
* ``AgentStarted`` and ``AgentEnded``: a tool call titled with the helper's task and the solution it serves, completed or failed when it ends, with its summary.
* ``Review``, ``Notice``: message lines. ``Usage``: nothing, except one line the first time ceilings are known. ``Waiting`` is not an update: it is a permission request (``permission_request``).
* ``Finished``: the stop reason (``end_turn`` for met, unmet and failed, with the outcome said in the report; ``cancelled`` for stopped) and one closing message with the outcome, the report,
  the changed files, what was refused, what was done outside the folder, cost and time, the metric before and after and the session to resume.

What the protocol cannot carry: the structure tree on request (no key reaches the agent), a live spend-against-ceiling gauge (a line at the start and in the closing report only), and
stopping one helper (a client can cancel only the whole turn). Standard library only."""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    MAIN, AgentEnded, AgentStarted, Finished, Notice, Review, RunStarted, SessionEvent, Step, Usage, Waiting, short)

KINDS = {"read": "read", "edit": "edit", "run": "execute", "check": "execute", "tool": "other", "delegate": "other", "note": "other", "message-received": "other"}
STATUS = {"running": "in_progress", "done": "completed", "failed": "failed", "blocked": "failed"}
AGENT_STATUS = {"running": "in_progress", "met": "completed", "unmet": "failed", "stopped": "failed", "failed": "failed", "not_started": "pending"}
STOP_REASONS = {"met": "end_turn", "unmet": "end_turn", "failed": "end_turn", "stopped": "cancelled"}
OPTION_APPROVE, OPTION_REFUSE = "approve", "refuse"
STEERING_METHODS = ("session/steering", "_session/steering")


def text_block(text: str) -> Dict[str, Any]:
    return {"type": "text", "text": text}


def message(text: str) -> Dict[str, Any]:
    return {"sessionUpdate": "agent_message_chunk", "content": text_block(text if text.endswith("\n") else text + "\n")}


def tool_content(text: str) -> List[Dict[str, Any]]:
    return [{"type": "content", "content": text_block(text)}] if text else []


def prompt_text(blocks: Sequence[Any]) -> str:
    """The text of a prompt: its text blocks, and a resource's text, joined; other blocks are named and left out."""
    parts = []
    for block in blocks or ():
        kind = block.get("type") if isinstance(block, Mapping) else getattr(block, "type", "")
        if kind == "text":
            parts.append(str(block.get("text") if isinstance(block, Mapping) else getattr(block, "text", "")))
        elif kind == "resource":
            resource = block.get("resource") if isinstance(block, Mapping) else getattr(block, "resource", None)
            text = resource.get("text") if isinstance(resource, Mapping) else getattr(resource, "text", "")
            if text:
                parts.append(str(text))
        elif kind == "resource_link":
            parts.append(str(block.get("uri") if isinstance(block, Mapping) else getattr(block, "uri", "")))
    return "\n".join(p for p in parts if p).strip()


def seconds_text(seconds: Optional[float]) -> str:
    if seconds is None:
        return ""
    whole = int(seconds)
    return f"{whole // 60}:{whole % 60:02d}"


class Translator:
    """Turns one run's events into protocol updates, in order, remembering which tool calls it has opened (a step is started once and updated after)."""

    def __init__(self, acting_for: str = "") -> None:
        self.acting_for = acting_for
        self.opened: Dict[str, str] = {}
        self.helpers: Dict[str, AgentStarted] = {}
        self.ceilings_said = False
        self.metric_before: Optional[float] = None
        self.metric = ""
        self.cost: Optional[float] = None
        self.seconds_by_event = 0.0
        self.solution = ""

    # --- events ---------------------------------------------------------------------------------------------------------------

    def updates(self, event: SessionEvent) -> List[Dict[str, Any]]:
        if isinstance(event, RunStarted):
            return self.started(event)
        if isinstance(event, Step):
            return self.step(event)
        if isinstance(event, AgentStarted):
            return self.helper_started(event)
        if isinstance(event, AgentEnded):
            return self.helper_ended(event)
        if isinstance(event, Review):
            return [message(f"Review: {event.text}" + (f" ({event.corrections} correction{'' if event.corrections == 1 else 's'})" if event.corrections else ""))]
        if isinstance(event, Notice):
            return [message(self.notice_text(event))]
        if isinstance(event, Usage):
            return self.usage(event)
        return []

    def started(self, event: RunStarted) -> List[Dict[str, Any]]:
        self.metric_before, self.metric, self.solution = event.metric_before, event.metric, event.solution
        lines = []
        if event.solution or event.milestone:
            lines.append(f"Serving {event.solution or 'this work'}" + (f", milestone: {event.milestone}" if event.milestone else ""))
        if event.frame:
            lines.append(f"Frame: {event.frame}")
        if self.acting_for:
            lines.append(f"Acting for {self.acting_for}")
        if event.metric_before is not None:
            lines.append(f"{event.metric or 'Metric'} before: {event.metric_before:g}")
        if event.resumed:
            lines.append(f"Resuming session {event.session_id}" if event.session_id else "Resuming the session")
        out = [message("\n\n".join(lines))] if lines else []      # a blank line between rows: a markdown client joins single line breaks into one paragraph
        entries = []
        if event.solution or event.milestone:
            entries.append({"content": f"{event.solution}: {event.milestone}".strip(": "), "priority": "high", "status": "in_progress"})
        if event.metric_before is not None:
            entries.append({"content": f"{event.metric or 'Metric'} (before {event.metric_before:g})", "priority": "medium", "status": "pending"})
        if entries:
            out.append({"sessionUpdate": "plan", "entries": entries})
        return out

    def step(self, event: Step) -> List[Dict[str, Any]]:
        if event.kind == "message-received":
            return [message(f"Taken up: {event.label}")]
        if event.kind == "delegate" and any(h.task == event.label for h in self.helpers.values()):
            return []                                    # the helper's own tool call already says it
        helper = self.helpers.get(event.agent_id)
        who =f"[{short(helper.task, 40)}] " if event.agent_id != MAIN and helper is not None else (f"[{event.agent_id[:8]}] " if event.agent_id != MAIN else "")
        why = f" (refused: {short(event.detail, 60)})" if event.state == "blocked" and event.detail else ""
        title = f"{who}{event.kind} {event.label}".strip() + why
        call_id = f"step:{event.agent_id}:{event.step_id or event.label}"
        status = STATUS.get(event.state, "in_progress")
        if call_id not in self.opened:
            self.opened[call_id] = status
            update: Dict[str, Any] = {"sessionUpdate": "tool_call", "toolCallId": call_id, "title": title, "kind": KINDS.get(event.kind, "other"), "status": status}
            if event.detail and not why:
                update["content"] = tool_content(event.detail)
            return [update]
        self.opened[call_id] = status
        update = {"sessionUpdate": "tool_call_update", "toolCallId": call_id, "title": title, "status": status}
        if event.detail:
            update["content"] = tool_content(event.detail)
        return [update]

    def helper_started(self, event: AgentStarted) -> List[Dict[str, Any]]:
        self.helpers[event.agent_id] = event
        parent = self.helpers.get(event.parent_id)
        under = f" under {short(parent.task, 30)}" if parent is not None else ""
        title = f"Helper: {short(event.task, 60)}" + (f" ({event.solution})" if event.solution else "") + under
        self.opened[f"agent:{event.agent_id}"] = "in_progress"
        return [{"sessionUpdate": "tool_call", "toolCallId": f"agent:{event.agent_id}", "title": title, "kind": "other", "status": "in_progress"}]

    def helper_ended(self, event: AgentEnded) -> List[Dict[str, Any]]:
        call_id = f"agent:{event.agent_id}"
        update: Dict[str, Any] = {"sessionUpdate": "tool_call_update", "toolCallId": call_id, "status": AGENT_STATUS.get(event.state, "completed")}
        detail = f"{event.state}, {event.calls} call{'' if event.calls == 1 else 's'}" + (f": {event.summary}" if event.summary else "")
        update["content"] = tool_content(detail)
        if call_id not in self.opened:
            helper = self.helpers.get(event.agent_id)
            return [{"sessionUpdate": "tool_call", "toolCallId": call_id, "title": f"Helper: {short(getattr(helper, 'task', '') or event.agent_id, 60)}", "kind": "other", **update}]
        return [update]

    @staticmethod
    def notice_text(event: Notice) -> str:
        if event.kind == "decision":
            return f"hub decision: {'go on' if event.decision == 'continue' else 'stop'}, {event.text}" if event.text else f"hub decision: {event.decision}"
        if event.kind == "outside-folder":
            return "Outside the folder: " + "; ".join(event.items)
        return event.text or event.kind

    def usage(self, event: Usage) -> List[Dict[str, Any]]:
        if event.cost_usd is not None:
            self.cost = event.cost_usd
        if self.ceilings_said or (event.ceiling_usd is None and event.ceiling_seconds is None):
            return []
        self.ceilings_said = True
        parts = []
        if event.ceiling_usd is not None:
            parts.append(f"${event.ceiling_usd:.2f}")
        if event.ceiling_seconds is not None:
            parts.append(seconds_text(event.ceiling_seconds))
        return [message("Ceilings for this run: " + " and ".join(parts))]

    # --- the end ---------------------------------------------------------------------------------------------------------------

    def closing(self, done: Finished) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """``(stop reason, the closing updates, the response's _meta)``."""
        lines = [{"met": "Done: the goal was met", "unmet": "Not done: the goal was not met", "stopped": "Stopped: finished work is kept", "failed": "Failed" + (f": {done.error}" if done.error else "")}[done.outcome]]
        if done.report.strip():
            lines.append(done.report.strip())
        if done.changed:
            lines.append(f"Changed ({len(done.changed)}): " + ", ".join(done.changed))
        elif done.outcome == "met":
            lines.append("Changed: nothing")
        if done.blocked:
            lines.append("Blocked or refused: " + "; ".join(done.blocked))
        if done.outside:
            lines.append("Outside the folder (report only): " + "; ".join(done.outside))
        if done.end_reason:
            lines.append(f"Ended because: {done.end_reason}")
        spent = done.spend_usd if done.spend_usd is not None else done.cost_usd
        cost = f"${spent:.4f}" if spent is not None else "cost unknown"
        elapsed = seconds_text(done.elapsed_seconds)
        lines.append("Cost and time: " + cost + (f", {elapsed}" if elapsed else ""))
        if done.metric_after is not None:
            before = f"{self.metric_before:g}" if self.metric_before is not None else "unknown"
            lines.append(f"{self.metric or 'Metric'}: before {before}, after {done.metric_after:g}")
        if done.session_id and done.outcome in ("stopped", "unmet"):
            lines.append(f"To continue: load session {done.session_id} and send a prompt")
        updates = [message("\n\n".join(lines))]
        if done.metric_after is not None and self.metric_before is not None:
            updates.append({"sessionUpdate": "plan", "entries": [{"content": f"{self.solution or 'work'}", "priority": "high", "status": "completed"},
                                                                  {"content": f"{self.metric or 'Metric'}: {self.metric_before:g} to {done.metric_after:g}", "priority": "medium", "status": "completed"}]})
        meta = {"hub": {"outcome": done.outcome, "sessionId": done.session_id, "metricBefore": self.metric_before, "metricAfter": done.metric_after, "changed": list(done.changed)}}
        return STOP_REASONS.get(done.outcome, "end_turn"), updates, meta


# --- permission ------------------------------------------------------------------------------------------------------------------

def permission_request(event: Waiting, helper_task: str = "") -> Dict[str, Any]:
    """The ``session/request_permission`` parameters (without the session id) for a risky step that waits: its question as the title, the effect as content, two options."""
    asker = f" ({short(helper_task, 30)} asks)" if helper_task else ""
    body = (f"It will change: {event.preview}" if event.preview else "")
    return {"toolCall": {"toolCallId": f"ask:{event.ask_id}", "title": event.question + asker, "kind": "execute", "status": "pending", "content": tool_content(body)},
            "options": [{"optionId": OPTION_APPROVE, "name": "Approve", "kind": "allow_once"}, {"optionId": OPTION_REFUSE, "name": "Refuse", "kind": "reject_once"}]}


def choice_of(response: Any) -> str:
    """``approve`` when the outcome selected the approve option, else ``refuse`` (a cancelled ask, a refusal and anything unknown are a refusal: a risky step never runs by accident)."""
    outcome = response.get("outcome") if isinstance(response, Mapping) else getattr(response, "outcome", None)
    kind = outcome.get("outcome") if isinstance(outcome, Mapping) else getattr(outcome, "outcome", None)
    option = outcome.get("optionId", outcome.get("option_id")) if isinstance(outcome, Mapping) else getattr(outcome, "option_id", None)
    return OPTION_APPROVE if kind == "selected" and option == OPTION_APPROVE else OPTION_REFUSE
