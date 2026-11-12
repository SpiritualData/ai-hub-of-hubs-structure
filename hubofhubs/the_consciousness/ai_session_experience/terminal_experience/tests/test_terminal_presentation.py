"""The presentation metric of Terminal Experience (evaluation/terminal_presentation): its records, weights, checks, the layer 2 harness and calibration set, and the
baseline test (a deliberately broken arm must be caught). The screen-replay tests need the evaluation-only emulator pyte and are skipped without it."""
import importlib
import json
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[5]
EVALUATION = ROOT / "evaluation"
COMPONENT = EVALUATION / "terminal_presentation"
sys.path.insert(0, str(EVALUATION))
sys.path.insert(0, str(COMPONENT))

import checks as C  # noqa: E402
from screen import Capture, Snapshot  # noqa: E402
from judged import calibration, judge  # noqa: E402

CONFIG = tomllib.loads((ROOT / "esoi.toml").read_text())
CHECKLIST_DIGEST = "29b08c726b8c"       # set when the checklist was frozen on 2026-11-11; a changed checklist is a new version and every arm is judged again


def test_cases_are_the_ones_the_builder_writes():
    build = importlib.import_module("build_cases")
    assert json.loads((COMPONENT / "cases.json").read_text()) == build.CASES
    assert len({c["id"] for c in build.CASES}) == len(build.CASES) >= 7


def test_every_check_has_a_weight_and_requirements_and_the_balance_sums_to_one():
    table = CONFIG["balance"]["terminal_presentation"]
    assert set(table["check_weights"]) == set(C.REQUIREMENTS)
    assert all(isinstance(w, int) and w >= 1 for w in table["check_weights"].values())
    assert abs(sum(table["weights"].values()) - 1.0) < 1e-9
    assert all(ids and all(x.startswith("X") for x in ids) for ids in C.REQUIREMENTS.values())


def test_contrast_is_the_wcag_ratio():
    assert round(C.ratio((0, 0, 0), (255, 255, 255)), 2) == 21.0
    assert C.ratio((114, 114, 114), (0, 0, 0)) < C.MIN_CONTRAST < C.ratio((114, 114, 114), (255, 255, 255))


def snapshot(at, *rows, scroll=(), live=None, styled=()):
    return Snapshot(at, tuple(rows), tuple(scroll), tuple(rows if live is None else live), tuple(styled))


class Step:
    type, kind, state, agent_id = "step", "edit", "done", "main"

    def __init__(self, label):
        self.label = label


def test_a_row_shown_twice_or_in_both_live_region_and_scrollback_fails():
    cap = Capture("stream", 80, 24, arrivals=[(0.0, Step("b.txt"))])
    cap.snapshots = [snapshot(0.1, "ok edit b.txt", "x")]
    assert C.each_update_once(cap) is True
    cap.snapshots = [snapshot(0.1, "[0:01] ok edit b.txt", "ok edit b.txt")]
    assert C.each_update_once(cap) is False
    cap.snapshots = [snapshot(0.1, "ok edit b.txt", scroll=("ok edit b.txt",))]
    assert C.each_update_once(cap) is False


def test_first_output_and_key_hints():
    cap = Capture("stream", 80, 24)
    cap.snapshots = [snapshot(0.05, ""), snapshot(1.5, "hello")]
    assert C.first_output(cap) is False
    cap.snapshots = [snapshot(0.05, "hello")]
    assert C.first_output(cap) is True
    wide, narrow = Capture("stream", 120, 40, seconds=1.0), Capture("stream", 80, 24, seconds=1.0)
    wide.snapshots = [snapshot(0.1, "Esc stop | type + Enter to steer | Tab structure")]
    narrow.snapshots = [snapshot(0.1, "Esc stop | type + Enter to steer | Tab struc")]
    assert C.key_hints([narrow, wide]) is False
    narrow.snapshots = [snapshot(0.1, "Esc stop | type + Enter to steer")]
    assert C.key_hints([narrow, wide]) is True


def test_repaint_bound_and_decoration_contrast():
    cap = Capture("stream", 80, 24, seconds=1.0, repaints=30, jumps=30)
    assert C.repaints_under_bound(cap) is False
    cap.repaints, cap.jumps = 5, 15
    assert C.repaints_under_bound(cap) is True
    cap.kind = "textual"
    assert C.repaints_under_bound(cap) is None
    cap.snapshots = [snapshot(0.1, "x", styled=[((1, 120, 212), (39, 39, 39), "▔▔", False)])]
    assert C.contrast_ok(cap) is True        # decoration needs 3:1 and this is 3.3
    cap.snapshots = [snapshot(0.1, "x", styled=[((1, 120, 212), (39, 39, 39), "text", False)])]
    assert C.contrast_ok(cap) is False


# --- layer 2 ------------------------------------------------------------------------------------------------------------------------

def test_the_checklist_is_frozen_and_every_item_names_a_published_source_and_frames():
    data = judge.load_checklist()
    assert judge.checklist_digest() == CHECKLIST_DIGEST
    assert len(data["items"]) == 15 and len({i["id"] for i in data["items"]}) == 15
    assert all(i["source"] and set(i["frames"]) <= {"start", "mid_run", "waiting", "stopped", "finished", "narrow"} for i in data["items"])


def test_a_yes_needs_a_quote_found_in_the_frame_and_the_majority_decides():
    grid = "+--+\n|Esc stop | type to steer     | 01\n|>                       | 02\n+--+"
    items = judge.items_for("mid_run")
    ids = [i["id"] for i in items]
    good = json.dumps({"items": [{"id": i, "verdict": "yes", "quote": "Esc stop"} for i in ids]})
    invented = json.dumps({"items": [{"id": i, "verdict": "yes", "quote": "Tab shows the tree"} for i in ids]})
    assert all(judge.verdicts(good, grid, items).values())
    assert not any(judge.verdicts(invented, grid, items).values())
    assert not any(judge.verdicts("not json", grid, items).values())
    replies = iter([good, invented, good])
    assert all(judge.judge_frame(lambda prompt, tier: next(replies), "tier", "mid_run", grid, runs=3).values())


def test_arms_are_blinded_and_shuffled_and_the_prompt_never_names_an_arm():
    seen = []

    def call(prompt, tier):
        seen.append(prompt)
        return json.dumps({"items": []})
    frames = {"live_session": {"start": "|live_session grid| 01"}, "textual_session": {"start": "|textual_session grid| 01"}}
    out = judge.judge_arms(call, frames, "tier", seed=3, runs=1)
    assert out["advisory"] is True and len(out["order"]) == 2
    assert not any("live_session" in p or "textual_session" in p for p in seen)


def test_a_layer_2_difference_breaks_a_tie_only_beyond_the_run_to_run_spread_and_the_thresholds_are_the_written_ones():
    assert (judge.MAX_MISSES, judge.MAX_FALSE_ALARMS) == (2, 1)
    result = {"share": {"a": 0.80, "b": 0.86}, "spread": {"a": 0.05, "b": 0.03}}
    assert judge.breaks_a_tie(result, "a", "b") == "b"          # 0.06 is more than the larger spread, 0.05
    result["spread"]["a"] = 0.07
    assert judge.breaks_a_tie(result, "a", "b") == "a"          # inside the spread: the incumbent stays
    assert judge.spread([0.8, 0.85, 0.82]) == 0.05
    assert judge.majority([{"x": True}, {"x": True}, {"x": False}]) == {"x": True}


def test_the_calibration_set_pairs_a_clean_frame_with_one_defect_each():
    cases = calibration.load_calibration()
    assert len(cases) == 12
    items = {i["id"] for i in judge.load_checklist()["items"]}
    wanted = {name: feature for name, _, _, feature, _ in calibration.DEFECTS}
    for case in cases:
        assert case["item"] in items and case["clean"] != case["defective"]
        assert calibration.present(case["clean"], wanted[case["id"]]) and not calibration.present(case["defective"], wanted[case["id"]]) or case["id"] in ("repeated-row", "repeated-row-finished")


def test_a_perfect_and_a_blind_judge_get_the_miss_rates_they_deserve():
    cases = calibration.load_calibration()
    by_grid = {}
    for case in cases:
        by_grid[case["clean"]] = True
        by_grid[case["defective"]] = False

    def judge_that_sees(prompt, tier):
        grid = prompt.split("Screen (", 1)[1].split("):\n", 1)[1].split("\n\nQuestions:", 1)[0]
        yes = by_grid.get(grid, True)
        text = judge.frame_text(grid).strip()
        quote = text.splitlines()[0].strip() if yes and text else ""
        return json.dumps({"items": [{"id": i["id"], "verdict": "yes" if yes else "no", "quote": quote} for i in judge.load_checklist()["items"]]})
    sees = judge.calibrate(judge_that_sees, "tier", runs=1)
    assert sees["miss_rate"] == 0.0 and sees["false_alarm_rate"] == 0.0
    def says_yes_to_everything(prompt, tier):
        grid = prompt.split("Screen (", 1)[1].split("):\n", 1)[1].split("\n\nQuestions:", 1)[0]
        first = judge.frame_text(grid).strip().splitlines()[0].strip()
        return json.dumps({"items": [{"id": i["id"], "verdict": "yes", "quote": first} for i in judge.load_checklist()["items"]]})
    blind = judge.calibrate(says_yes_to_everything, "tier", runs=1)
    assert blind["miss_rate"] == 1.0


def test_no_model_name_in_the_presentation_code():
    for path in COMPONENT.rglob("*.py"):
        text = path.read_text()
        assert "claude-" not in text and "gpt-" not in text and "gemini-" not in text, path


# --- the baseline: a deliberately broken arm must be caught -------------------------------------------------------------------------

def failed_checks(arm_module, scenario):
    pytest.importorskip("pyte")
    score = importlib.import_module("terminal_presentation.score")
    mod = importlib.import_module(arm_module)
    case = next(c for c in json.loads((COMPONENT / "cases.json").read_text()) if c["id"] == f"presentation-{scenario}")
    return score.score_case(mod.build(None), case)


def test_the_reference_draws_each_update_once_and_a_frame_that_is_never_erased_does_not():
    assert failed_checks("terminal_presentation.impls.reference", "watch")["checks"]["each-update-once"] is True
    broken = failed_checks("terminal_presentation.broken.no_erase", "watch")
    assert broken["checks"]["each-update-once"] is False and not broken["ok"]


def test_an_arm_that_reads_no_key_fails_the_correction_round_trip():
    reference = failed_checks("terminal_presentation.impls.reference", "steer")
    assert reference["ok"] and reference["score"] == 1.0
    deaf = failed_checks("terminal_presentation.broken.deaf", "steer")
    assert not deaf["ok"] and deaf["checks"]["round-trip-steer"] is False
