"""The metric's selection rule: floors per stage, repeated runs, pass rate dominates, cost and time break ties within noise."""
from hubofhubs.the_world.tools.delegated_agent_sessions import selection_stages as stages


def run(passed, cases, cost, seconds):
    return {"passed": passed, "cases": cases, "cost_usd": cost, "seconds": seconds}


OPEN = {"a": [run(18, 18, 0.8, 100)], "b": [run(18, 18, 0.5, 100)], "c": [run(18, 18, 0.1, 50)]}


def test_a_cheap_six_of_nine_arm_never_beats_an_eight_of_nine_arm():
    hard = {"a": [run(8, 9, 0.9, 300)] * 3, "c": [run(6, 9, 0.1, 100)] * 3}
    verdict = stages.decide(OPEN, hard, arms=["a", "c"])
    assert verdict.winner == "a"


def test_cost_breaks_a_tie_within_noise():
    hard = {"a": [run(8, 9, 0.9, 300)] * 3, "b": [run(8, 9, 0.5, 300)] * 3}
    verdict = stages.decide(OPEN, hard, arms=["a", "b"])
    assert verdict.winner == "b" and "cheaper" not in verdict.reason or verdict.winner == "b"


def test_a_significantly_lower_pass_rate_is_not_a_contender_however_cheap():
    hard = {"a": [run(9, 9, 0.9, 300)] * 6, "c": [run(6, 9, 0.01, 10)] * 6}
    assert stages.decide(OPEN, hard, arms=["a", "c"]).winner == "a"


def test_an_arm_below_the_open_ended_floor_is_not_selectable():
    open_runs = {"a": [run(18, 18, 0.8, 100)], "c": [run(15, 18, 0.1, 50)]}
    hard = {"a": [run(7, 9, 0.9, 300)] * 3, "c": [run(9, 9, 0.1, 100)] * 3}
    verdict = stages.decide(open_runs, hard, arms=["a", "c"])
    assert verdict.winner == "a" and verdict.stages["c"]["open_ended"].startswith("stopped")


def test_an_arm_below_the_hard_floor_is_not_selectable():
    hard = {"a": [run(5, 9, 0.9, 300)] * 3}
    verdict = stages.decide(OPEN, hard, arms=["a"])
    assert verdict.winner == "" and verdict.stages["a"]["hard"].startswith("stopped")


def test_an_arm_with_too_few_runs_waits_once_another_arm_has_enough():
    hard = {"a": [run(8, 9, 0.9, 300)] * 3, "c": [run(9, 9, 0.1, 100)]}
    verdict = stages.decide(OPEN, hard, arms=["a", "c"])
    assert verdict.winner == "a" and "needed" in verdict.stages["c"]["repeated"]


def test_with_no_arm_having_enough_runs_the_repeat_stage_skips():
    hard = {"a": [run(8, 9, 0.9, 300)], "c": [run(9, 9, 0.1, 100)]}
    verdict = stages.decide(OPEN, hard, arms=["a", "c"])
    assert verdict.winner == "c" and verdict.stages["c"]["repeated"].startswith("not run")


def test_a_failed_real_task_stops_the_arm():
    hard = {"a": [run(8, 9, 0.9, 300)] * 3}
    verdict = stages.decide(OPEN, hard, {"a": [{"ok": "0"}]}, arms=["a"])
    assert verdict.winner == "" and verdict.stages["a"]["real_task"].startswith("stopped")


def test_the_lead_test_is_esois_and_matches_a_known_value():
    from esoi.optimization.leaderboard import stats
    assert abs(stats.fisher_exact_two_sided(8, 8, 0, 8) - 2 / 12870) < 1e-9   # 2 of C(16, 8) = 12870 tables
    assert stages.lead_shown((8, 8), (0, 8)) and not stages.lead_shown((25, 27), (24, 27))


def test_the_alpha_here_is_the_alpha_the_metric_cascade_declares():
    import csv
    from pathlib import Path
    from esoi.optimization.leaderboard import cascade_stages
    with (Path(__file__).resolve().parent.parent / "metrics.csv").open(newline="", encoding="utf-8") as handle:
        cell = next(r for r in csv.DictReader(handle) if r["metric_id"] == "metric-delegated-agent-sessions-hard")["cascading_conditionals"]
    parsed, problems = cascade_stages.parse(cell)
    assert problems == []
    assert [lead.value for lead in parsed[-1].requirement.whole] == [stages.ALPHA]


HARD = {"a": [run(8, 9, 0.9, 300)] * 3, "b": [run(8, 9, 0.9, 300)] * 3}


def test_without_depth_runs_the_depth_stage_skips_and_nothing_changes():
    verdict = stages.decide(OPEN, HARD, arms=["a", "b"], depth_runs={})
    assert verdict.winner == stages.decide(OPEN, HARD, arms=["a", "b"]).winner
    assert verdict.stages["a"]["depth"].startswith("not run")


def test_an_arm_below_the_depth_floor_is_not_selectable():
    depth = {"a": [run(5, 5, 0.3, 100)] * 3, "b": [run(3, 5, 0.1, 50)] * 3}
    verdict = stages.decide(OPEN, HARD, arms=["a", "b"], depth_runs=depth)
    assert verdict.winner == "a" and verdict.stages["b"]["depth"].startswith("stopped: pass rate")


def test_an_arm_with_too_few_depth_runs_waits_once_another_arm_has_enough():
    depth = {"a": [run(4, 5, 0.3, 100)] * 3, "b": [run(5, 5, 0.1, 50)]}
    verdict = stages.decide(OPEN, HARD, arms=["a", "b"], depth_runs=depth)
    assert verdict.winner == "a" and "needed" in verdict.stages["b"]["depth"]


def test_an_arm_that_passes_every_stage_passes_the_depth_stage_at_the_floor():
    depth = {"a": [run(4, 5, 0.3, 100)] * 3, "b": [run(4, 5, 0.3, 100)] * 3}
    verdict = stages.decide(OPEN, HARD, arms=["a", "b"], depth_runs=depth)
    assert verdict.stages["a"]["depth"].startswith("passed") and verdict.winner == "a"


def test_depth_cost_breaks_a_tie_when_every_contender_ran_the_depth_set():
    hard = {"a": [run(8, 9, 0.5, 300)] * 3, "b": [run(8, 9, 0.6, 300)] * 3}
    depth = {"a": [run(5, 5, 2.5, 100)] * 3, "b": [run(5, 5, 0.5, 100)] * 3}
    assert stages.decide(OPEN, hard, arms=["a", "b"]).winner == "a"
    assert stages.decide(OPEN, hard, arms=["a", "b"], depth_runs=depth).winner == "b"
