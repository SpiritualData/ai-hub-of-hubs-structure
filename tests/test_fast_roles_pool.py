"""The pooled stage of the fast-tier roles: its cases, its readers and its no-model baseline. Offline, no model call."""
import collections
import importlib
import sys
from pathlib import Path

EVALUATION = Path(__file__).resolve().parent.parent / "evaluation"
sys.path.insert(0, str(EVALUATION))
score = importlib.import_module("fast_roles_pool.score")
CASES = score.load_cases()


def test_the_pool_holds_each_roles_cases_with_the_source_of_every_one():
    assert collections.Counter(c["role"] for c in CASES) == {"request_classification": 62, "representative_selection": 9, "folder_view_picking": 41}
    assert len({c["id"] for c in CASES}) == len(CASES) and all(c["source"] for c in CASES)


def test_every_pooled_role_is_a_fast_role_of_the_table():
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers
    for role in score.ROLES:
        assert role_tiers.tier_for(role) == "fast", role


def test_the_replies_are_read_as_the_label_the_source_states():
    ok = {"doability": ('{"ai_can_do": true}', dict(ai_can_do=True)), "assignee": ('{"assignee": "u1", "ai_can_do": false}', dict(assignee="u1", ai_can_do=False))}
    for kind, (reply, expect) in ok.items():
        case = dict(kind=kind, role="x", args=dict(prompt="p", member_ids=["u1"]), expect=expect)
        assert score.score_case(lambda k, a: reply, case)["ok"], kind
        assert not score.score_case(lambda k, a: "not json", case)["ok"], kind
    rank = dict(kind="quest_rank", role="x", args=dict(prompt="p", items=2), expect=dict(chosen=["q1", None]))
    assert score.score_case(lambda k, a: 'x {"results": [{"item": 1, "quest_id": "q1"}, {"item": 2, "quest_id": ""}]}', rank)["ok"]
    assert not score.score_case(lambda k, a: '{"results": [{"item": 1, "quest_id": "q2"}]}', rank)["ok"]


def test_a_goal_handed_to_the_ai_that_a_person_must_keep_is_counted():
    case = dict(kind="doability", role="x", args=dict(prompt="p"), expect=dict(ai_can_do=False))
    assert score.score_case(lambda k, a: '{"ai_can_do": true}', case)["wrong_yes"]


def test_the_no_answer_baseline_fails_every_prompt_case():
    fn = importlib.import_module("fast_roles_pool.broken.no_answer").build(None)
    prompt_cases = [c for c in CASES if c["kind"] != "folder_pick"]
    assert not any(score.score_case(fn, c)["ok"] for c in prompt_cases if c["kind"] != "quest_rank" or c["expect"]["chosen"] != [None])
