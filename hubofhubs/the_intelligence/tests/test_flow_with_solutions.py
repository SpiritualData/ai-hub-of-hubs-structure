"""One request through the Intelligence flow with ESOI records: relevant solutions, one pass each, the goal held to their own targets, pieces tied to
solutions, a piece short of its target returned to the Planner, and the write-back (scripted model answers, the hub's own public records)."""
import json
from pathlib import Path

from hubofhubs.the_intelligence.critical_thinking.flow import CriticalThinkingComposition
from hubofhubs.the_intelligence.critical_thinking.metric_translation.translation import GoalRecord
from hubofhubs.the_intelligence.critical_thinking.solution_passes.passes import NetworkPasses
from hubofhubs.the_intelligence.flow import IntelligenceComposition
from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import network_of
from hubofhubs.the_intelligence.subconscious.relevant_solutions.records_index import RecordsIndex
from hubofhubs.the_intelligence.subconscious.solution_briefs import briefs

ROOT = Path(__file__).resolve().parents[3]
REQUEST = "Should Cards From Files switch to the Graphify arm?"


class Quiet:
    def __getattr__(self, name):
        return lambda *args, **kwargs: {}


class Subconscious:
    def prepare(self, request, files=None, budget_tokens=4000, records=None, knowledge="retrieved", limit=5, depth=3):
        found = RecordsIndex().relevant(request, records, limit, depth)["solutions"]
        return {"cards": [], "solutions": briefs(network_of(records), found, request, knowledge)}


class Goal:
    def __init__(self):
        self.calls = 0

    def check(self, goal, done_standard, outcome):
        self.calls += 1
        return {"met": self.calls > 2, "reason": "first try short"}


class Mind:
    def __init__(self):
        self.seen = []

    def think(self, request, considered=None, unmet=None, **kwargs):
        self.seen.append((considered, unmet))
        return {"text": "kept the selected arm", "results": [{"piece": "keep the arm", "solution_id": "cards-from-files", "text": "kept", "items": []}]}


class Records:
    def __init__(self):
        self.changes = []

    def apply(self, change):
        self.changes.append(change)
        return {"applied": True}


def ask(prompt):
    if "Its children's own passes found" in prompt:
        return json.dumps({"combination_effect": False, "why": "none"})
    if "This solution relies on" in prompt:
        return json.dumps({"still_holds": True})
    return json.dumps({"applies": True, "needs": "a measured comparison", "target": {"metric_id": "metric-cards-from-files", "value": "0.61", "done_when": "a run on the same cases"},
                       "conflicts": [{"record": "graphify_files", "conflict": "passed 3 of 63"}], "knowledge": [{"claim": "popularity is not a result", "source": "results"}]})


def test_the_flow_considers_each_solution_ties_pieces_returns_a_short_piece_and_writes_back():
    goal, mind, records = Goal(), Mind(), Records()
    critical = CriticalThinkingComposition(GoalRecord(), records, goal, Quiet(), None, None, NetworkPasses(None))
    flow = IntelligenceComposition(Quiet(), Subconscious(), critical, mind, Quiet(), Quiet(), Quiet())
    out = flow.process(REQUEST, records=str(ROOT), ask=ask, now="2026-11-08T00:00:00")
    considered = out["considered"]
    assert considered["findings"][0]["solution_id"] == "cards-from-files" and "cards-from-files" in considered["prompts"]
    assert mind.seen[0][0]["findings"] and mind.seen[1][1]["failed_pieces"] == ["keep the arm"]      # short of its target: back to the Planner
    assert out["attempts"] == 2
    assert any(c.get("table") == "knowledge" and "popularity" in c["fields"]["claim"] for c in records.changes)
