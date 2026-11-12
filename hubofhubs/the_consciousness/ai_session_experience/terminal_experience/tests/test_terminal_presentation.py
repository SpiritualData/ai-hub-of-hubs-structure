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
    assert len({c["id"] for c in build.CASES}) == len(build.CASES) >= 8


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


def test_the_run_the_owner_pasted_fails_the_old_look_on_every_revision_2_check_and_passes_the_new_renderers():
    old = failed_checks("terminal_presentation.broken.old_look", "pasted_run")
    new = failed_checks("terminal_presentation.impls.reference", "pasted_run")
    assert not old["ok"] and all(old["checks"][name] is False for name in C.REVISION_2), {k: v for k, v in old["checks"].items() if v is not False}
    assert new["ok"] and new["score"] == 1.0, new["note"]


def test_the_internal_vocabulary_is_read_from_the_renderers_own_names_not_a_hand_list():
    hyphenated, column, lifecycle = C.internal_words()
    from hubofhubs.the_consciousness.ai_session_experience.session_events import EVENTS, STEP_KINDS
    assert set(hyphenated) == {w for w in list(EVENTS) + list(STEP_KINDS) if "-" in w} and "message-received" in hyphenated
    assert column.match("ok run      date") and column.match("[0:03] ok edit     notes.md") and not column.match("✓ Ran date")
    assert lifecycle.search("ok note     session started")


def test_the_revision_2_checks_judge_a_capture_on_their_own_terms():
    cap = Capture("stream", 56, 24)
    cap.snapshots = [snapshot(0.1, "✓ AI Hub of Hubs Structure         0:05 · $0.21", "❯ What is today?", "Today is Wednesday, November 11, 2026.")]
    cap.raw = "✓ Goal met · 0:05 · $0.21 · 2 calls\nahohs work --resume 0a239607-4796-46d9-a544-6eebe0537683 --harness native\n"
    assert C.no_raw_markdown(cap) and C.header_has_full_name(cap) and C.resume_command_unbroken(cap) and C.cost_at_cent_precision(cap)
    cap.raw = "ahohs work --resume\n  0a239607 --harness native\n calls | 135 tokens\n"
    assert C.resume_command_unbroken(cap) is False and C.no_empty_figure_segment(Capture("stream", 56, 24, snapshots=[snapshot(0.1, " calls | 135 tokens")])) is False
    assert C.no_raw_markdown(Capture("stream", 56, 24, snapshots=[snapshot(0.1, "Today is **Wednesday**")])) is False
    assert C.cost_at_cent_precision(Capture("stream", 56, 24, snapshots=[snapshot(0.1, "$0.2077 of $20.00")])) is False


def test_an_arm_that_reads_no_key_fails_the_correction_round_trip():
    reference = failed_checks("terminal_presentation.impls.reference", "steer")
    assert reference["ok"] and reference["score"] == 1.0
    deaf = failed_checks("terminal_presentation.broken.deaf", "steer")
    assert not deaf["ok"] and deaf["checks"]["round-trip-steer"] is False


def test_an_arm_that_declares_labels_its_screen_does_not_show_fails_the_three_checks_that_read_them():
    watch = failed_checks("terminal_presentation.broken.false_labels", "watch")
    approve = failed_checks("terminal_presentation.broken.false_labels", "approve")
    pasted = failed_checks("terminal_presentation.broken.false_labels", "pasted_run")
    assert watch["checks"]["key-hints-present-and-whole"] is False
    assert approve["checks"]["risky-step-waits-with-preview"] is False
    assert pasted["checks"]["goal-as-persons-message"] is False
    # the same screens held to the shared words (the reference declares nothing) pass: it is the false declaration that fails them
    assert failed_checks("terminal_presentation.impls.reference", "watch")["checks"]["key-hints-present-and-whole"] is True
    assert failed_checks("terminal_presentation.impls.reference", "approve")["checks"]["risky-step-waits-with-preview"] is True
    assert failed_checks("terminal_presentation.impls.reference", "pasted_run")["checks"]["goal-as-persons-message"] is True


def test_a_real_runs_recorded_events_show_the_answer_once_and_the_old_note_rule_showed_it_twice():
    pytest.importorskip("textual")
    new = failed_checks("terminal_presentation.impls.reference", "real_run")
    assert new["checks"]["answer-once"] is True, new["note"]
    assert failed_checks("terminal_presentation.broken.flush_on_figure", "real_run")["checks"]["answer-once"] is False


def test_the_shared_rule_holds_interim_text_until_a_row_draws_and_drops_what_is_part_of_the_answer():
    from hubofhubs.the_consciousness.ai_session_experience.session_events import Finished as Done, Step as StepEvent, Usage
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionView, event_line
    view = SessionView()
    note = lambda text: StepEvent(step_id="t", kind="note", label=text, state="done")
    answer = "Today is **2026-11-11**. I took it from my context; I did not check the clock. No files changed."
    assert event_line(note("Today is **2026-11-11**. I took it from my con..."), view) == ""
    assert event_line(Usage(cost_usd=0.01), view) == ""          # a figure update draws nothing and does not flush the note
    assert event_line(Usage(tokens=5), view) == ""
    assert event_line(Done(outcome="met", report=answer), view).strip() == "" or "Today is" not in event_line(Done(outcome="met", report=answer), view)
    # pieces of the answer, one note each: both are the closing's, neither is drawn twice
    view = SessionView()
    event_line(note("Today is 2026-11-11."), view)
    event_line(note("I took it from my context; I did not check the clock."), view)
    assert "Today is" not in event_line(Done(outcome="met", report=answer), view)
    # a remark that is not the answer stays as a quiet row, with the next row that draws
    view = SessionView()
    event_line(note("Checking the folder first"), view)
    assert "Checking the folder first" in event_line(StepEvent(step_id="s", kind="run", label="ls", state="done"), view)


def waiting_capture(labels, *rows):
    class Ask:
        type, question, preview = "waiting", "Deploy now?", "creates x"

    class Stop:
        type, agent_id = "approve", ""
    cap = Capture("external", 100, 30, labels=dict(labels))
    cap.snapshots = [snapshot(0.5, *rows)]
    cap.arrivals = [(0.4, Ask())]
    cap.controls = [(2.0, Stop(), True)]
    cap.seconds = 3.0
    return cap


def test_a_declared_choice_label_is_required_on_the_waiting_screen_and_the_shared_words_otherwise():
    rows = ("Deploy now?", "creates x", "Allow once   Reject")
    assert C.risky_step_waits_with_preview(waiting_capture({"allow": "Allow once", "refuse": "Reject"}, *rows)) is True
    assert C.risky_step_waits_with_preview(waiting_capture({"allow": "Allow once", "refuse": "Decline"}, *rows)) is False        # a declared label that is not on the screen
    assert C.risky_step_waits_with_preview(waiting_capture({"allow": "Allow once", "refuse": ""}, *rows)) is False              # an empty declared label
    assert C.risky_step_waits_with_preview(waiting_capture({}, *rows)) is False                                                 # nothing declared: the shared words (y and n, approve and refuse)
    assert C.risky_step_waits_with_preview(waiting_capture({}, "Deploy now?", "creates x", "approve (y) | refuse (n)")) is True
    assert C.risky_step_waits_with_preview(waiting_capture({"allow": "Allow once", "refuse": "Reject"}, "Deploy now?", "Allow once   Reject")) is False       # the preview must be visible


def test_a_declared_stop_hint_is_required_whole_at_every_size_whatever_its_verb():
    def sized(width, row, labels):
        cap = Capture("external", width, 24, labels=dict(labels))
        cap.snapshots = [snapshot(0.5, row)]
        cap.seconds = 2.0
        return cap
    declared = {"stop": "esc interrupt"}
    assert C.key_hints([sized(100, "esc interrupt   $0.02", declared), sized(56, "esc interrupt  $0.02", declared)]) is True
    assert C.key_hints([sized(100, "esc interrupt   $0.02", declared), sized(56, "esc...upt", declared)]) is False
    assert C.key_hints([sized(100, "esc interrupt", {"stop": ""}), sized(56, "esc interrupt", {"stop": ""})]) is False
    assert C.key_hints([sized(100, "Esc stop | Tab structure", {}), sized(56, "Esc stop", {})]) is True                          # nothing declared: the shared row


def test_a_declared_person_marker_must_start_the_goal_row_and_not_the_answers():
    class Started:
        type, goal = "run-started", "What is today?"

    class Done:
        type, report = "finished", "Today is Wednesday."

    def capture(labels, *rows):
        cap = Capture("external", 100, 30, labels=dict(labels))
        cap.snapshots = [snapshot(0.5, *rows)]
        cap.arrivals = [(0.1, Started()), (0.4, Done())]
        return cap
    assert C.goal_as_message(capture({"person": "┃"}, "  ┃  What is today?", "  Today is Wednesday.")) is True
    assert C.goal_as_message(capture({"person": "┃"}, "  ┃  Today is Wednesday.", "  ┃  What is today?")) is False        # the AI's text carries the person's marker: not distinct
    assert C.goal_as_message(capture({"person": "»»"}, "  ┃  What is today?")) is False                                      # a declared marker that is not on the screen
    assert C.goal_as_message(capture({"person": ""}, "  ┃  What is today?")) is False
    assert C.goal_as_message(capture({}, "  ┃  What is today?")) is False and C.goal_as_message(capture({}, "❯ What is today?")) is True
