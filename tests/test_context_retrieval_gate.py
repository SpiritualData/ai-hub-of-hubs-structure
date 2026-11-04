"""The cascade conditions of context_retrieval (gate.py): per-kind tolerance, case minimums and the source-access gates, on made-up result rows."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evaluation"))

from context_retrieval import gate

COUNTS = "file:63/topic:126/orientation:32/none:32/topic_open:63/grouping:32/memory:47"


def details(**kinds):
    d = {f"{k}_utility": str(v) for k, v in kinds.items()}
    d.update(cases_by_kind=COUNTS, source_calls_max="0", scan_share_max="0.0", out_of_scope="0")
    return d


def verdict(arms):
    return {(arm, name): ok for arm, name, ok, _ in gate.check(arms)}


def test_an_arm_that_wins_one_kind_and_loses_another_beyond_the_tolerance_fails_the_kind_check():
    arms = {"abstaining_hybrid": ("s", details(topic=0.40, memory=0.60)), "greedy": ("s", details(topic=0.60, memory=0.50)),
            "steady": ("s", details(topic=0.45, memory=0.58))}
    got = verdict(arms)
    assert got[("greedy", "kinds")] is False and got[("steady", "kinds")] is True


def test_a_scan_of_the_sources_fails_the_risk_gates_and_an_index_only_arm_passes_them():
    scan = details(topic=0.5)
    scan.update(source_calls_max="892", scan_share_max="1.0", out_of_scope="3")
    got = verdict({"abstaining_hybrid": ("s", details(topic=0.4)), "live_scan": ("s", scan)})
    assert not got[("live_scan", "source-calls")] and not got[("live_scan", "no-full-scan")] and not got[("live_scan", "scope")]
    assert got[("abstaining_hybrid", "source-calls")] and got[("abstaining_hybrid", "no-full-scan")] and got[("abstaining_hybrid", "scope")]


def test_a_new_kind_below_its_minimum_does_not_count_and_two_case_sets_do_not_compare():
    thin = details(topic=0.4)
    thin["cases_by_kind"] = "file:63/memory:10"
    got = verdict({"abstaining_hybrid": ("s", details(topic=0.4)), "thin": ("t", thin)})
    assert got[("thin", "min-cases")] is False and got[("*", "same-cases")] is False
