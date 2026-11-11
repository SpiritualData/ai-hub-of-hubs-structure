"""Solution workers: the hub's own sub-agents, arranged as the hierarchy of the solutions being worked on, with no model call of its own.

Role: work is specified as solutions, each with its own records, a metric and milestones, and a solution delegates to child solutions
(``delegates_to``). Handing a task to ad hoc sub-agents with ad hoc briefs loses that structure. ``work_solution`` follows it instead: one worker
per solution, each briefed only with its own solution's frame and the one line its parent hands down (the parent's frame and the siblings' output
never reach it, which is the isolation), each with its own done-standard (the solution's next milestone not yet met) checked by something other
than the worker. Children go first, in parallel up to ``width``, and report up compactly (``SolutionReport.compact``); the parent then does its own
part holding those reports and is checked; an unmet part is worked again, with what the check found missing, while rounds remain and Goal Completion's stop decision (``stop``, the hub's selected one
resolved by name when none is given, with what the person stated and the policy as ``stop_inputs``) says another round is worth its cost: a plateau, a regress, a
met goal, a limit the person stated or a need only a person can meet ends the rounds with that reason in ``SolutionReport.stopped``.

Everything that touches the outside is injected: ``frame`` (the records of a solution), ``children`` (which child solutions a task concerns),
``work`` (one solution's part: an external agent session today, an in-hub loop later), ``check`` (the independent verdict on the milestone),
``already_met`` and ``cancel``. ``records_frame`` and ``delegates_of`` build the first two from the hub's own record reading. The limits that apply to
any handoff (authority, the goal record's budget, cancellation) stay in ``delegation.py``; this module adds the tree budget
``{depth, width, calls, rounds}`` (the shape of ``solution_passes.depth.build_out``'s), shared by the whole tree through one locked counter, where
``calls`` counts worker calls (a check is a separate judgment and is not counted). Standard library plus the hub and ``esoi``."""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_intelligence.critical_thinking.solution_passes.solution_run import solution_frame

DEFAULT_BUDGET = {"calls": 16, "depth": 2, "width": 4, "rounds": 2}
HANDED = "{parent} needs from {child}, for: {task}, toward: {milestone}"
MET, UNMET, ALREADY_MET, NOT_STARTED, CANCELLED = "met", "unmet", "already_met", "not_started", "cancelled"


@dataclass
class SolutionReport:
    """What one solution's worker came to, with the reports of the children it ran first. ``met`` is None when nothing was started (``status`` is then
    ``not_started`` or ``cancelled``, and ``missing`` says why); ``already_met`` is a child the records already show done, started at no cost."""
    solution: str
    name: str = ""
    milestone: str = ""
    met: Optional[bool] = None
    status: str = NOT_STARTED
    output: str = ""
    missing: str = ""
    calls: int = 0
    stopped: str = ""      # why no further round was worked: the stop decision's code and decision, "" when the rounds ran out or the goal was met
    children: List["SolutionReport"] = field(default_factory=list)

    def total_calls(self) -> int:
        return self.calls + sum(c.total_calls() for c in self.children)

    def compact(self, chars: int = 600) -> str:
        """What goes up to the parent: the status, the milestone, the output clipped to ``chars`` and what is missing."""
        text = " ".join(str(self.output or "").split())
        text = text if len(text) <= chars else text[:max(chars - 3, 0)].rstrip() + "..."
        lines = [f"{self.name or self.solution} ({self.solution}): {self.status}"]
        for label, value in (("Milestone", self.milestone), ("Output", text), ("Missing", self.missing)):
            if value:
                lines.append(f"{label}: {value}")
        return "\n".join(lines)

    def tree_text(self) -> str:
        """An indented outline, one line per solution with its status: the shape of the solution hierarchy that was worked."""
        def lines(node: "SolutionReport", depth: int) -> List[str]:
            note = f", {node.missing}" if node.status in (NOT_STARTED, CANCELLED) and node.missing else ""
            own = f"{'  ' * depth}- {node.name or node.solution} ({node.solution}): {node.status}, {node.calls} call{'' if node.calls == 1 else 's'}{note}"
            return [own] + [line for child in node.children for line in lines(child, depth + 1)]
        return "\n".join(lines(self, 0))


class Counter:
    """The calls left for the whole tree; ``take`` is atomic, so parallel children never overspend."""
    def __init__(self, calls: int):
        self.left, self.lock = int(calls), threading.Lock()

    def take(self) -> bool:
        with self.lock:
            if self.left <= 0:
                return False
            self.left -= 1
            return True


def delegates_of(records: Any) -> Callable[[str, str], List[str]]:
    """A ``children`` callable from the hub's own records: the ids a solution row names in ``delegates_to`` (``none`` and ids the records do not know
    left out), whatever the task; a consumer that filters by relevance supplies its own. ``records`` is a records root or a network."""
    from esoi import split_ids
    from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import network_of
    net = network_of(records)

    def children(solution_id: str, task: str = "") -> List[str]:
        return [c for c in split_ids(net.row(solution_id).get("delegates_to", "")) if c != "none" and net.has(c)]
    return children


def records_frame(records: Any) -> Callable[[str], Dict[str, Any]]:
    """A ``frame`` callable from the hub's own records: the solution's ``name``, ``approach`` (its purpose when it has none) and its next milestone not
    yet met as ``milestone`` ("" when every milestone is met). ``records`` is a records root or a network."""
    from esoi.structure.intent_registry.fields import parse_milestones
    from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import network_of
    net = network_of(records)

    def frame(solution_id: str) -> Dict[str, Any]:
        row = net.row(solution_id)
        unmet = [m["text"] for m in parse_milestones(row.get("milestones", ""), in_order=True) if not m["met"]]
        return {"name": net.name(solution_id), "approach": row.get("approach") or row.get("purpose") or "", "milestone": unmet[0] if unmet else ""}
    return frame


def better(old: Tuple[str, Mapping[str, Any]], new: Tuple[str, Mapping[str, Any]]) -> bool:
    """Whether a reworked attempt replaces the kept one: a met attempt always; otherwise the latest, unless both checks gave a ``score`` and the new one
    is not strictly higher (a lower score is never kept)."""
    if new[1].get("met"):
        return True
    if old[1].get("met"):
        return False
    a, b = old[1].get("score"), new[1].get("score")
    return b > a if a is not None and b is not None else True


def work_solution(solution_id: str, *, frame: Callable[[str], Mapping[str, Any]], children: Callable[[str, str], Sequence[str]],
                  work: Callable[[Mapping[str, Any]], str], check: Callable[[str, str, str], Mapping[str, Any]], task: str = "", handed: str = "",
                  budget: Optional[Mapping[str, int]] = None, already_met: Optional[Callable[[str], bool]] = None,
                  cancel: Optional[Callable[[], bool]] = None, session: Optional[Callable[[Dict[str, Any]], None]] = None,
                  stop: Optional[Callable[[Mapping[str, Any]], Mapping[str, Any]]] = None, stop_inputs: Optional[Mapping[str, Any]] = None) -> SolutionReport:
    """Work ``task`` through the hierarchy under ``solution_id`` and return the tree of reports. Each node: its children first (each a recursive call,
    in parallel up to ``width``, each handed ``HANDED`` filled in), then its own ``work(brief)`` with the children's compact reports, then
    ``check(solution_id, milestone, output) -> {"met", "missing"[, "score"]}``; unmet with rounds left, it works again with ``missing`` in the brief.
    The brief holds only ``solution_id``, ``name``, ``frame``, ``milestone``, ``task``, ``handed``, ``reports`` and, on a rework, ``missing`` and
    ``round``. A worker or check that raises leaves that node unmet with the error as ``missing``; the rest of the tree still runs. Work that is not
    started (calls spent, depth reached, a cycle, cancellation) is reported with the reason, never dropped.

    With a ``session`` sink each node is announced as an agent of the tree, with its parent and its solution: ``agent-started`` once its frame is
    known and ``agent-ended`` with its state and calls when it is done, as dicts shaped like the session events of the Consciousness container. The
    brief then also holds ``agent_id`` (the node's agent), so a worker can report its steps under its solution."""
    bound = {**DEFAULT_BUDGET, **dict(budget or {})}
    counter = Counter(bound["calls"])
    if stop is None:
        from hubofhubs.the_intelligence.critical_thinking.goal_completion.stop_rule import selected_stop_decider
        stop = selected_stop_decider()      # the hub's own resolution; None when none is assembled, and every round then runs as before
    inputs = dict(stop_inputs or {})

    def another_round(tried: List[Dict[str, Any]]) -> str:
        """"" when a further round is worth working, else why not (``code:decision``). A decision that fails is a refusal to iterate."""
        if stop is None:
            return ""
        scores = [t["score"] for t in tried]
        history = {"iterations": [{"verdict": t["met"], "metric": t["score"] if all(x is not None for x in scores) else None, "changed": t["changed"],
                                   "missing": [t["missing"]] if t["missing"] else [], "spend_usd": 0.0, "seconds": 0.0} for t in tried],
                   "metric": {"better": "higher", "target": 1.0}, "stated": dict(inputs.get("stated") or {}), "policy": dict(inputs.get("policy") or {}),
                   "needs_human": inputs.get("needs_human") or ""}
        try:
            verdict = dict(stop(history) or {})
        except Exception as error:      # noqa: BLE001
            return f"decision_failed:{type(error).__name__}"
        return "" if verdict.get("decision", "continue") == "continue" else f"{verdict.get('code') or ''}:{verdict.get('decision')}"

    begun: set = set()

    def agent_of(path: Tuple[str, ...], sid: str) -> str:
        return "-".join(path + (sid,))

    def say(kind: str, **data: Any) -> None:
        if session is not None:
            try:
                session(dict(data, type=kind))
            except Exception:      # noqa: BLE001  a surface that fails never stops the work
                pass

    def node(sid: str, task_text: str, handed_line: str, level: int, path: Tuple[str, ...]) -> SolutionReport:
        report = node_body(sid, task_text, handed_line, level, path)
        agent = agent_of(path, sid)
        if agent in begun:
            state = {MET: "met", ALREADY_MET: "met", CANCELLED: "stopped", NOT_STARTED: "not_started"}.get(report.status, "unmet")
            say("agent-ended", agent_id=agent, state=state, calls=report.total_calls(), summary=report.missing[:100])
        return report

    def node_body(sid: str, task_text: str, handed_line: str, level: int, path: Tuple[str, ...]) -> SolutionReport:
        report = SolutionReport(solution=sid)
        try:
            fields = dict(frame(sid) or {})
        except Exception as error:      # noqa: BLE001  a records failure is this node's result, not the tree's
            report.status, report.missing = UNMET, f"{type(error).__name__}: {error}"
            return report
        report.name, report.milestone = str(fields.get("name") or sid), str(fields.get("milestone") or "")
        begun.add(agent_of(path, sid))
        say("agent-started", agent_id=agent_of(path, sid), parent_id="-".join(path) or "main", task=report.name, solution=sid)
        if cancel is not None and cancel():
            report.status, report.missing = CANCELLED, "cancelled before this work started"
            return report
        try:
            kids = [c for c in dict.fromkeys(children(sid, task_text) or ()) if c != sid]
        except Exception as error:      # noqa: BLE001
            kids, report.missing = [], f"children not read: {type(error).__name__}: {error}"

        def child(cid: str) -> SolutionReport:
            if cid in path:
                return SolutionReport(solution=cid, name=cid, status=NOT_STARTED, missing="cycle: already on the path " + " > ".join(path + (sid,)))
            if level >= bound["depth"]:
                return SolutionReport(solution=cid, name=cid, status=NOT_STARTED, missing=f"depth limit {bound['depth']} reached")
            if already_met is not None and already_met(cid):
                try:
                    shown = frame(cid)
                except Exception:      # noqa: BLE001
                    shown = {}
                return SolutionReport(solution=cid, name=str(shown.get("name") or cid), milestone=str(shown.get("milestone") or ""), met=True,
                                      status=ALREADY_MET, output="already met: no work was started")
            try:
                name = str(frame(cid).get("name") or cid)
            except Exception:      # noqa: BLE001
                name = cid
            line = HANDED.format(parent=report.name, child=name, task=task_text, milestone=report.milestone)
            return node(cid, task_text, line, level + 1, path + (sid,))

        if kids:
            with ThreadPoolExecutor(max_workers=max(1, min(int(bound["width"]), len(kids)))) as pool:
                report.children = list(pool.map(child, kids))
        reports = [c.compact() for c in report.children]
        base = {"solution_id": sid, "name": report.name, "frame": solution_frame({**fields, "next_milestone": fields.get("next_milestone") or fields.get("milestone")}), "milestone": report.milestone, "task": task_text,
                "handed": handed_line, "reports": reports}
        if session is not None:
            base["agent_id"] = agent_of(path, sid)
        kept: Optional[Tuple[str, Mapping[str, Any]]] = None
        tried: List[Dict[str, Any]] = []
        for attempt in range(1, int(bound["rounds"]) + 1):
            if cancel is not None and cancel():
                if kept is None:
                    report.status, report.missing = CANCELLED, "cancelled before this work started"
                break
            if tried and (why := another_round(tried)):
                report.stopped = why
                break
            if not counter.take():
                if kept is None:
                    report.status, report.missing = NOT_STARTED, f"call budget of {bound['calls']} spent"
                break
            report.calls += 1
            brief = dict(base) if attempt == 1 else {**base, "missing": str(kept[1].get("missing") or ""), "round": attempt}
            try:
                output = str(work(brief) or "")
                verdict = dict(check(sid, report.milestone, output) or {})
            except Exception as error:      # noqa: BLE001  one failing worker or check must not stop its siblings or its parent
                kept = kept or ("", {"met": False, "missing": f"{type(error).__name__}: {error}"})
                continue
            score = verdict.get("score")
            tried.append({"met": bool(verdict.get("met")), "score": float(score) if isinstance(score, (int, float)) and not isinstance(score, bool) else None,
                          "missing": str(verdict.get("missing") or ""), "changed": int(not tried or output != tried[-1].get("output", "")), "output": output})
            if kept is None or better(kept, (output, verdict)):
                kept = (output, verdict)
            if kept[1].get("met"):
                break
        if kept is not None:
            report.output, report.met = kept[0], bool(kept[1].get("met"))
            report.status = MET if report.met else UNMET
            report.missing = "" if report.met else str(kept[1].get("missing") or "")
        return report

    return node(solution_id, task, handed, 0, ())
