"""Solution Passes's passes, the pieces tied to solutions and the write-back, with scripted model answers (no model call)."""
import json

from hubofhubs.the_intelligence.critical_thinking.metric_translation.translation import GoalRecord
from hubofhubs.the_intelligence.critical_thinking.solution_passes.passes import NetworkPasses
from hubofhubs.the_intelligence.critical_thinking.solution_passes.write_back import combined_check, proposals_of
from hubofhubs.the_intelligence.mind.planner.solution_pieces import tie

BRIEFS = {
    "solutions": [{"solution_id": "a", "name": "A", "prompt": "PROMPT-A", "chain": ["p", "top"]},
                  {"solution_id": "b", "name": "B", "prompt": "PROMPT-B", "chain": ["p", "top"]}],
    "ancestors": {"p": {"solution_id": "p", "name": "P", "prompt": "PROMPT-P", "parent": "top", "children": ["a", "b"]},
                  "top": {"solution_id": "top", "name": "Top", "prompt": "PROMPT-TOP", "parent": "", "children": ["p"]}},
    "dependents": {"d": {"solution_id": "d", "name": "D", "prompt": "PROMPT-D", "relies": {"a": "uses it"}}},
}


def scripted(combination=True):
    seen = []

    def ask(prompt):
        seen.append(prompt.split("\n", 1)[0])
        if prompt.startswith("PROMPT-P") or prompt.startswith("PROMPT-TOP"):
            return json.dumps({"combination_effect": combination if prompt.startswith("PROMPT-P") else False, "why": "w", "metric_update": ""})
        if prompt.startswith("PROMPT-D"):
            return json.dumps({"still_holds": False, "why": "its input changes"})
        sid = prompt[7].lower()
        return "```json\n" + json.dumps({"applies": True, "needs": f"work on {sid}", "target": {"metric_id": f"metric-{sid}", "value": "9", "done_when": f"{sid} done"},
                                         "knowledge": [{"claim": f"lesson {sid}", "kind": "lesson", "source": "results"}], "candidates": ["New Arm"]}) + "\n```"
    return ask, seen


def test_every_solution_gets_its_own_pass_then_parents_climb_until_no_effect():
    ask, seen = scripted()
    out = NetworkPasses(None).consider("change it", BRIEFS, ask=ask)
    assert [f["solution_id"] for f in out["findings"]] == ["a", "b"] and out["findings"][0]["target"]["metric_id"] == "metric-a"
    assert [(p["solution_id"], p["level"]) for p in out["parents"]] == [("p", 1), ("top", 2)]
    assert out["stopped_at"][0]["solution_id"] == "top" and out["dependents"][0]["still_holds"] is False
    assert out["calls"] == 5 and sorted(seen) == ["PROMPT-A", "PROMPT-B", "PROMPT-D", "PROMPT-P", "PROMPT-TOP"]


def test_a_scope_with_no_effect_stops_the_climb_and_caps_never_cut_a_solution_pass():
    ask, _ = scripted(combination=False)
    out = NetworkPasses(None).consider("change it", BRIEFS, ask=ask, limits={"calls": 0})
    assert len(out["findings"]) == 2 and out["parents"] == []
    assert {c["solution_id"] for c in out["cut"]} == {"p", "d"}
    stopped = NetworkPasses(None).consider("change it", BRIEFS, ask=ask)
    assert [p["solution_id"] for p in stopped["parents"]] == ["p"] and stopped["stopped_at"][0]["solution_id"] == "p"


def test_a_consumers_own_pass_replaces_the_model_pass_for_its_solution():
    ask, seen = scripted()
    out = NetworkPasses(None).consider("change it", BRIEFS, own_passes={"a": lambda request, brief: {"applies": True, "needs": "the measured increment"}}, ask=ask)
    assert out["findings"][0]["by"] == "own pass" and out["findings"][0]["needs"] == "the measured increment" and "PROMPT-A" not in seen


def test_pieces_are_tied_to_solutions_and_held_to_their_own_targets():
    ask, _ = scripted()
    considered = {**NetworkPasses(None).consider("change it", BRIEFS, ask=ask), "prompts": {"a": "PROMPT-A", "b": "PROMPT-B"}}
    pieces = tie([{"piece": "work on a", "tool": "delegated-agent-sessions", "sub_goal": {}}], considered)
    assert [p["solution_id"] for p in pieces] == ["a", "b"]
    assert pieces[0]["sub_goal"]["done_standard"] == "a done (metric-a 9)" and pieces[0]["request"]["brief"].startswith("PROMPT-A")
    target = GoalRecord().translate("change it", solutions=[{**f["target"], "solution_id": f["solution_id"], "name": f["name"]} for f in considered["findings"]])
    assert target["metric"] == "each relevant solution's own metric" and "metric-b" in target["done_standard"]


def test_write_back_proposes_sourced_knowledge_results_and_candidates_and_a_broken_dependent_blocks_the_whole():
    ask, _ = scripted()
    considered = NetworkPasses(None).consider("change it", BRIEFS, ask=ask)
    pieces = [{"solution_id": "a", "piece": "x", "metric_id": "metric-a", "value": "9", "done_standard": "a done", "met": True, "reason": ""},
              {"solution_id": "b", "piece": "y", "metric_id": "metric-b", "value": "9", "done_standard": "b done", "met": False, "reason": "no"}]
    changes = proposals_of(considered, {"pieces": pieces}, "2026-11-08")
    tables = [c["table"] for c in changes]
    assert tables.count("knowledge") == 4 and tables.count("implementations") == 2
    assert all(c["fields"]["source"] for c in changes if c["table"] == "knowledge")
    combined = combined_check(pieces, considered)
    assert combined["met"] is False and any("no longer gets" in r for r in combined["reasons"]) and any("b did not meet" in r for r in combined["reasons"])


def test_a_piece_short_of_its_rubric_is_split_worked_part_by_part_recombined_and_rechecked():
    from hubofhubs.the_intelligence.critical_thinking.solution_passes.depth import build_out
    rubric = ["names the audience", "gives three steps", "ends with one ask"]

    def check(text, item):
        missing = [r for r in item["requirements"] if r not in text]
        return {"met": not missing, "score": 1 - len(missing) / len(item["requirements"]), "missing": missing}

    def work(item):
        return " ".join(item["requirements"]) if len(item["requirements"]) == 1 else "names the audience"

    out = build_out({"goal": "a script", "requirements": rubric, "prompt": "P"}, work, check)
    assert out["before"] < 1 and out["after"] == 1 and out["met"] and out["levels"] == 1
    capped = build_out({"goal": "a script", "requirements": rubric, "prompt": "P"}, work, check, budget={"calls": 3})
    assert capped["stopped"] == "budget" and not capped["met"]


def test_the_verbatim_combine_keeps_each_part_as_written_even_when_the_call_rewrites_it():
    from hubofhubs.the_intelligence.critical_thinking.solution_passes.depth import verbatim_combine
    parts = [{"requirements": ["one ask"], "text": "Reply with your start date."}, {"requirements": ["three steps"], "text": "1. Read.\n2. Join.\n3. Post."}]
    combine = verbatim_combine(lambda prompt: "Welcome. 1. Read.\n2. Join.\n3. Post. Please tell us when you can start.")
    out = combine({"goal": "a welcome"}, "Welcome.", parts)
    assert "1. Read." in out and "Reply with your start date." in out


def test_each_solution_finding_is_handed_on_before_the_parent_passes():
    ask, _ = scripted()
    seen = []
    out = NetworkPasses(None).consider("change it", BRIEFS, ask=ask, on_finding=lambda f: seen.append((f["solution_id"], len(seen))))
    assert sorted(s for s, _ in seen) == ["a", "b"] and out["parents"]
