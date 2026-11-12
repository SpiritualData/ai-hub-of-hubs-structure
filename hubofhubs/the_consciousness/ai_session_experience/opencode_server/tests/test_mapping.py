"""The mapping of the hub's session events to the opencode client's events and messages (``mapping.Translator`` over ``projection.Store``): every event type, the finish the owner asked for (the helper
and its solution on the row, a read named, the hub's own figures, a notice in the transcript, a short title, the closing with the outcome line and the resume command), a refused step, a stop that
ends open steps, id reuse, monotonic ids. Pure: no socket, no thread, no client."""
import re

from hubofhubs.the_consciousness.ai_session_experience.opencode_server import mapping
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.projection import Ids, Store
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    AgentEnded, AgentStarted, Finished, Notice, Review, RunStarted, Step, Usage, Waiting)


def make(acting_for=""):
    clock = iter(range(1000, 10 ** 6))
    store = Store("/work", clock=lambda: next(clock) / 1000)
    root = store.ids.make("ses")
    store.create_session(root, "")
    return store, root, mapping.Translator(store, root, acting_for)


def kinds(store):
    return [e["type"] for _, e in store.log]


def messages(store, root, kind):
    return [m for m in store.messages[root] if m["type"] == kind]


def tools(store, root):
    return [p for m in messages(store, root, "assistant") for p in m["content"] if p["type"] == "tool"]


def test_the_goal_is_the_persons_message_and_a_short_title_cut_at_a_word():
    store, root, t = make()
    t.handle(RunStarted(goal="Make the note keeper ignore blank text and trim what it keeps", harness="native", solution="notes", milestone="blank notes are ignored"))
    title = store.sessions[root]["title"]
    assert title.endswith("…") and len(title) <= mapping.TITLE_WIDTH and title[:-1].rstrip() in "Make the note keeper ignore blank text and trim what it keeps"
    assert not title[:-1].endswith(("keep", "kee", "ign"))            # never in the middle of a word
    assert mapping.title_of("What is today?") == "What is today?"
    user = messages(store, root, "user")
    assert [m["text"] for m in user] == ["Make the note keeper ignore blank text and trim what it keeps"]
    assert store.active[root] == "running" and store.sessions[root]["metadata"]["hub"]["serves"] == "notes"


def test_the_clients_own_message_id_is_kept_and_the_goal_is_not_said_twice():
    store, root, t = make()
    iid = store.enqueue_user(root, "do the work", iid="msg_client0000000000000000000")
    t.handle(RunStarted(goal="do the work"))
    assert iid == "msg_client0000000000000000000" and [m["id"] for m in messages(store, root, "user")] == [iid]
    assert store.pending[root] == []


def test_a_read_a_command_and_an_edit_are_named_tool_calls_with_their_object_and_diff():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    diff = "--- a/n.py\n+++ b/n.py\n@@ -1,2 +1,3 @@\n a\n-b\n+c\n+d\n"
    for step in (Step(step_id="1", kind="read", label="src/notes.py", state="running"), Step(step_id="1", kind="read", label="src/notes.py", state="done"),
                 Step(step_id="2", kind="run", label="date", state="running"), Step(step_id="2", kind="run", label="date", state="done", detail="Wed"),
                 Step(step_id="3", kind="edit", label="n.py", state="running"), Step(step_id="3", kind="edit", label="n.py", state="done", detail=diff)):
        t.handle(step)
    read, command, edit = tools(store, root)
    assert (read["name"], read["state"]["input"]) == ("read", {"path": "src/notes.py"}) and read["state"]["status"] == "completed"
    assert (command["name"], command["state"]["input"]["command"], command["state"]["content"][0]["text"]) == ("bash", "date", "Wed")
    file = edit["state"]["metadata"]["files"][0]
    assert edit["name"] == "edit" and file["patch"] == diff and (file["additions"], file["deletions"]) == (2, 1)
    assert len(messages(store, root, "assistant")) == 3           # one step each, none counted into an anonymous group


def test_a_step_that_was_refused_is_an_error_row_with_the_reason():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Step(step_id="1", kind="run", label="rm -r x", state="running"))
    t.handle(Step(step_id="1", kind="run", label="rm -r x", state="blocked", detail="the person refused it"))
    (call,) = tools(store, root)
    assert call["state"]["status"] == "error" and call["state"]["error"]["message"] == "Refused: the person refused it" and call["state"]["error"]["type"] == "refused"


def test_a_stop_ends_what_was_running_as_interrupted_and_says_how_to_resume():
    store, root, t = make()
    t.handle(RunStarted(goal="g", session_id="s-1"))
    t.handle(Step(step_id="1", kind="run", label="sleep 9", state="running"))
    t.handle(Finished(outcome="stopped", session_id="s-1"))
    (call,) = tools(store, root)
    assert call["state"]["status"] == "error" and call["state"]["error"]["message"] == "Step interrupted" and call["state"]["metadata"]["interrupted"] is True
    assert "session.step.failed" in kinds(store) and "session.execution.interrupted" in kinds(store) and root not in store.active
    said = [p["text"] for m in messages(store, root, "assistant") for p in m["content"] if p["type"] == "text"]
    assert len(said) == 1 and "Stopped, your work is kept" in said[0] and "Type resume to continue it" in said[0]
    assert messages(store, root, "idle")[-1]["outcome"] == "interrupted"


def test_a_run_that_ends_has_nothing_left_running():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Step(step_id="1", kind="run", label="x", state="running"))
    t.handle(Finished(outcome="met", report="Done."))
    assert tools(store, root)[0]["state"]["status"] == "completed" and "session.execution.succeeded" in kinds(store)


def test_a_helper_is_a_child_session_and_a_row_naming_the_helper_and_the_solution_it_serves():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(AgentStarted(agent_id="test-writer", task="write the tests", solution="notes-keeper"))
    t.handle(Step(agent_id="test-writer", step_id="a", kind="edit", label="tests.py", state="running"))
    t.handle(Step(agent_id="test-writer", step_id="a", kind="edit", label="tests.py", state="done"))
    t.handle(AgentEnded(agent_id="test-writer", state="met", calls=2, summary="tests added"))
    (row,) = [p for p in tools(store, root) if p["name"] == "task"]
    assert row["state"]["input"]["agent"] == "test writer" and "serves notes-keeper" in row["state"]["input"]["description"] and row["state"]["status"] == "completed"
    child = row["state"]["metadata"]["sessionId"]
    assert store.sessions[child]["parentID"] == root and tools(store, child)[0]["state"]["input"] == {"path": "tests.py"}
    assert child not in store.active and messages(store, child, "idle")[-1]["outcome"] == "succeeded"


def test_a_generated_helper_id_is_not_shown_as_its_name():
    assert mapping.helper_name("tool-4") == "helper" and mapping.helper_name("agent_12") == "helper" and mapping.helper_name("test-writer") == "test writer"


def test_the_hand_off_step_and_the_helpers_own_event_make_one_row_in_either_order():
    for first_step in (True, False):
        store, root, t = make()
        t.handle(RunStarted(goal="g"))
        step = Step(step_id="d", kind="delegate", label="write the tests", state="running")
        started = AgentStarted(agent_id="tool-4", task="write the tests")
        for event in ((step, started) if first_step else (started, step)):
            t.handle(event)
        t.handle(AgentEnded(agent_id="tool-4", state="met", summary="ok"))
        t.handle(Step(step_id="d", kind="delegate", label="write the tests", state="done"))
        assert len([p for p in tools(store, root) if p["name"] == "task"]) == 1


def test_a_helper_step_with_no_helper_event_still_shows_as_a_row():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Step(step_id="d", kind="delegate", label="write the tests", state="running"))
    t.handle(Step(step_id="d", kind="delegate", label="write the tests", state="done"))
    assert [p["name"] for p in tools(store, root)] == ["task"]


def test_a_diff_preview_is_an_edit_request_and_any_other_preview_is_a_command_request_with_the_question():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Waiting(ask_id="a1", question="Apply this edit?", risky="n.py", preview="--- a/n.py\n+++ b/n.py\n@@ -1 +1 @@\n-a\n+b\n"))
    t.handle(Waiting(ask_id="a2", question="Deploy now?", risky="deploy", preview="creates deployed.txt"))
    first, second = store.open_requests(root)
    assert first["action"] == "edit" and first["metadata"]["diff"].startswith("---") and first["resources"] == ["n.py"]
    assert second["action"] == "shell" and second["resources"] == ["Deploy now?", "creates deployed.txt"]
    assert store.answer("a1", "once")["id"] == "a1" and [r["id"] for r in store.open_requests(root)] == ["a2"]
    assert "permission.replied" in kinds(store)


def test_usage_is_the_hubs_own_figures_and_the_steps_billed_add_up_to_them():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Usage(cost_usd=0.0042, tokens=135, calls=1))
    t.handle(Step(step_id="1", kind="run", label="a", state="running"))
    t.handle(Step(step_id="1", kind="run", label="a", state="done"))
    t.handle(Usage(cost_usd=0.2077, tokens=400, calls=2))
    t.handle(Finished(outcome="met", report="Done.", cost_usd=0.2077, tokens=400))
    info = store.sessions[root]
    assert info["cost"] == 0.2077 and info["tokens"]["input"] == 400
    assert abs(sum(m["cost"] for m in messages(store, root, "assistant")) - 0.2077) < 1e-9
    assert t.hub_metadata()["hub"]["quiet"] == ""                         # the client shows $0.21 itself; a quiet note is only for a near ceiling or under a cent


def test_a_cost_under_a_cent_is_said_in_the_plugins_quiet_note_not_as_zero():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Usage(cost_usd=0.0004, tokens=10))
    assert t.hub_metadata()["hub"]["quiet"] == "<$0.01"


def test_a_ceiling_is_named_only_once_half_of_it_is_used():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Usage(cost_usd=1.0, ceiling_usd=20.0))
    assert t.hub_metadata()["hub"]["quiet"] == "" and t.hub_metadata()["hub"]["spend_full"] == "$1.00 of $20.00"
    t.handle(Usage(cost_usd=12.0, ceiling_usd=20.0))
    assert t.hub_metadata()["hub"]["quiet"] == "$12.00 of $20.00"


def test_a_notice_and_a_review_are_quiet_rows_in_the_transcript_never_a_toast():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Notice(kind="decision", text="x", decision="continue", reason="plateau"))
    t.handle(Notice(kind="soft-limit", text="The run is wrapping up: most of its spend is used."))
    t.handle(Review(text="looks right", corrections=0))
    rows = [m["description"] for m in messages(store, root, "synthetic")]
    assert len(rows) == 3 and "wrapping up" in rows[1] and rows[2].startswith("Review")
    assert "tui.toast.show" not in kinds(store)


def test_an_interim_note_that_is_the_answer_is_not_drawn_and_a_lifecycle_note_never_is():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Step(step_id="s0", kind="note", label="session started", state="done"))
    t.handle(Step(step_id="s2", kind="note", label="Today is **Wednesday, November 11, 2026**. The system clock read 6:...", state="done"))
    t.handle(Finished(outcome="met", report="Today is **Wednesday, November 11, 2026**. The system clock read 6:43 PM.\n\nSecond paragraph."))
    texts = [p["text"] for m in messages(store, root, "assistant") for p in m["content"] if p["type"] == "text"]
    assert len(texts) == 1 and "Second paragraph" in texts[0]


def test_a_real_runs_notes_and_figure_updates_leave_the_answer_in_the_closing_only():
    import json
    from pathlib import Path
    from hubofhubs.the_consciousness.ai_session_experience.session_events import event_from_dict
    fixture = Path(__file__).resolve().parents[5] / "evaluation" / "terminal_presentation" / "real_native_run.json"
    store, root, t = make()
    for item in json.loads(fixture.read_text()):
        t.handle(event_from_dict(item))
    texts = [p["text"] for m in messages(store, root, "assistant") for p in m["content"] if p["type"] == "text"]
    assert len(texts) == 1 and texts[0].startswith("Today is **2026-11-11**") and "Goal met" in texts[0]


def test_notes_that_are_pieces_of_the_answer_are_dropped_and_a_different_remark_is_kept():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Step(step_id="a", kind="note", label="Checking the folder first", state="done"))
    t.handle(Step(step_id="b", kind="note", label="The file has two lines.", state="done"))
    t.handle(Step(step_id="c", kind="note", label="It is short.", state="done"))
    t.handle(Finished(outcome="met", report="The file has two lines. It is short."))
    texts = [p["text"] for m in messages(store, root, "assistant") for p in m["content"] if p["type"] == "text"]
    assert texts[0] == "Checking the folder first" and len(texts) == 2 and texts[1].startswith("The file has two lines. It is short.")


def test_an_interim_note_that_is_not_the_answer_is_drawn_once_something_follows():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Step(step_id="n", kind="note", label="I will read the file first", state="done"))
    t.handle(Step(step_id="1", kind="read", label="a.txt", state="running"))
    texts = [p["text"] for m in messages(store, root, "assistant") for p in m["content"] if p["type"] == "text"]
    assert texts == ["I will read the file first"]


PASTED = ("Today is **Wednesday, November 11, 2026**. The system clock read 6:43 PM PST when I checked.\n\nI checked it with the `date` command and didn't change any files.")


def test_the_closing_is_the_answer_then_one_outcome_line_then_the_resume_command_alone():
    store, root, t = make()
    t.handle(RunStarted(goal="What is today?", harness="native", session_id="0a239607-4796-46d9-a544-6eebe0537683"))
    t.handle(Step(step_id="s1", kind="run", label="date", state="running"))
    t.handle(Step(step_id="s1", kind="run", label="date", state="done"))
    t.handle(Usage(at=3.5, cost_usd=0.2077, tokens=135, calls=2, ceiling_usd=20.0, ceiling_seconds=14400.0))
    t.handle(Finished(at=5.0, outcome="met", report=PASTED, session_id="0a239607-4796-46d9-a544-6eebe0537683", cost_usd=0.2077, tokens=135))
    closing = [p["text"] for m in messages(store, root, "assistant") for p in m["content"] if p["type"] == "text"][-1]
    assert closing.startswith("Today is **Wednesday, November 11, 2026**") and "didn't change any files." in closing
    assert "✓ Goal met · 0:05 · $0.21 · 2 calls · 135 tokens · no files changed" in closing
    assert closing.rstrip().endswith("```\nahohs work --resume 0a239607-4796-46d9-a544-6eebe0537683 --harness native\n```") and "Continue this session later, in this folder:" in closing
    assert closing.count("Goal met") == 1


def test_a_second_finished_with_the_metric_after_replaces_the_closing_and_ends_the_session_once():
    store, root, t = make()
    t.handle(RunStarted(goal="g", metric="checks", metric_before=1.0))
    t.handle(Finished(outcome="met", report="Done."))
    t.handle(Finished(outcome="met", report="Done.", metric_after=3.0))
    texts = [p["text"] for m in messages(store, root, "assistant") for p in m["content"] if p["type"] == "text"]
    assert len(texts) == 1 and "after 3 (+2)" in texts[0]
    assert kinds(store).count("session.execution.succeeded") == 1 and t.hub_metadata()["hub"]["metric"].endswith("after 3 (+2)")


def test_a_failed_run_ends_the_session_failed_with_the_reason():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    t.handle(Finished(outcome="failed", error="the tool broke"))
    assert messages(store, root, "idle")[-1]["outcome"] == "failed" and "Failed" in [p["text"] for m in messages(store, root, "assistant") for p in m["content"]][-1]


def test_a_message_the_run_took_up_moves_from_the_inbox_into_the_transcript_and_the_plugin_sees_it_sent_then_taken_up():
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    iid = store.enqueue_user(root, "use the short name", iid="msg_mine000000000000000000000")
    t.correction_sent(iid, "use the short name")
    assert [i["id"] for i in store.pending[root]] == [iid] and t.hub_metadata()["hub"]["corrections"] == [{"id": iid, "text": "use the short name", "taken_up": False}]
    t.handle(Step(step_id=iid, kind="message-received", label="use the short name", state="done"))
    assert store.pending[root] == [] and messages(store, root, "user")[-1]["id"] == iid
    assert t.hub_metadata()["hub"]["corrections"][0]["taken_up"] is True


def test_the_hub_metadata_carries_what_the_plugin_places():
    store, root, t = make(acting_for="the owner")
    t.handle(RunStarted(goal="g", solution="notes", milestone="m", frame="f", metric="checks", metric_before=1.0))
    t.handle(AgentStarted(agent_id="h", task="t"))
    hub = t.hub_metadata()["hub"]
    assert (hub["serves"], hub["milestone"], hub["acting_for"], hub["helpers"]) == ("notes", "m", "the owner", 1) and "before 1" in hub["metric"] and hub["structure"][0].startswith("main")


def test_ids_sort_in_the_order_they_were_made_and_events_carry_a_sequence_per_session():
    ids = Ids(clock=lambda: 5.0)
    made = [ids.make("msg") for _ in range(50)]
    assert made == sorted(made) and len(set(made)) == 50 and re.fullmatch(r"msg_[0-9a-f]{12}[A-Za-z0-9]{14}", made[0])
    store, root, t = make()
    t.handle(RunStarted(goal="g"))
    seqs = [e["durable"]["seq"] for _, e in store.log if "durable" in e and e["durable"]["aggregateID"] == root]
    assert seqs == list(range(len(seqs)))
