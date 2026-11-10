"""Structure Watch: the scripted cases of the metric, the default timing and the route of each item through Judgment Calls."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "evaluation"))
sys.path.insert(0, str(ROOT / "evaluation" / "structure_watch"))
import score  # noqa: E402
from hubofhubs.api import structure_watch_due  # noqa: E402
from hubofhubs.the_consciousness.judgment_calls.judgment import SeverityPolicy  # noqa: E402
from hubofhubs.the_intelligence.nervous_system.structure_watch.watch import BestTierCall, FindingsOnly, OUTPUT_TOKENS  # noqa: E402

CASES = json.loads((ROOT / "evaluation" / "structure_watch" / "cases.json").read_text(encoding="utf-8"))


def test_every_scripted_case_passes_for_the_call():
    run = score.adapt(BestTierCall, None)
    failed = [c["id"] for c in CASES if not score.score_case(run, c)["ok"]]
    assert failed == []


def test_the_findings_only_baseline_never_calls_a_model():
    calls = []
    arm = FindingsOnly(ask=lambda *a: calls.append(a))
    got = arm.watch({"intent": "x", "tables": {"solutions": [{"solution_id": "s", "name": "s", "purpose": "p", "authoritative_metric_id": "", "metric_ids": ""}], "implementations": []}, "now": "2026-11-10T09:00:00Z"})
    assert calls == [] and got["called"] is False and got["items"][0]["subject"] == "solutions:s"


def test_judgment_calls_asks_for_a_persons_structure_and_proceeds_for_the_ais():
    judge = SeverityPolicy().decide
    assert judge({"severity": "low", "reason": "r"}, "", {"needs_person": True})["decision"] == "ask"
    assert judge({"severity": "high", "reason": "r"}, "", {"ai_owned": True})["decision"] == "proceed"


def test_default_timing_end_of_run_and_session_start():
    now = "2026-11-10T09:00:00Z"
    assert structure_watch_due("end_of_run", now, "2026-11-10T08:00:00Z", now)["due"] is True
    assert structure_watch_due("end_of_run", now, "2026-11-10T08:00:00Z", "")["due"] is False          # nothing changed
    assert structure_watch_due("session_start", now, "2026-11-10T08:00:00Z", now)["due"] is False       # last watch under a day old
    assert structure_watch_due("session_start", now, "2026-11-08T08:00:00Z", now)["due"] is True
    assert structure_watch_due("end_of_run", now, "", now, off=True)["due"] is False


def test_the_output_cap_is_a_few_hundred_tokens():
    assert OUTPUT_TOKENS <= 500
