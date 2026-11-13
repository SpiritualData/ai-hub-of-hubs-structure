"""A consumer's own slash commands and header lines reach the client through the bridge: listed, run from the menu or as a typed line, said as one quiet row, never sent to the AI."""
from hubofhubs.the_consciousness.ai_session_experience.opencode_server import routes
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge import Bridge, SlashCommand


class Idle:
    name = "idle"

    def __init__(self):
        self.goals = []

    def start(self, goal, sink, resume_session_id=""):
        self.goals.append(goal)
        raise AssertionError("a command must never start a run")

    def control(self, control):
        return False


def make(said=None, header=None):
    calls = []

    def run(argument):
        calls.append(argument)
        return said if said is not None else [f"set to {argument}", "second line"]

    harness = Idle()
    bridge = Bridge(lambda folder: harness, "/work", commands=[SlashCommand("topic", "Choose the topic", run)], header=header)
    return bridge, calls, harness


def rows(bridge):
    return [m for m in bridge.store.messages[bridge.root] if m["type"] == "synthetic"]


def test_the_command_list_names_the_consumers_commands():
    bridge, _, _ = make()
    listed = routes.handle(bridge, "GET", "/api/command", {}, None)[1]["data"]
    assert listed == [{"name": "topic", "description": "Choose the topic"}]


def test_choosing_a_command_in_the_menu_runs_it_and_says_one_row():
    bridge, calls, harness = make()
    assert routes.handle(bridge, "POST", f"/api/session/{bridge.root}/command", {}, {"name": "topic", "text": "tomatoes"})[0] == 204
    assert calls == ["tomatoes"] and harness.goals == []
    assert [r["text"] for r in rows(bridge)] == ["set to tomatoes\nsecond line"]


def test_an_unknown_command_is_not_found():
    bridge, _, _ = make()
    assert routes.handle(bridge, "POST", f"/api/session/{bridge.root}/command", {}, {"name": "nope", "text": ""})[0] == 404


def test_a_typed_command_line_runs_the_command_and_is_not_a_message():
    bridge, calls, harness = make()
    made = bridge.prompt("/topic tomatoes please")
    assert made["kind"] == "command" and calls == ["tomatoes please"] and harness.goals == [] and not bridge.running


def test_a_command_that_fails_says_so_and_the_session_goes_on():
    bridge = Bridge(lambda folder: None, "/work", commands=[SlashCommand("boom", "Fails", lambda argument: 1 / 0)])
    assert bridge.command("/boom")
    assert "failed: ZeroDivisionError" in rows(bridge)[0]["text"]


def test_a_command_that_says_nothing_adds_no_row():
    bridge, _, _ = make(said=[])
    bridge.command("topic", "x")
    assert rows(bridge) == []


def test_the_header_lines_reach_the_plugin_through_the_metadata_and_follow_a_command():
    current = ["Matched: Garden"]
    bridge, _, _ = make(header=lambda: list(current))
    bridge.translator.publish()
    assert bridge.store.sessions[bridge.root]["metadata"]["hub"]["header"] == ["Matched: Garden"]
    current[:] = ["Selected: Orchard", "Looked at 2 sources."]
    bridge.command("topic", "orchard")
    assert bridge.store.sessions[bridge.root]["metadata"]["hub"]["header"] == ["Selected: Orchard", "Looked at 2 sources."]


def test_header_lines_that_cannot_be_read_are_left_out():
    def broken():
        raise RuntimeError("no")
    bridge, _, _ = make(header=broken)
    assert bridge.translator.header_lines() == []
