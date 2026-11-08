"""The choice of arm for a consumer: the cascade rule over the arms its providers allow, then public priors, then idea ratings."""
import json

from hubofhubs.the_world.tools.delegated_agent_sessions import arm_choice

CASCADE = ("idea [kind=idea | scale=s | min-pass-rate=0.75] > offline [real=no | gate=all-pass] > "
           "one [sample=sample:1 | real=yes | gate=all-pass] > staged [sample=sample:6 | real=yes | gate=competitive] > whole [sample=full | real=yes]")

CLAUDE_FAST = "subprocess_goal_runner@provider=anthropic,tier=fast"
CLAUDE_BEST = "subprocess_goal_runner@provider=anthropic,tier=best"
GEMINI_FAST = "opencode_runner@provider=gemini,tier=fast"
CODEX = "codex_cli_runner@provider=openai,tier=fast"


def row(impl, passed, cases, balanced, sample):
    return {"impl": impl, "component": "agent_sessions", "cases": str(cases), "passed": str(passed), "balanced": str(balanced),
            "sample": sample, "cases_sha": "abc", "model_calls": str(cases), "cost_usd": "0.01", "seconds": "10", "date": "2026-11-08",
            "dev": f"{passed}/{cases}", "heldout": "0/0"}


def snapshot(rows):
    return {"cascade": CASCADE, "rows": rows}


MEASURED = snapshot({
    CLAUDE_FAST: {"3": row(CLAUDE_FAST, 6, 6, 0.95, "sample:6")},
    CLAUDE_BEST: {"3": row(CLAUDE_BEST, 6, 6, 0.90, "sample:6")},
    GEMINI_FAST: {"3": row(GEMINI_FAST, 6, 6, 0.98, "sample:6")},
})


def test_only_arms_the_consumer_can_run():
    got = arm_choice.choose_agent_arm(["anthropic"], snapshot=MEASURED, priors=[], ideas=[])
    assert got.arm == CLAUDE_FAST and got.basis == "measured" and got.stage == "staged"
    both = arm_choice.choose_agent_arm(["anthropic", "google"], snapshot=MEASURED, priors=[], ideas=[])
    assert both.arm == GEMINI_FAST and both.provider == "gemini" and both.harness == "opencode_runner"


def test_a_later_stage_wins_over_a_better_earlier_one():
    rows = {CLAUDE_FAST: {"2": row(CLAUDE_FAST, 1, 1, 0.99, "sample:1")},
            CLAUDE_BEST: {"2": row(CLAUDE_BEST, 1, 1, 0.97, "sample:1"), "3": row(CLAUDE_BEST, 6, 6, 0.90, "sample:6")}}
    got = arm_choice.choose_agent_arm(["anthropic"], snapshot=snapshot(rows), priors=[], ideas=[])
    assert got.arm == CLAUDE_FAST and "held in place" in got.reason   # it beat the leader at the shared earlier stage and is not yet run later


def test_public_prior_then_idea_when_nothing_eligible_is_measured():
    priors = [{"arm_id": CODEX, "prior": "0.5", "grade": "C", "reason": "public board"},
              {"arm_id": "opencode_runner@provider=openai,tier=fast", "prior": "0.9", "grade": "D", "reason": "one blog"}]
    got = arm_choice.choose_agent_arm(["openai"], snapshot=MEASURED, priors=priors, ideas=[])
    assert got.arm == CODEX and got.basis == "public prior" and "grade C" in got.reason   # a D grade is not usable
    ideas = [{"arm": "opencode_runner@provider=openai,tier=fast", "problem_fit": "4", "purpose_fit": "4", "real_conditions": "3",
              "cost_and_risk": "3", "checkability": "4"}]
    got = arm_choice.choose_agent_arm(["openai"], snapshot=MEASURED, priors=[], ideas=ideas)
    assert got.basis == "idea" and got.score == 0.9 and "not measured" in got.reason


def test_no_eligible_arm():
    assert arm_choice.choose_agent_arm([], snapshot=MEASURED, priors=[], ideas=[]) is None
    assert arm_choice.choose_agent_arm(["unknown-provider"], snapshot=MEASURED, priors=[], ideas=[]) is None


def test_the_shipped_snapshot_reads(tmp_path):
    shipped = arm_choice.read_snapshot()
    assert "cascade" in shipped and isinstance(shipped.get("rows"), dict)
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert arm_choice.read_snapshot(bad) == {}
    json.dumps(shipped)


def test_the_prior_fallback_weighs_cost_and_time_like_the_measured_stage():
    balance = {"weights": {"accuracy": 0.7, "cost": 0.15, "time": 0.15}, "cost_per_case_usd": 0.10, "seconds_per_case": 120}
    priors = [{"arm_id": CLAUDE_BEST, "prior": "0.65", "grade": "B", "cost_per_case_usd": "0.09", "seconds_per_case": "110"},
              {"arm_id": CLAUDE_FAST, "prior": "0.55", "grade": "C", "cost_per_case_usd": "0.005", "seconds_per_case": "20"}]
    got = arm_choice.choose_agent_arm(["anthropic"], snapshot={"cascade": CASCADE, "rows": {}, "balance": balance}, priors=priors, ideas=[])
    assert got.arm == CLAUDE_FAST and got.basis == "public prior"   # 0.7*0.55 + cheap and fast beats 0.7*0.65 at nearly the whole budget
    unpriced = [dict(priors[0]), {"arm_id": CLAUDE_FAST, "prior": "0.55", "grade": "C"}]
    got = arm_choice.choose_agent_arm(["anthropic"], snapshot={"cascade": CASCADE, "rows": {}, "balance": balance}, priors=unpriced, ideas=[])
    assert got.arm == CLAUDE_BEST   # a row that states no cost is never counted as free


def test_hard_work_uses_its_own_metric_and_falls_back_to_ordinary_work():
    hard = {"cascade": CASCADE, "rows": {CLAUDE_BEST: {"4": row(CLAUDE_BEST, 7, 7, 0.8, "")}, CLAUDE_FAST: {"4": row(CLAUDE_FAST, 3, 7, 0.5, "")}}}
    snap = dict(MEASURED, kinds={"hard": hard})
    got = arm_choice.choose_agent_arm(["anthropic"], difficulty="hard", snapshot=snap, priors=[], ideas=[])
    assert got.arm == CLAUDE_BEST and got.reason.startswith("for hard work")
    assert arm_choice.choose_agent_arm(["anthropic"], snapshot=snap, priors=[], ideas=[]).arm == CLAUDE_FAST
    assert arm_choice.choose_agent_arm(["gemini"], difficulty="hard", snapshot=snap, priors=[], ideas=[]).arm == GEMINI_FAST
