"""The HTTP side of ``opencode_server``: the route set replayed from a recorded client trace (no client needed), the wire shapes, the run decisions made from server state (start, steer, stop,
resume, follow-up, a refused step), the event stream (heartbeat, reconnect, replay from the last event id, a snapshot that agrees with the events), the per-run password and the loopback-only default."""
import base64
import http.client
import json
import threading
import time
from pathlib import Path

import pytest

from hubofhubs.the_consciousness.ai_session_experience.opencode_server import routes
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge import Bridge
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.server import OpencodeServer, is_loopback
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    Approve, Capabilities, Finished, Refuse, RunStarted, Steer, Step, Stop, Waiting)

TRACE = json.loads((Path(__file__).parent / "fixtures" / "client_trace.json").read_text())


class Fake:
    """A harness the test drives: it starts, reads a file, optionally waits to be released or stopped, and finishes; it records every control and every start."""
    name = "fake"

    def __init__(self, steer=True, ask=False):
        self.capabilities = Capabilities(stop=True, resume=True, steer=steer, approve=True)
        self.controls, self.starts, self.ask = [], [], ask
        self.release, self.stopped = threading.Event(), threading.Event()
        self.took = []

    def control(self, control):
        self.controls.append(control)
        if isinstance(control, Stop):
            self.stopped.set()
        if isinstance(control, Steer):
            self.took.append(control)
        return True

    def start(self, goal, sink, resume_session_id=""):
        self.starts.append((goal, resume_session_id))
        sink(RunStarted(goal=goal, harness="fake", session_id="S1", resumed=bool(resume_session_id)))
        sink(Step(step_id=f"r{len(self.starts)}", kind="read", label="a.txt", state="running"))
        if self.ask:
            sink(Waiting(ask_id="ask-1", question="Deploy?", risky="deploy", preview="creates x"))
            while not any(isinstance(c, (Approve, Refuse)) for c in self.controls):
                time.sleep(0.01)
            refused = any(isinstance(c, Refuse) for c in self.controls)
            sink(Step(step_id=f"r{len(self.starts)}", kind="read", label="a.txt", state="blocked" if refused else "done", detail="refused by the person" if refused else ""))
            done = Finished(outcome="unmet" if refused else "met", report="Stopped: refused." if refused else "ok", session_id="S1")
            sink(done)
            return done
        while not (self.release.is_set() or self.stopped.is_set()):
            time.sleep(0.01)
        for control in self.took:
            sink(Step(step_id=control.message_id, kind="message-received", label=control.text, state="done"))
        self.took = []
        if self.stopped.is_set():
            self.stopped.clear()
            done = Finished(outcome="stopped", session_id="S1")
        else:
            sink(Step(step_id=f"r{len(self.starts)}", kind="read", label="a.txt", state="done"))
            done = Finished(outcome="met", report="All done.", session_id="S1")
        sink(done)
        return done


def make(**kwargs):
    harness = Fake(**kwargs)
    return Bridge(lambda folder: harness, "/work", steer_wait=0.3), harness


def fill(template, bridge):
    return template.replace("{session}", bridge.root).replace("{request}", "ask-1")


def messages(bridge, kind):
    return [m for m in bridge.store.messages[bridge.root] if m["type"] == kind]


# --- the route set -------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("interface", ["full_screen", "inline"])
def test_every_request_the_recorded_client_made_is_answered(interface):
    bridge, harness = make(ask=True)
    for method, template in TRACE[interface]:
        if template == "/api/event":
            continue
        body = {"text": "go", "id": "msg_client0000000000000000000"} if template.endswith("/prompt") else {"decision": "once"} if template.endswith("/reply") else {}
        if template.endswith("/wait"):
            harness.ask = False
            bridge.running = False
        status, answer = routes.handle(bridge, method, fill(template, bridge), {}, body)
        assert status in (200, 204), (method, template, status, answer)
    assert TRACE["client"] == "2.2.7"


def test_lists_are_wrapped_and_the_message_list_honours_the_order():
    bridge, _ = make()
    for path in ("/api/agent", "/api/model", "/api/provider", "/api/command", "/api/permission/request"):
        status, answer = routes.handle(bridge, "GET", path, {}, None)
        assert status == 200 and set(answer) == {"location", "data"} and answer["location"] == {"directory": "/work"}
    status, session = routes.handle(bridge, "GET", "/api/session", {}, None)
    assert session["cursor"] == {"previous": None, "next": None} and session["data"][0]["id"] == bridge.root
    bridge.store.enqueue_user(bridge.root, "one")
    bridge.store.deliver(bridge.root, bridge.store.pending[bridge.root][0]["id"])
    bridge.store.synthetic(bridge.root, "x", "two")
    ascending = routes.handle(bridge, "GET", f"/api/session/{bridge.root}/message", {"order": ["asc"]}, None)[1]["data"]
    descending = routes.handle(bridge, "GET", f"/api/session/{bridge.root}/message", {"order": ["desc"]}, None)[1]["data"]
    assert [m["type"] for m in ascending] == ["user", "synthetic"] and [m["type"] for m in descending] == ["synthetic", "user"]


def test_an_unknown_route_or_session_is_a_json_404_and_the_info_names_the_tested_version():
    bridge, _ = make()
    assert routes.handle(bridge, "GET", "/api/session/nope", {}, None)[0] == 404
    assert routes.handle(bridge, "GET", "/api/telemetry", {}, None) == (404, routes.NOT_FOUND)
    status, info = routes.handle(bridge, "GET", "/api/info", {}, None, 4321)
    assert info["version"] == "2.2.7" and info["urls"] == ["http://127.0.0.1:4321"]


# --- the run, decided from the server's own state ----------------------------------------------------------------------------------------------------

def test_a_first_prompt_starts_the_run_with_the_clients_message_id_and_a_prompt_while_it_works_is_a_steer():
    bridge, harness = make()
    made = bridge.prompt("do the work", "msg_first000000000000000000000")
    assert made["kind"] == "start" and bridge.running
    time.sleep(0.2)
    assert [m["id"] for m in messages(bridge, "user")] == ["msg_first000000000000000000000"] and harness.starts == [("do the work", "")]
    note = bridge.prompt("use the short name", "msg_note00000000000000000000")
    assert note["kind"] == "steer" and isinstance(harness.controls[-1], Steer) and harness.controls[-1].message_id == "msg_note00000000000000000000"
    harness.release.set()
    assert bridge.wait(5)
    assert [m["id"] for m in messages(bridge, "user")] == ["msg_first000000000000000000000", "msg_note00000000000000000000"]      # taken up, not said twice


def test_an_interrupt_is_a_stop_and_the_next_prompt_resumes_the_session_the_run_ended_with():
    bridge, harness = make()
    bridge.prompt("do the work", "msg_a")
    time.sleep(0.2)
    assert bridge.interrupt() is True and isinstance(harness.controls[-1], Stop)
    assert bridge.wait(5) and bridge.last_outcome == "stopped" and messages(bridge, "idle")[-1]["outcome"] == "interrupted"
    assert any("Type resume" in m["description"] for m in messages(bridge, "synthetic"))
    bridge.prompt("resume", "msg_b")
    time.sleep(0.2)
    assert harness.starts[-1] == ("resume", "S1")
    harness.release.set()
    assert bridge.wait(5) and bridge.last_outcome == "met"
    bridge.prompt("one more thing", "msg_c")                    # a follow-up after a finished run continues the hub session too
    time.sleep(0.2)
    assert harness.starts[-1] == ("one more thing", "S1")
    harness.release.set()
    assert bridge.wait(5)


def test_an_interrupt_with_no_run_is_not_accepted():
    bridge, _ = make()
    assert bridge.interrupt() is False


def test_approve_and_a_refusal_are_controls_and_a_refused_step_shows_its_reason():
    for decision, outcome in (("once", "met"), ("reject", "unmet")):
        bridge, harness = make(ask=True)
        bridge.prompt("go", "msg_a")
        for _ in range(100):
            if bridge.store.open_requests():
                break
            time.sleep(0.02)
        (request,) = bridge.store.open_requests()
        assert request["action"] == "shell" and "creates x" in request["resources"][1]
        status, _ = routes.handle(bridge, "POST", f"/api/session/{bridge.root}/permission/{request['id']}/reply", {}, {"decision": decision, "message": "not now"})
        assert status == 204 and bridge.wait(5) and bridge.last_outcome == outcome
        assert isinstance(harness.controls[-1], Approve if decision == "once" else Refuse)
        if decision == "reject":
            tool = [p for m in messages(bridge, "assistant") for p in m["content"] if p["type"] == "tool"][0]
            assert tool["state"]["error"]["message"] == "Refused: refused by the person"
            assert harness.controls[-1].reason == "not now"


def test_a_harness_that_cannot_take_a_message_leaves_it_waiting_and_the_next_run_starts_with_it():
    bridge, harness = make(steer=False)
    bridge.prompt("do the work", "msg_a")
    time.sleep(0.2)
    queued = bridge.prompt("then this", "msg_b")
    assert queued["kind"] == "queued" and [i["id"] for i in bridge.store.pending[bridge.root]] == ["msg_b"]
    harness.release.set()
    for _ in range(100):
        if len(harness.starts) == 2:
            break
        time.sleep(0.02)
    assert harness.starts[1] == ("then this", "S1")
    harness.release.set()
    assert bridge.wait(5)


def test_a_harness_that_raises_ends_the_run_failed_and_says_so():
    class Broken(Fake):
        def start(self, goal, sink, resume_session_id=""):
            raise RuntimeError("boom")
    bridge = Bridge(lambda folder: Broken(), "/work")
    bridge.prompt("go", "msg_a")
    assert bridge.wait(5) and bridge.last_outcome == "failed" and messages(bridge, "idle")[-1]["outcome"] == "failed"


# --- the server: password, loopback, the event stream ------------------------------------------------------------------------------------------------

def request(server, method, path, body=None, token=True, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
    sent = dict(headers or {})
    if token:
        sent["authorization"] = "Basic " + base64.b64encode(f"opencode:{server.token}".encode()).decode()
    connection.request(method, path, body=json.dumps(body) if body is not None else None, headers=sent)
    answer = connection.getresponse()
    data = answer.read()
    connection.close()
    return answer.status, (json.loads(data) if data else None)


def test_the_server_listens_on_the_loopback_interface_on_a_free_port_and_wants_its_password():
    bridge, _ = make()
    server = OpencodeServer(bridge).start()
    try:
        assert server.httpd.server_address[0] == "127.0.0.1" and server.port > 0 and len(server.token) >= 24
        assert request(server, "GET", "/api/info", token=False)[0] == 401
        assert request(server, "GET", "/api/info", headers={"authorization": "Basic " + base64.b64encode(b"opencode:wrong").decode()}, token=False)[0] == 401
        status, info = request(server, "GET", "/api/info")
        assert status == 200 and info["version"] == "2.2.7"
        assert request(server, "POST", f"/api/session/{bridge.root}/model", {"model": {"id": "hub", "providerID": "hub"}})[0] == 204
    finally:
        server.stop()


def test_a_host_that_is_not_loopback_is_refused_unless_it_is_asked_for():
    bridge, _ = make()
    assert is_loopback("127.0.0.1") and is_loopback("::1") and is_loopback("localhost") and not is_loopback("0.0.0.0") and not is_loopback("192.168.1.5")
    for host in ("0.0.0.0", "192.168.1.5", "example.org"):
        with pytest.raises(ValueError, match="loopback"):
            OpencodeServer(bridge, host=host)
    OpencodeServer(bridge, host="127.0.0.1", allow_remote=True).httpd.server_close()


def read_events(server, count, headers=None, timeout=10):
    """The first ``count`` data events of a stream (comments are counted separately)."""
    connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=timeout)
    sent = {"authorization": "Basic " + base64.b64encode(f"opencode:{server.token}".encode()).decode(), **(headers or {})}
    connection.request("GET", "/api/event", headers=sent)
    answer = connection.getresponse()
    events, comments, ids = [], 0, []
    while len(events) < count:
        line = answer.fp.readline().decode()
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
        elif line.startswith(": "):
            comments += 1
        elif line.startswith("id: "):
            ids.append(line[4:].strip())
    connection.close()
    return events, comments, ids


def test_the_stream_starts_with_server_connected_and_carries_a_heartbeat_while_quiet():
    bridge, _ = make()
    server = OpencodeServer(bridge, heartbeat=0.05).start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.port, timeout=10)
        connection.request("GET", "/api/event", headers={"authorization": "Basic " + base64.b64encode(f"opencode:{server.token}".encode()).decode()})
        answer = connection.getresponse()
        assert answer.status == 200 and answer.getheader("content-type") == "text/event-stream"
        assert json.loads(answer.fp.readline().decode()[6:])["type"] == "server.connected"
        seen = [answer.fp.readline().decode() for _ in range(4)]
        assert any(line.startswith(": heartbeat") for line in seen)
        connection.close()
    finally:
        server.stop()


def test_a_client_that_reconnects_names_the_last_event_and_gets_what_it_missed_and_the_snapshot_agrees():
    bridge, harness = make()
    server = OpencodeServer(bridge, heartbeat=0.05).start()
    try:
        bridge.prompt("do the work", "msg_a")
        time.sleep(0.2)
        first, _, ids = read_events(server, 1, headers={"last-event-id": ""})
        seen_before = bridge.store.log[-1][1]["id"]
        harness.release.set()
        assert bridge.wait(5)
        events, _, _ = read_events(server, 1 + 3, headers={"last-event-id": seen_before})
        missed = [e["type"] for e in events[1:]]
        assert missed and set(missed) <= {e["type"] for _, e in bridge.store.log}
        assert "session.execution.succeeded" in [e["type"] for _, e in list(bridge.store.log)[-10:]]
        status, page = request(server, "GET", f"/api/session/{bridge.root}/message?order=asc")
        texts = [p["text"] for m in page["data"] if m["type"] == "assistant" for p in m["content"] if p["type"] == "text"]
        assert status == 200 and any("All done." in t for t in texts) and page["data"][-1]["type"] == "idle"
    finally:
        server.stop()


def test_a_store_replays_only_events_after_the_one_named_and_nothing_for_an_unknown_id():
    bridge, _ = make()
    store = bridge.store
    store.synthetic(bridge.root, "a", "a")
    mark = store.log[-1][1]["id"]
    store.synthetic(bridge.root, "b", "b")
    waiting = store.subscribe(mark)
    assert waiting.get_nowait()["data"]["text"] == "b" and waiting.empty()
    assert store.subscribe("evt_unknown").empty()


# --- the hub's own scripted harness (the stream runner's contract), over HTTP, as the protocol round trips of the ACP arm's cases -----------------------------

def scripted_server(tmp_path, turns, pause=0.05):
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import stream_kit
    kit = stream_kit(str(tmp_path), turns, pause=pause)
    bridge = Bridge(lambda folder: kit.harness, str(tmp_path))
    return bridge, OpencodeServer(bridge).start(), kit


def wait_for(check, seconds=15):
    end = time.time() + seconds
    while time.time() < end:
        if check():
            return True
        time.sleep(0.02)
    return False


def test_a_risky_step_waits_with_its_preview_and_only_runs_once_approved_over_http(tmp_path):
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import report, turn, use
    for decision, ran in (("once", True), ("reject", False)):
        (tmp_path / decision).mkdir()
        bridge, server, kit = scripted_server(tmp_path / decision, [turn(use("deploy", "release 1.0")), turn(report("Finished."))])
        try:
            assert request(server, "POST", f"/api/session/{bridge.root}/prompt", {"id": "msg_a", "text": "ship it"})[0] == 200
            assert wait_for(lambda: bridge.store.open_requests())
            (ask,) = bridge.store.open_requests()
            assert not (tmp_path / decision / "deployed.txt").exists()                  # nothing ran while it waited
            assert request(server, "POST", f"/api/session/{bridge.root}/permission/{ask['id']}/reply", {"decision": decision, "message": "no"})[0] == 204
            assert bridge.wait(15)
            assert (tmp_path / decision / "deployed.txt").exists() is ran
        finally:
            server.stop()


def test_a_stop_then_a_prompt_resumes_without_repeating_finished_work_over_http(tmp_path):
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import edit, report, turn
    bridge, server, kit = scripted_server(tmp_path, [turn(edit("one.txt")), turn(edit("two.txt")), turn(edit("three.txt"), report("All three."))], pause=0.3)
    try:
        request(server, "POST", f"/api/session/{bridge.root}/prompt", {"id": "msg_a", "text": "go"})
        assert wait_for(lambda: (tmp_path / "one.txt").exists())
        assert request(server, "POST", f"/api/session/{bridge.root}/interrupt?resume=true")[1] == {"interrupted": True}
        assert bridge.wait(15) and bridge.last_outcome == "stopped"
        request(server, "POST", f"/api/session/{bridge.root}/prompt", {"id": "msg_b", "text": "resume"})
        assert bridge.wait(15) and bridge.last_outcome == "met"
        texts = [p["text"] for m in bridge.store.messages[bridge.root] if m["type"] == "assistant" for p in m["content"] if p["type"] == "text"]
        assert all((tmp_path / name).exists() for name in ("one.txt", "two.txt", "three.txt")) and any("All three." in t for t in texts)
        edits = [p for m in bridge.store.messages[bridge.root] if m["type"] == "assistant" for p in m["content"] if p["type"] == "tool" and p["name"] == "edit"]
        assert len({p["state"]["input"]["path"] for p in edits}) == len(edits)         # an edit is not drawn twice after the resume
    finally:
        server.stop()


def test_a_message_typed_while_it_works_is_taken_up_and_shown_sent_then_taken_up_over_http(tmp_path):
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import edit, read, report, turn
    bridge, server, kit = scripted_server(tmp_path, [turn(read("a.txt")), turn(edit("b.txt")), turn(edit("c.txt"), report("Done."))], pause=0.3)
    (tmp_path / "a.txt").write_text("alpha\n")
    try:
        request(server, "POST", f"/api/session/{bridge.root}/prompt", {"id": "msg_a", "text": "go"})
        assert wait_for(lambda: bridge.running and bridge.store.messages[bridge.root])
        assert request(server, "POST", f"/api/session/{bridge.root}/prompt", {"id": "msg_b", "text": "use the short name"})[0] == 200
        sent = bridge.translator.hub_metadata()["hub"]["corrections"]
        assert sent and sent[0]["text"] == "use the short name"
        assert bridge.wait(20)
        assert bridge.translator.hub_metadata()["hub"]["corrections"][0]["taken_up"] is True
        users = [m["text"] for m in bridge.store.messages[bridge.root] if m["type"] == "user"]
        assert users == ["go", "use the short name"] and any("use the short name" in prompt for prompt in kit.trace.prompts)      # the harness's own model was given it
    finally:
        server.stop()
