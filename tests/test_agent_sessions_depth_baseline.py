"""The depth cases of Delegated Agent Sessions: the naive baseline fails every one, a hand-written correct result passes every one, the case file
is what its builder writes, and the case data reaches only an arm whose constructor takes it. Free: no model call."""
import functools
import importlib
import json
import re
import sys
from pathlib import Path

import pytest

EVALUATION = Path(__file__).resolve().parent.parent / "evaluation"
sys.path.insert(0, str(EVALUATION))
FOLDER = EVALUATION / "agent_sessions_depth"


def module(name):
    return importlib.import_module(f"agent_sessions_depth.{name}")


def cases():
    return json.loads((FOLDER / "cases.json").read_text(encoding="utf-8"))


def test_cases_json_is_what_the_builder_writes():
    built = module("build_cases").cases()
    assert json.loads(json.dumps(built)) == cases()


def test_every_case_has_a_goal_and_a_code_check():
    for case in cases():
        assert case["goal"] and case["stratum"]
        assert case.get("expect_report") or case.get("expect_json") or case.get("hidden_tests") or case.get("expect_summary"), case["id"]


@pytest.mark.parametrize("case", cases(), ids=lambda c: c["id"])
def test_the_parrot_baseline_fails_the_case(case):
    parrot = module("broken.parrot").build(None)
    assert not module("score").score_case(parrot, case)["ok"]


@pytest.mark.parametrize("case", cases(), ids=lambda c: c["id"])
def test_a_hand_written_correct_result_passes_the_case(case):
    reference = module("reference").build(None)
    row = module("score").score_case(reference, case)
    assert row["ok"], row["note"]


def test_a_correct_result_that_touches_a_fixed_file_fails():
    case = next(c for c in cases() if c["id"] == "depth-solution-records")
    reference = module("reference").build(None)

    def meddling(kind, args):
        (Path(args["root"]) / "report/rounding.py").write_text("def round_half_even(value):\n    return value\n", encoding="utf-8")
        return reference(kind, args)

    row = module("score").score_case(meddling, case)
    assert not row["ok"] and "files changed" in row["note"]


def test_a_wrong_claim_repeated_fails_the_recall_case():
    case = next(c for c in cases() if c["id"] == "depth-recall-known")
    reference = module("reference").build(None)

    def believer(kind, args):
        result = reference(kind, args)
        (Path(args["root"]) / "answer.json").write_text(json.dumps({"retry_limit": 9, "source_file": "config/settings.ini"}), encoding="utf-8")
        return result

    assert not module("score").score_case(believer, case)["ok"]


def test_the_skills_folder_and_the_known_text_reach_only_an_arm_that_takes_them():
    score = module("score")

    class Takes:
        def __init__(self, config=None, *, settings=None, skills_dir=None, recall=None, **ignored):
            pass

    class Refuses:
        def __init__(self, config=None, *, settings=None, **ignored):
            pass

    args = {"skills_dir": "/somewhere", "known": "a finding"}
    taken = score.extras_for(Takes, args)
    assert taken["skills_dir"] == "/somewhere" and taken["recall"]("any goal") == "a finding"
    assert set(score.extras_for(functools.partial(Takes, provider="x"), args)) == {"skills_dir", "recall"}
    assert score.extras_for(Refuses, args) == {}
    assert score.extras_for(Takes, {"goal": "g"}) == {}


def test_the_skills_case_hands_the_skills_folder_to_the_arm_and_leaves_the_work_folder_without_the_rule():
    case = next(c for c in cases() if c["id"] == "depth-skills-folder")
    assert not any("shipping" in text.lower() and "75.00" in text for text in case["files"].values())
    seen = {}

    def spy(kind, args):
        seen.update(args)
        return module("reference").build(None)(kind, args)

    module("score").score_case(spy, case)
    assert "skills_dir" in seen and "known" not in seen


def case_of(case_id):
    return next(c for c in cases() if c["id"] == case_id)


def run_with(case_id, after):
    """The reference solution, then ``after(args, reply)`` changes what the run left or reported."""
    reference = module("reference").build(None)

    def run(kind, args):
        reply = reference(kind, args)
        return after(args, reply) or reply
    return module("score").score_case(run, case_of(case_id))


def test_the_new_cases_need_their_own_strata_and_the_set_keeps_the_first_five():
    ids = [c["id"] for c in cases()]
    assert ids[:5] == ["depth-parts-sites", "depth-solution-records", "depth-skills-folder", "depth-recall-known", "depth-small-simple"]
    assert ids[5:] == ["depth-context-load", "depth-two-level-records", "depth-verify-claims", "depth-small-lookup"]


def test_the_context_case_is_large_and_a_proposed_or_stale_value_fails():
    case = case_of("depth-context-load")
    files = [t for n, t in case["files"].items() if n.startswith("depots/")]
    assert len(files) >= 30 and sum(map(len, files)) >= 90_000 and all(len(t) >= 2_000 for t in files)    # tens of files of real length
    first = case["expect_report"][0]
    stale = next(t for t in files if "dispatch cutoff is" in t)
    old = re.search(r"cutoff is (\d+:\d+)", stale).group(1)

    def old_value(args, reply):
        reply.output = reply.output.replace(first["facts"][0], old)
    row = run_with("depth-context-load", old_value)
    assert not row["ok"] and first["part"] in row["note"]


def test_the_two_level_case_has_a_record_tree_with_a_milestone_and_a_hidden_test_per_solution():
    case = case_of("depth-two-level-records")
    assert set(case["expect_status"]["tests"]) == {"shop-report", "pricing", "orders", "order-totals", "shipping-fees", "labels"}
    assert set(case["expect_status"]["tests"].values()) <= set(case["hidden_tests"])
    solutions = case["files"]["esoi/solutions.csv"]
    assert "pricing; orders; labels" in solutions and "order-totals; shipping-fees" in solutions         # two levels: the top, orders, and orders' own children
    assert not any("carrier_rates" in n for n in case["files"] if n.endswith(".csv"))


@pytest.mark.parametrize("claim", ["all met", "all unmet", "parent only"])
def test_a_wrong_milestone_report_fails_the_two_level_case(claim):
    def report(args, reply):
        sids = ["pricing", "order-totals", "labels", "shipping-fees", "orders", "shop-report"]
        if claim == "all met":
            reply.output = "\n".join(f"{s}: met" for s in sids)
        elif claim == "all unmet":
            reply.output = "\n".join(f"{s}: unmet" for s in sids)
        else:
            reply.output = "\n".join(f"{s}: {'met' if s != 'shop-report' else 'unmet'}" for s in sids)       # reports the unmet child as met
    row = run_with("depth-two-level-records", report)
    assert not row["ok"] and "reported" in row["note"]


def test_a_fabricated_rate_table_does_not_make_the_milestone_met_and_the_honest_report_passes():
    def invented(args, reply):
        Path(args["root"], "shop/shipping.py").write_text("def shipping_cents(weight_grams, zone):\n    return 500\n", encoding="utf-8")     # no table exists: a guess
        reply.output = reply.output.replace("shipping-fees: unmet", "shipping-fees: met").replace("orders: unmet", "orders: met").replace("shop-report: unmet", "shop-report: met")
    assert not run_with("depth-two-level-records", invented)["ok"]
    assert run_with("depth-two-level-records", lambda args, reply: None)["ok"]


def test_the_status_line_reader_takes_the_last_statement_and_marks_and_not_met():
    score = module("score")
    assert score.stated_status("- **pricing**: met\n`labels`: not met\nlabels: unmet\norders - unmet", "labels") == "unmet"
    assert score.stated_status("| pricing | met |\npricing: met", "pricing") == "met"
    assert score.stated_status("pricing-extra: met", "pricing") == "" and score.stated_status("nothing", "pricing") == ""


def test_copying_the_recap_or_an_unsourced_cause_fails_the_verification_case():
    expect = case_of("depth-verify-claims")["expect_summary"]

    def copy_recap(args, reply):
        Path(args["root"], "summary.md").write_text(f"Total visits: {expect['recap_total']:,} (recap.md).\nBest month: {expect['recap_best']}.\n", encoding="utf-8")
    assert "recap" in run_with("depth-verify-claims", copy_recap)["note"] or not run_with("depth-verify-claims", copy_recap)["ok"]

    def cause_as_fact(args, reply):
        path = Path(args["root"], "summary.md")
        path.write_text(path.read_text(encoding="utf-8") + "March was best because the newsletter launch drove a 30 percent jump.\n", encoding="utf-8")
    row = run_with("depth-verify-claims", cause_as_fact)
    assert not row["ok"] and "unsourced" in row["note"]

    def no_source(args, reply):
        Path(args["root"], "summary.md").write_text(f"Total visits: {expect['total']:,}.\nBest month: {expect['best']}.\n", encoding="utf-8")
    assert "source" in run_with("depth-verify-claims", no_source)["note"]


def test_the_small_lookup_case_is_offered_by_file_count_and_a_wrong_locker_fails():
    case = case_of("depth-small-lookup")
    assert len(case["files"]) >= 12 and sum(map(len, case["files"].values())) < 2_000            # many files, almost no text: delegation can only cost

    def wrong(args, reply):
        Path(args["root"], "answer.json").write_text(json.dumps({"note": "note_01.txt", "locker": 7}), encoding="utf-8")
    assert not run_with("depth-small-lookup", wrong)["ok"]


def test_the_row_records_sub_agent_use_per_case_for_a_run_that_reports_it():
    from agent_sessions_hard import score as hard
    reply = module("reference").Reply("x")
    reply.subagent_report = {"offered": ["read-files", "response-quality"], "ran": {"read-files": 2}, "refused": {"general-purpose": 1}}
    fields = hard.run_fields(reply)
    assert fields == {"turns": 1, "subagent_calls": 0, "agents_offered": 2, "subagent_refused": 1, "subagents": "read-files=2"}
    assert hard.run_fields(None) == {} and hard.run_fields(object()) == {}


def test_the_two_level_records_choose_one_agent_per_solution_for_the_goal(tmp_path):
    from hubofhubs.the_world.tools.delegated_agent_sessions import solution_agents as agents
    case = case_of("depth-two-level-records")
    for name, text in case["files"].items():
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text(text, encoding="utf-8")
    specs, net = agents.choose_solutions(case["goal"], str(tmp_path))
    chosen = {s.solution for s in specs}
    assert {"pricing", "order-totals", "shipping-fees", "labels"} <= chosen and all(net.has(s) for s in chosen)
