"""The general-task cases of Delegated Agent Sessions tell a real report from the naive baseline: an agent that parrots the goal back fails, an agent that
reports nothing fails every case, and an agent that reports the expected facts passes. Offline, no model."""
import importlib
import json
import sys
from pathlib import Path

EVALUATION = Path(__file__).resolve().parent.parent / "evaluation"
sys.path.insert(0, str(EVALUATION))
score = importlib.import_module("agent_sessions.score")
CASES = json.loads((EVALUATION / "agent_sessions" / "cases.json").read_text())


class Reply:
    def __init__(self, output, met=True):
        self.output, self.met, self.error = output, met, ""


REPORTS = [c for c in CASES if c.get("stratum", "report") == "report"]


def facts(case):
    """One accepted spelling of each expected fact, as a report would state them."""
    return " ".join(score.spellings(fact)[0] for fact in case["expect"])


def test_the_cases_are_eighteen_with_unique_ids_and_twelve_are_general_tasks_with_expected_facts():
    assert len(CASES) == 18 and len({c["id"] for c in CASES}) == 18 and len(REPORTS) == 12
    assert all(c["expect"] and c["files"] and not any(word in c["goal"].lower() for word in ("implement", "function", "pytest")) for c in REPORTS)


def test_the_parrot_baseline_fails_every_case_and_a_report_with_the_facts_passes():
    parrot = importlib.import_module("agent_sessions.broken.parrot").build(None)
    assert sum(not score.score_case(parrot, c)["ok"] for c in CASES) == len(CASES)
    for case in REPORTS:
        assert score.score_case(lambda kind, args, c=case: Reply(facts(c)), case)["ok"]


def test_a_run_that_changes_a_file_or_does_not_meet_the_goal_fails():
    case = CASES[0]
    assert not score.score_case(lambda kind, args: Reply(facts(case), met=False), case)["ok"]

    def overwrite(kind, args):
        Path(args["root"], "notes.txt").write_text("changed", encoding="utf-8")
        return Reply(facts(case))
    assert not score.score_case(overwrite, case)["ok"]
