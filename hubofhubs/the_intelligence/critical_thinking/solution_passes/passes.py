"""Solution Passes by network passes: a separate cheap model pass for each relevant solution, each reading that solution's own generated
prompt, then narrower passes for the scopes above and for the dependents.

1. **Solution passes**, all in parallel and never cut for budget: what the solution needs from the request, the target its own metric sets (so
   Metric Translation does not invent one), the risks, conflicts with its recorded results, knowledge worth keeping and candidates it names.
2. **Parent passes**, one level at a time: one pass per scope above, given its children's findings. Does the change still serve its purpose and
   milestone, does it affect siblings, does its metric or the way its children combine need updating? A scope whose pass finds no effect on the
   combination stops the climb on that branch.
3. **Dependent passes**, narrow: does what the dependent relies on still hold?

Depth and the number of calls are capped (``DEFAULT_LIMITS``); a pass the cap leaves out is reported in ``cut`` with why, never silently. A
consumer may hand its own pass for a solution (``own_passes``), for instance the step that already measured that solution's milestone; it
replaces the model pass for that solution only. Standard library plus the hub and ``esoi``."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

from esoi import Lazy, implementation

from hubofhubs.the_intelligence.critical_thinking.solution_passes.interface import DEFAULT_LIMITS
from hubofhubs.the_world.model_plumbing.interface import ModelPlumbing

FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")
RULES = "Write plainly. Use no em dashes. Reply with JSON only, no markdown."
SOLUTION_ASK = """{prompt}

## Your part
Consider this request for this solution only, from its records above first: {request}
{rules} Shape:
{{"applies": true or false, "needs": "<what this solution needs from the request, one or two sentences, empty if it does not apply>",
"target": {{"metric_id": "<this solution's own metric id from its records>", "value": "<the target value or improvement its metric or next milestone sets>", "done_when": "<one sentence a checker can test>"}},
"risks": ["<risk>"], "conflicts": [{{"record": "<the record or result line>", "says": "<what it says>", "conflict": "<how the request conflicts with it>"}}],
"knowledge": [{{"claim": "<a lesson worth keeping for this solution>", "kind": "lesson", "source": "<the record it rests on>"}}],
"candidates": ["<an alternative implementation the request names that the records do not hold>"]}}"""
PARENT_ASK = """{prompt}

## Your part
A change is proposed under this scope. Its children's own passes found:
{children}
The request: {request}
Judge this level only, as its own scope. {rules} Shape:
{{"serves_purpose": true or false, "milestone_effect": "<effect on this scope's next milestone, or empty>", "siblings_affected": ["<child id>"],
"metric_update": "<what in this scope's metric or in how its children combine needs updating, or empty>", "combination_effect": true or false,
"why": "<one or two sentences citing the records>"}}"""
DEPENDENT_ASK = """{prompt}

## Your part
This solution relies on: {relies}
A change is proposed there: {changes}
{rules} Shape: {{"still_holds": true or false, "why": "<one sentence citing what it relies on>"}}"""


def parse_json(text: Any) -> Dict[str, Any]:
    raw = FENCE.sub("", str(text or "").strip())
    start, end = raw.find("{"), raw.rfind("}")
    try:
        found = json.loads(raw[start:end + 1]) if start >= 0 and end > start else {}
    except ValueError:
        return {}
    return found if isinstance(found, dict) else {}


def listed(value: Any) -> List[Any]:
    return [v for v in value if v] if isinstance(value, list) else ([value] if value else [])


def finding_line(finding: Mapping[str, Any]) -> str:
    target = finding.get("target") or {}
    return (f"- {finding.get('name') or finding['solution_id']} ({finding['solution_id']}): needs {finding.get('needs') or 'nothing'}; target "
            f"{target.get('metric_id') or '?'} {target.get('value') or ''}; risks {'; '.join(map(str, finding.get('risks') or [])) or 'none'}; "
            f"conflicts {'; '.join(str(c.get('conflict') if isinstance(c, Mapping) else c) for c in finding.get('conflicts') or []) or 'none'}")


def parent_line(found: Mapping[str, Any]) -> str:
    return (f"- {found.get('name') or found['solution_id']} ({found['solution_id']}), a scope above: combination affected "
            f"{found.get('combination_effect')}; metric update {found.get('metric_update') or 'none'}; {found.get('why') or ''}")


def shaped_finding(sid: str, name: str, got: Mapping[str, Any]) -> Dict[str, Any]:
    target = got.get("target") if isinstance(got.get("target"), Mapping) else {}
    return {"solution_id": sid, "name": name, "applies": got.get("applies"), "needs": str(got.get("needs") or ""),
            "target": {"metric_id": str(target.get("metric_id") or ""), "value": str(target.get("value") or ""), "done_when": str(target.get("done_when") or "")},
            "risks": listed(got.get("risks")), "conflicts": listed(got.get("conflicts")),
            "knowledge": [k for k in listed(got.get("knowledge")) if isinstance(k, Mapping) and k.get("claim")],
            "candidates": [str(c) for c in listed(got.get("candidates"))], **({"error": got["error"]} if got.get("error") else {})}


@implementation("solution-passes", "network_passes")
class NetworkPasses:
    """One cheap pass per relevant solution in parallel, then parent passes climbing one level at a time and narrow dependent passes, within caps that
    never cut a relevant solution's own pass."""
    REQUIRES = ()     # the model comes through Model Plumbing
    PAID = True

    def __init__(self, plumbing: Lazy[ModelPlumbing], tier: str = "cheap"):
        self.plumbing, self.tier = plumbing, tier

    def consider(self, request: str, briefs: Mapping[str, Any], own_passes: Optional[Mapping[str, Callable[..., Mapping[str, Any]]]] = None,
                 limits: Optional[Mapping[str, int]] = None, ask: Optional[Callable[[str], str]] = None,
                 on_finding: Optional[Callable[[Mapping[str, Any]], Any]] = None) -> Mapping[str, Any]:
        bound = {**DEFAULT_LIMITS, **dict(limits or {})}
        own = dict(own_passes or {})
        call = ask or (lambda prompt: self.plumbing.ask(prompt, self.tier))
        state = {"calls": 0}
        solutions = list(briefs.get("solutions") or [])
        ancestors = dict(briefs.get("ancestors") or {})
        by_id = {s["solution_id"]: s for s in solutions}

        def model(prompt: str) -> Dict[str, Any]:
            state["calls"] += 1
            try:
                got = parse_json(call(prompt))
            except Exception as error:      # noqa: BLE001  a failed pass is a finding that says so, never a crash of the flow
                return {"error": f"{type(error).__name__}: {error}"}
            return got or {"error": "the pass did not answer in the asked shape"}

        def solution_pass(brief: Mapping[str, Any]) -> Dict[str, Any]:
            sid = brief["solution_id"]
            if sid in own:
                try:
                    got = dict(own[sid](request, brief) or {})
                except Exception as error:      # noqa: BLE001
                    got = {"error": f"{type(error).__name__}: {error}"}
                return {**shaped_finding(sid, brief.get("name", sid), got), "by": "own pass"}
            got = model(SOLUTION_ASK.format(prompt=brief.get("prompt", ""), request=request, rules=RULES))
            return {**shaped_finding(sid, brief.get("name", sid), got), "by": "model pass"}

        def announced(brief: Mapping[str, Any]) -> Dict[str, Any]:
            found = solution_pass(brief)
            if on_finding is not None:      # each solution's finding is usable the moment its own pass returns, before any parent pass
                try:
                    on_finding(found)
                except Exception:      # noqa: BLE001  a consumer's hook never stops the passes
                    pass
            return found

        findings = self.parallel([lambda b=b: announced(b) for b in solutions], bound["width"])
        found_by = {f["solution_id"]: f for f in findings}
        cut: List[Dict[str, str]] = []
        parents: List[Dict[str, Any]] = []
        stopped: List[Dict[str, Any]] = []
        # Level 1 is each relevant solution's nearest scope above; a scope that is itself relevant already had its own pass.
        frontier: Dict[str, List[str]] = {}
        for brief in solutions:
            chain = list(brief.get("chain") or [])
            if chain and chain[0] not in by_id:
                frontier.setdefault(chain[0], []).append(brief["solution_id"])
        lines: Dict[str, str] = {sid: finding_line(f) for sid, f in found_by.items()}
        dependents = dict(briefs.get("dependents") or {})
        level = 1
        dependent_jobs = []
        dependents_out: List[Dict[str, Any]] = []
        for other, brief in dependents.items():
            relies = "; ".join(f"{s}: {how}" for s, how in (brief.get("relies") or {}).items())
            changes = "\n".join(lines[s] for s in brief.get("relies") or {} if s in lines)
            dependent_jobs.append((other, relies, changes, brief))
        while frontier and level <= bound["depth"]:
            room = bound["calls"] - state["calls"]
            jobs = []
            for parent, children in frontier.items():
                if parent not in ancestors:
                    cut.append({"solution_id": parent, "why": "no brief was prepared for this scope"})
                    continue
                if len(jobs) >= room:
                    cut.append({"solution_id": parent, "why": f"the call cap of {bound['calls']} was reached"})
                    continue
                children_text = "\n".join(lines.get(c, f"- {c}") for c in children)
                prompt = PARENT_ASK.format(prompt=ancestors[parent].get("prompt", ""), children=children_text, request=request, rules=RULES)
                jobs.append((parent, children, prompt))
            room_for_dependents = max(room - len(jobs), 0) if level == 1 else 0
            take_now = dependent_jobs[:room_for_dependents] if level == 1 else []
            if level == 1:
                for other, _, _, _ in dependent_jobs[room_for_dependents:]:
                    cut.append({"solution_id": other, "why": f"the call cap of {bound['calls']} was reached before this dependent"})
            answers = self.parallel([lambda p=p: model(p) for _, _, p in jobs]
                                    + [lambda d=d: model(DEPENDENT_ASK.format(prompt=d[3].get("prompt", ""), relies=d[1], changes=d[2] or "(no finding)", rules=RULES))
                                       for d in take_now], bound["width"])
            next_frontier: Dict[str, List[str]] = {}
            for (parent, children, _), got in zip(jobs, answers[:len(jobs)]):
                entry = {"solution_id": parent, "name": ancestors[parent].get("name", parent), "level": level, "children": children,
                         "serves_purpose": got.get("serves_purpose"), "milestone_effect": str(got.get("milestone_effect") or ""),
                         "siblings_affected": [str(s) for s in listed(got.get("siblings_affected"))], "metric_update": str(got.get("metric_update") or ""),
                         "combination_effect": got.get("combination_effect"), "why": str(got.get("why") or ""), **({"error": got["error"]} if got.get("error") else {})}
                parents.append(entry)
                lines[parent] = parent_line(entry)
                above = ancestors[parent].get("parent") or ""
                if got.get("combination_effect") is False:
                    stopped.append({"solution_id": parent, "level": level, "why": "its pass found no effect on how its children combine"})
                elif above and above not in by_id:
                    next_frontier.setdefault(above, []).append(parent)
            if level == 1:
                dependents_out = [{"solution_id": d[0], "name": d[3].get("name", d[0]), "relies_on": sorted((d[3].get("relies") or {}).keys()),
                                        "still_holds": got.get("still_holds"), "why": str(got.get("why") or ""), **({"error": got["error"]} if got.get("error") else {})}
                                       for d, got in zip(take_now, answers[len(jobs):])]
            frontier, level = next_frontier, level + 1
        for parent in frontier:
            cut.append({"solution_id": parent, "why": f"the depth cap of {bound['depth']} levels was reached"})
        if level == 1 and dependent_jobs:      # no scope above any relevant solution: the dependents still get their passes
            room = max(bound["calls"] - state["calls"], 0)
            take_now = dependent_jobs[:room]
            cut += [{"solution_id": d[0], "why": f"the call cap of {bound['calls']} was reached before this dependent"} for d in dependent_jobs[room:]]
            answers = self.parallel([lambda d=d: model(DEPENDENT_ASK.format(prompt=d[3].get("prompt", ""), relies=d[1], changes=d[2] or "(no finding)", rules=RULES))
                                     for d in take_now], bound["width"])
            dependents_out = [{"solution_id": d[0], "name": d[3].get("name", d[0]), "relies_on": sorted((d[3].get("relies") or {}).keys()),
                                    "still_holds": got.get("still_holds"), "why": str(got.get("why") or ""), **({"error": got["error"]} if got.get("error") else {})}
                                   for d, got in zip(take_now, answers)]
        return {"findings": findings, "parents": parents, "dependents": dependents_out, "calls": state["calls"], "cut": cut, "stopped_at": stopped}

    @staticmethod
    def parallel(jobs: Sequence[Callable[[], Any]], width: int) -> List[Any]:
        if not jobs:
            return []
        with ThreadPoolExecutor(max_workers=max(1, min(width, len(jobs)))) as pool:
            return list(pool.map(lambda job: job(), jobs))
