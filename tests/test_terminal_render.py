"""Events in, blocks out: the Trail, interim folding, asks and the stopped reason, with no UI library and no model."""
import ast
from pathlib import Path

from hubofhubs.ports.deep import ProgressEvent
from hubofhubs.ports.events import EVENT_DECISION, EVENT_INTERIM, EVENT_RESULT, EVENT_WORK_TRACE
from hubofhubs.terminal import (Ask, Block, TerminalState, answer_ask, ask_block, close_ask, continue_message, earlier_preview, fold_ask,
                                interim_message, parse_answer, render, settle, to_text, toggle_trail, toggle_updates, unfold_ask)

PACKAGE = Path(__file__).resolve().parent.parent / "hubofhubs" / "terminal"


def trace(step, state="running", read=1, items=None, kind="sources", counts=None):
    return ProgressEvent(type=EVENT_WORK_TRACE, text=f"{step} {state}", data={
        "v": 1, "step_id": step, "kind": kind, "state": state, "label_key": "", "solution_id": "s", "affects_user": False,
        "counts": counts or {"read": read}, "items": items or []})


def site(ref, label=""):
    return {"ref": ref, "label": label or ref, "kind": "read"}


def state(**kw):
    s = TerminalState(**kw)
    s.new_turn("t1")
    return s


def interim(done, why="", nxt=""):
    return ProgressEvent(type=EVENT_INTERIM, text=done, data={"done": done, "why_more": why, "next": nxt, "will_continue": True})


# -- the Trail ---------------------------------------------------------------------------------------------------------------------

def test_the_live_line_is_the_newest_page_and_replaces_in_place():
    s = state()
    assert render(trace("w", items=[]), s) == []                       # nothing opened: nothing shown
    first = render(trace("w", items=[site("a.org")]), s)
    assert [(b.kind, b.text, b.fold_key) for b in first] == [("trail_live", "Opened a.org", "trail")]
    second = render(trace("w", items=[site("a.org"), site("https://www.b.org/x?q=1")], read=2), s)
    assert second[0].text == "Opened b.org" and second[0].fold_key == "trail"
    assert render(trace("w", items=[site("a.org"), site("https://www.b.org/x?q=1")], read=2), s) == []   # no change, no block


def test_a_live_line_ends_when_the_step_is_done_and_the_summary_settles_in_the_same_place():
    s = state()
    render(trace("w", items=[site("blog.rust-lang.org", "Rust blog")]), s)
    gone = render(trace("w", state="done", items=[site("blog.rust-lang.org", "Rust blog")]), s)
    assert gone[0].removed and gone[0].fold_key == "trail"
    summary = settle(s)[-1]
    assert (summary.kind, summary.text, summary.fold_key) == ("trail_summary", "Read blog.rust-lang.org", "trail")
    assert ("expand_trail", "Show details") in summary.actions            # the page has a title to add


def test_no_work_no_line_and_no_empty_button():
    s = state()
    assert settle(s)[-1].removed
    render(trace("w", state="done", items=[site("a.org")], counts={"read": 1}), s)
    only = settle(s)[-1]
    assert only.text == "Read a.org" and only.actions == ()               # the line says it all


def test_the_trail_expands_to_five_rows_then_all_then_closes():
    s = state()
    pages = [site(f"s{i}.org", f"Page {i}") for i in range(8)]
    render(trace("w", state="done", read=8, items=pages), s)
    opened = toggle_trail(s)[0]
    assert opened.state == "expanded" and len([r for r in opened.rows if "Page" in r]) == 5
    assert any("Show all 8" in r for r in opened.rows)
    every = toggle_trail(s)[0]
    assert len([r for r in every.rows if "Page" in r]) == 8
    assert not any("s0.org" in r for r in every.rows[1:])                 # the line names s0.org, so its row is the title alone
    assert toggle_trail(s)[0].state == "settled"


def test_a_search_that_opened_no_page_expands_to_the_found_sites_said_as_found():
    s = state()
    listed = [{"ref": "ubuntu.com", "label": "ubuntu.com", "kind": "found"}, {"ref": "a.org", "label": "A guide", "kind": "found"}]
    render(trace("w", state="done", counts={"found": 5, "read": 0}, items=listed), s)
    closed = settle(s)[-1]
    assert closed.text == "Searched the web, found 5 results" and ("expand_trail", "Show details") in closed.actions
    opened = toggle_trail(s)[0]
    assert list(opened.rows) == ["  ubuntu.com (found, not opened)", "  a.org (found, not opened)  A guide"]


def test_a_shared_thread_never_shows_a_private_record_title():
    s = state(shared=True)
    private = {"ref": "r", "label": "My private goal", "kind": "goal"}
    render(trace("r", state="done", kind="records", counts={"read": 1}, items=[private]), s)
    assert all("private" not in to_text([b]) for b in settle(s))


def test_unknown_kinds_and_bad_events_never_raise():
    s = state()
    assert render(ProgressEvent(type=EVENT_WORK_TRACE, text="x", data={"junk": 1}), s) == []
    assert render(ProgressEvent(type="somethingnew", text="x", data=None), s) == []


# -- interim replies and the fold -----------------------------------------------------------------------------------------------

def test_the_first_interim_is_open_and_says_why_more_and_what_is_next():
    s = state()
    (block,) = render(interim("Read 3 of 9 files.", "Six files are not read yet", "Read the rest"), s)
    assert block.kind == "interim" and block.state == "open" and block.fold_key == "msg:t1:1"
    assert block.rows == ("Still needed: Six files are not read yet", "Next: Read the rest")
    assert render(interim("x", "same", "Same"), s)[-1].rows == ("Still needed: same",)   # a next that repeats the gap is dropped


def test_a_second_interim_folds_the_first_into_one_row_with_a_preview_and_opens_the_new_one():
    s = state()
    render(interim("Read 3 of 9 files. More follows.", "six left"), s)
    blocks = render(interim("Read 6 of 9 files.", "three left"), s)
    assert blocks[0].removed and blocks[0].fold_key == "msg:t1:1"
    row, latest = blocks[1], blocks[2]
    assert (row.kind, row.title, row.text, row.state) == ("earlier_updates", "Earlier updates (1)", "Read 3 of 9 files.", "folded")
    assert latest.kind == "interim" and latest.state == "open" and latest.fold_key == "msg:t1:2"


def test_the_final_folds_every_interim_and_the_row_expands_in_place():
    s = state()
    render(interim("First part done."), s)
    render(interim("Second part done."), s)
    closing = settle(s)
    row = [b for b in closing if b.kind == "earlier_updates"][0]
    assert row.title == "Earlier updates (2)" and row.text == "Second part done."
    opened = toggle_updates(s)[0]
    assert opened.state == "expanded" and opened.fold_key == row.fold_key and "First part done." in opened.rows
    assert toggle_updates(s)[0].state == "folded"


def test_a_replayed_message_shows_once_and_the_preview_is_cut_at_a_word():
    a, b = interim_message("t", 1, "Same."), interim_message("t", 1, "Same again.")
    from hubofhubs.terminal import group
    earlier, latest = group([a, b])
    assert earlier == [] and latest.text == "Same again."
    long = interim_message("t", 1, "word " * 60)
    assert earlier_preview([long]).endswith("…") and len(earlier_preview([long])) <= 91


# -- asks ---------------------------------------------------------------------------------------------------------------------------

def decision(**data):
    base = {"outcome": "asked", "question": "Which spreadsheet should I use?", "why_only_you": "Only you know which one is current",
            "done": "Read both", "options": ["The 2025 sheet", "The 2026 sheet"], "assigned_to": "u1", "asker_user_id": "u1"}
    base.update(data)
    return ProgressEvent(type=EVENT_DECISION, text="Read both\n\nWhich spreadsheet should I use?", decision_id="d1", data=base)


def test_an_ask_for_the_viewer_shows_the_question_options_and_not_now():
    s = state(viewer_id="u1")
    (block,) = render(decision(), s)
    assert (block.kind, block.state, block.title, block.text) == ("ask", "open", "Needs you", "Which spreadsheet should I use?")
    assert "1. The 2025 sheet" in block.rows and "Only you know which one is current" in block.rows
    ids = [a for a, _ in block.actions]
    assert ids == ["option:1", "option:2", "send", "not_now"]


def test_an_answer_is_a_number_or_free_text_and_not_now_leaves_it_open():
    s = state(viewer_id="u1")
    render(decision(), s)
    assert answer_ask(s, "2").response_text == "The 2026 sheet"
    assert answer_ask(s, "The one from March").response_text == "The one from March"
    assert answer_ask(s, "   ") is None
    folded = fold_ask(s)[0]
    assert folded.state == "folded" and s.ask is not None and ("answer_now", "Answer now") in folded.actions
    assert answer_ask(s, "1") is None                                    # folded: a line is not an answer
    assert unfold_ask(s)[0].state == "open"
    settled = close_ask(s)[0]
    assert settled.text == "You answered. Answer saved." and s.ask is None
    assert close_ask(state(), resumes=True) == []


def test_resumes_is_claimed_only_when_told():
    s = state(viewer_id="u1")
    render(decision(), s)
    assert close_ask(s, resumes=True)[0].text == "You answered. Picking this back up with the answer."


def test_an_ask_for_someone_else_says_who_it_waits_on_and_hides_the_question_from_others():
    s = state(viewer_id="u2")
    (other,) = render(decision(assigned_to="u9", assigned_to_name="Sam", asker_user_id="u1"), s)
    assert (other.title, other.text, other.state) == ("Waiting on Sam", "", "waiting")
    assert answer_ask(s, "1") is None
    asker = ask_block(Ask("d1", "Q?", assigned_to="u9", asker_id="u1"), viewer_id="u1")
    assert asker.title == "Waiting on a teammate" and asker.text == "Q?"


def test_no_decision_id_is_not_an_ask():
    assert render(ProgressEvent(type=EVENT_DECISION, text="Which file?", data={}), state()) == []
    # a decision with an id but no question in its data is a parked approval or a clarifying question, not an ask
    assert render(ProgressEvent(type=EVENT_DECISION, text="Which file?", decision_id="d9", data={}), state()) == []


# -- a stopped reply -----------------------------------------------------------------------------------------------------------------

def result(outcome, reason=""):
    return ProgressEvent(type=EVENT_RESULT, text="Partial answer", data={"outcome": outcome, "stop_reason": reason})


def test_a_stopped_reply_names_the_reason_and_offers_continue():
    s = state()
    render(result("stopped", "budget"), s)
    stop = settle(s)[-1]
    assert stop.kind == "stopped" and stop.text.startswith("I stopped here because this was taking more than I could spend")
    assert stop.actions == (("continue", "Continue"),) and continue_message() == "Continue"
    assert settle(s, can_continue=False)[-1].actions == ()


def test_a_met_reply_or_a_stop_without_a_reason_adds_nothing():
    for outcome, reason in (("met", ""), ("stopped", ""), ("stopped", "weather"), ("asked", "")):
        s = state()
        render(result(outcome, reason), s)
        assert all(b.kind != "stopped" for b in settle(s))


# -- text, hygiene ---------------------------------------------------------------------------------------------------------------------

def test_no_em_dash_reaches_a_block_and_the_plain_text_reads_whole():
    b = Block(text="a — b", rows=("c—d",), title="t")
    assert "—" not in to_text([b]) and b.text == "a, b"


def test_the_renderers_import_no_ui_library_and_no_consumer():
    for path in PACKAGE.glob("*.py"):
        text = path.read_text()
        assert "—" not in text, path
        names = {n.split(".")[0] for node in ast.walk(ast.parse(text)) if isinstance(node, (ast.Import, ast.ImportFrom))
                 for n in ([a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""])}
        assert not names & {"textual", "rich", "prompt_toolkit", "quest_ai_runner"}, (path, names)
        assert "Quest AI Runner" not in text and "quest_ai_runner" not in text
