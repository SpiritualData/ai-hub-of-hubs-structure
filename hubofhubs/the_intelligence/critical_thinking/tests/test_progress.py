"""The increment rule, the bookkeeping refusal, measuring an increment and the composed progress step, on generic fixtures (no consumer data)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from hubofhubs.the_intelligence.critical_thinking.decision_check.agreement import MajorityVote  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.esoi_application.apply import RecordFieldEdit  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.flow import CriticalThinkingComposition  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.goal_completion.done_evidence import measure  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.metric_upkeep.upkeep import RecordFieldUpkeep  # noqa: E402
from hubofhubs.the_intelligence.critical_thinking.pursuit import (  # noqa: E402
    DELIVERABLE, EVIDENCE, METRIC_READ, REFUSED_BOOKKEEPING, BoundedReplan, Increment, choose_increment, doable_by_ai, only_bookkeeping_writes)

MILESTONE = {"solution_id": "sol-a", "name": "Launch tutorials published", "done_when": "Six tutorials are published", "moved_by": "person",
             "records": ["sol-a", "m-pub"], "lands_on": {"title_prefix": "T1 "}}
MEANS = [{"name": "write_text"}, {"name": "publish_video", "outward": True}, {"name": "web_search"}]
SCRIPT = {"kind": "deliverable", "actor": "ai", "inputs": ["sol-a"], "tools": ["write_text"], "checks": [True, True], "size": "inline",
          "requirements": ["has an opening", "has a call to action"]}
PUBLISH = {"kind": "deliverable", "actor": "ai", "inputs": ["sol-a"], "tools": ["publish_video"], "checks": [True, True]}
RESEARCH = {"kind": "evidence", "actor": "ai", "inputs": ["sol-a"], "tools": ["web_search"], "checks": [True, True]}


def test_an_item_is_the_ais_only_when_inputs_exist_no_tool_is_outward_and_both_checks_agree():
    assert doable_by_ai(SCRIPT, MEANS, MILESTONE["records"])
    assert not doable_by_ai(PUBLISH, MEANS, MILESTONE["records"])                       # publishing is outward: the person's
    assert not doable_by_ai(dict(SCRIPT, checks=[True, False]), MEANS, MILESTONE["records"])
    assert not doable_by_ai(dict(SCRIPT, inputs=["missing-record"]), MEANS, MILESTONE["records"])
    assert not doable_by_ai(dict(SCRIPT, actor="person"), MEANS, MILESTONE["records"])


def test_the_ladder_takes_the_first_rung_that_applies():
    child = [{"metric_id": "m-pub", "action": "define_intermediate", "child_metric": {"id": "m-pub-intermediate", "total": "6"}}]
    found = choose_increment(MILESTONE, child, [RESEARCH, SCRIPT], MEANS)
    assert found.kind == DELIVERABLE and found.measure_id == "m-pub-intermediate" and found.method == "rubric" and found.lands_on["title_prefix"] == "T1 "
    read = [{"metric_id": "m-pub", "action": "read", "reading": {"value": 1}}]
    assert choose_increment(MILESTONE, read, [PUBLISH], MEANS).kind == METRIC_READ          # the only deliverable is outward, so the reading is next
    assert choose_increment(MILESTONE, [], [PUBLISH, RESEARCH], MEANS).kind == EVIDENCE
    assert choose_increment(MILESTONE, [], [PUBLISH], MEANS) is None


def test_pursue_refuses_bookkeeping_alone_on_a_progress_turn_only():
    met = lambda outcome: {"met": True}     # noqa: E731
    owner_only = {"text": "Ann owns it, due Friday.", "writes": [{"fields": ["assignee", "due_date"]}]}
    refused = BoundedReplan().pursue("move it forward", "", owner_only, check=met, progress=True)
    assert refused["status"] == REFUSED_BOOKKEEPING and not refused["met"]
    assert BoundedReplan().pursue("put the office hour on the quest", "", owner_only, check=met)["status"] == "met"     # a bookkeeping request is done when its bookkeeping is
    with_work = dict(owner_only, increments=[{"measure_id": "m", "before": 0}])
    assert BoundedReplan().pursue("move it forward", "", with_work, check=met, progress=True)["status"] == "met"
    assert only_bookkeeping_writes(owner_only["writes"]) and not only_bookkeeping_writes([{"fields": ["description"]}])


def judge(requirement, part):
    return requirement.split()[-1] in part.lower()


def test_measure_scores_parts_against_requirements_by_a_judge_and_an_empty_artifact_is_zero():
    inc = Increment(DELIVERABLE, "m-x", requirements=["has an opening", "has a call to action"], method="rubric")
    assert measure(inc, None, judge).value == 0
    after = measure(inc, {"parts": ["An opening line. Then a call to action.", "only an opening"]}, judge, total=6)
    assert after.value == 1 and after.total == 6 and after.method == "rubric"
    evidence = measure(Increment(EVIDENCE, "m-e", method="evidence"), {"questions": [{"answer": "yes", "source": "a page"}, {"answer": "", "source": ""}]})
    assert (evidence.value, evidence.total) == (1, 2)
    simulated = measure(Increment("simulation", "m-s", method="simulation"), None, reader=lambda: {"value": 3, "as_of": "2030-01-01"})
    assert simulated.simulated and simulated.value == 3


def test_progress_composes_upkeep_the_increment_before_the_work_and_after():
    tables = {"metrics": {"m-pub": {"name": "Tutorials published", "record": "Current value: 0 of 6", "solution_ids": ["sol-a"]}}}
    esoi = RecordFieldEdit(tables)

    def ask(prompt):
        if "Propose ONE intermediate metric" in prompt:
            return json.dumps({"name": "Scripts meeting the rubric", "definition": "Count scripts meeting every rubric item.", "unit": "scripts", "total": 6,
                               "feeds_parent": "Each tutorial needs its script first."})
        return json.dumps({"pick": "tracks", "quote": "Proposed intermediate metric"})
    composition = CriticalThinkingComposition(None, esoi, None, None, MajorityVote(plumbing=None),
                                              RecordFieldUpkeep(esoi=esoi, decision=MajorityVote(plumbing=None)))
    made = composition.progress(MILESTONE, tables["metrics"], [SCRIPT], lambda inc: {"artifact": {"parts": ["An opening. A call to action."]},
                                                                                     "evidence_ref": "goal T1 scripts", "asks": ["Record it.", "Second ask."]},
                                judge=judge, means=MEANS, today="2030-03-10", ask=ask)
    assert made["status"] == "measured" and made["increment"]["measure_id"] == "Scripts meeting the rubric"
    assert (made["before"]["value"], made["after"]["value"], made["after"]["total"]) == (0, 1, 6)
    assert made["asks"] == ["Record it."]          # at most one person-only step, added to the increment
    nothing = composition.progress(MILESTONE, esoi.records["metrics"], [SCRIPT], lambda inc: {"artifact": ""}, judge=judge, means=MEANS, today="2030-03-10", ask=ask)
    assert nothing["status"] == REFUSED_BOOKKEEPING
