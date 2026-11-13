"""``ahohs acp``: the mapping of session events to protocol updates (pure), and the agent served over stdio against the hub's own ACP client (its steering extension included) with a
scripted fake harness: start, steps, a helper, permission approved and refused, cancel, resume and steering. No model, no network. The round trips need the optional SDK (extra acp)."""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

import pytest

from hubofhubs.the_consciousness.ai_session_experience.acp_agent import mapping
from hubofhubs.the_consciousness.ai_session_experience.session_events import AgentEnded, AgentStarted, Finished, RunStarted, Step, Waiting

AGENT = [sys.executable, "-m", "hubofhubs.the_consciousness.ai_session_experience.acp_agent", "--demo", "--pause", "0.12"]


# --- the mapping, with no protocol library ----------------------------------------------------------------------------------------

def test_a_step_is_one_tool_call_started_then_updated_with_its_kind_and_state_mapped():
    t = mapping.Translator()
    first = t.updates(Step(step_id="s1", kind="edit", label="b.txt", state="running"))
    again = t.updates(Step(step_id="s1", kind="edit", label="b.txt", state="done"))
    assert first[0]["sessionUpdate"] == "tool_call" and first[0]["kind"] == "edit" and first[0]["status"] == "in_progress"
    assert again[0]["sessionUpdate"] == "tool_call_update" and again[0]["toolCallId"] == first[0]["toolCallId"] and again[0]["status"] == "completed"
    assert {k: mapping.KINDS[k] for k in ("read", "run", "check", "tool")} == {"read": "read", "run": "execute", "check": "execute", "tool": "other"}
    blocked = t.updates(Step(step_id="s2", kind="run", label="rm x", state="blocked", detail="needs approval"))[0]
    assert blocked["status"] == "completed" and "could not be checked" in blocked["title"] and "needs approval" not in blocked["title"]      # one plain quiet line; the raw text is in the detail
    outside = t.updates(Step(step_id="s3", kind="run", label="head x", state="blocked", detail="head in '/elsewhere/x' was blocked"))[0]
    assert "not allowed in this folder" in outside["title"] and "/elsewhere" not in outside["title"]
    assert t.updates(Step(step_id="s4", kind="tool", label="TaskCreate", state="done")) == []      # the agent's own task list is never drawn


def test_a_helper_is_a_tool_call_titled_with_its_task_and_solution_and_its_steps_name_it():
    t = mapping.Translator()
    start = t.updates(AgentStarted(agent_id="a1", task="write the tests", solution="tests"))[0]
    assert start["title"].startswith("Helper: write the tests") and "(tests)" in start["title"]
    step = t.updates(Step(step_id="x", kind="edit", label="t.py", state="done", agent_id="a1"))[0]
    assert step["title"].startswith("[write the tests] edit t.py")
    assert t.updates(Step(step_id="d", kind="delegate", label="write the tests", state="done")) == []      # the helper's own call already says it
    end = t.updates(AgentEnded(agent_id="a1", state="met", calls=2, summary="ok"))[0]
    assert end["status"] == "completed" and "2 calls" in end["content"][0]["content"]["text"]


def test_the_start_names_what_the_work_serves_who_the_ai_acts_for_and_the_metric_before():
    t = mapping.Translator(acting_for="Sam")
    ups = t.updates(RunStarted(solution="notes", milestone="ship", frame="Notes, then deploy.", metric="checks", metric_before=1.0))
    text = ups[0]["content"]["text"]
    assert "Serving notes, milestone: ship" in text and "Acting for Sam" in text and "checks before: 1" in text and ups[1]["sessionUpdate"] == "plan"


def test_the_end_maps_to_a_stop_reason_and_a_closing_report_with_the_metric_after():
    t = mapping.Translator()
    t.updates(RunStarted(metric="checks", metric_before=1.0))
    stop, ups, meta = t.closing(Finished(outcome="met", report="All done.", changed=("a.txt",), metric_after=3.0, cost_usd=0.01))
    text = ups[0]["content"]["text"]
    assert stop == "end_turn" and "Done: the goal was met" in text and "Changed (1): a.txt" in text and "before 1, after 3" in text and meta["hub"]["outcome"] == "met"
    stop, ups, _ = t.closing(Finished(outcome="stopped", session_id="sess-1"))
    assert stop == "cancelled" and "load session sess-1" in ups[0]["content"]["text"]
    assert mapping.Translator().closing(Finished(outcome="failed", error="boom"))[0] == "end_turn"


def test_a_risky_step_is_a_permission_request_with_its_preview_and_only_a_selected_approve_approves():
    ask = mapping.permission_request(Waiting(ask_id="ask-1", question="Run deploy?", preview="creates deployed.txt"), "write the tests")
    assert "creates deployed.txt" in ask["toolCall"]["content"][0]["content"]["text"] and "write the tests asks" in ask["toolCall"]["title"]
    assert [o["optionId"] for o in ask["options"]] == ["approve", "refuse"]
    assert mapping.choice_of({"outcome": {"outcome": "selected", "optionId": "approve"}}) == "approve"
    for other in ({"outcome": {"outcome": "cancelled"}}, {"outcome": {"outcome": "selected", "optionId": "refuse"}}, {}, None):
        assert mapping.choice_of(other) == "refuse"


def test_a_prompt_is_its_text_blocks():
    assert mapping.prompt_text([{"type": "text", "text": "ship it"}, {"type": "image"}, {"type": "resource", "resource": {"text": "notes"}}]) == "ship it\nnotes"


def test_without_the_sdk_the_agent_says_how_to_install_it(monkeypatch):
    from hubofhubs.the_consciousness.ai_session_experience.acp_agent import server
    monkeypatch.setitem(sys.modules, "acp", None)
    with pytest.raises(server.AcpUnavailable, match="pip install 'hubofhubs\\[acp\\]'"):
        server.sdk()


# --- the agent over stdio against the hub's own ACP client ---------------------------------------------------------------------------

acp = pytest.importorskip("acp")


def environment():
    return {"PATH": "/usr/bin:/bin", "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}


async def with_agent(client, folder, script):
    from hubofhubs.the_world.tools.delegated_agent_sessions.acp_session import open_agent_connection
    async with open_agent_connection(client, AGENT, env=environment(), cwd=folder) as (conn, _process):
        client.on_connect(conn)
        init = await conn.initialize(protocol_version=1, client_capabilities={"fs": {"readTextFile": False, "writeTextFile": False}})
        session = await conn.new_session(cwd=folder, mcp_servers=[])
        return await script(conn, init, session.session_id)


def hub_client(folder, **config):
    from hubofhubs.the_world.tools.delegated_agent_sessions.acp_config import AcpConfig
    from hubofhubs.the_world.tools.delegated_agent_sessions.acp_session import AcpRun, AcpSessionClient
    ticks = []
    run = AcpRun(cfg=AcpConfig(working_dir=folder, **config), goal="ship it", run_id="r", emit=lambda e: ticks.append((e.data.get("phase"), e.text)))
    run.loop = asyncio.get_event_loop()
    return AcpSessionClient(run), run, ticks


def test_the_hub_client_and_the_hub_agent_steer_approve_and_finish_together():
    folder = tempfile.mkdtemp(prefix="acp-")

    async def go():
        client, run, ticks = hub_client(folder, skip_permissions=True)

        async def script(conn, init, session_id):
            run.conn, run.session_id = conn, session_id
            run.steering_supported = bool((init.field_meta or {}).get("steering", {}).get("supported"))

            async def steer():
                await asyncio.sleep(0.25)
                return await run.inject_steering("name the file notes.md")
            steering = asyncio.create_task(steer())
            response = await conn.prompt(session_id=session_id, prompt=[{"type": "text", "text": "ship it"}])
            return response, await steering, run.steering_supported
        return await with_agent(client, folder, script), ticks
    (response, injected, advertised), ticks = asyncio.run(go())
    texts = " | ".join(text for _, text in ticks)
    assert advertised and injected is True
    assert response.stop_reason == "end_turn" and response.field_meta["hub"]["outcome"] == "met"
    assert "Taken up: name the file notes.md" in texts and "Helper: write the tests" in texts and "Done: the goal was met" in texts
    assert Path(folder, "deployed.txt").exists()          # the permission request was answered approve by the hub client's permission model


def test_a_refused_permission_never_runs_the_step_and_the_report_lists_it():
    folder = tempfile.mkdtemp(prefix="acp-")

    async def go():
        client, run, ticks = hub_client(folder, skip_permissions=False, allowed_tools=["none"])      # the hub client's own model rejects the ask

        async def script(conn, init, session_id):
            return await conn.prompt(session_id=session_id, prompt=[{"type": "text", "text": "ship it"}])
        return await with_agent(client, folder, script), ticks
    response, ticks = asyncio.run(go())
    assert not Path(folder, "deployed.txt").exists()
    assert "Denied" in " ".join(text for _, text in ticks) and response.field_meta["hub"]["outcome"] in ("met", "unmet")


class Recorder:
    """A bare ACP client that records every update and answers permission as told."""

    def __init__(self, answer="approve"):
        self.updates, self.asked, self.answer = [], [], answer

    def on_connect(self, conn):
        self.conn = conn

    async def session_update(self, session_id, update, **kwargs):
        self.updates.append(update.model_dump(mode="json", by_alias=True, exclude_none=True) if hasattr(update, "model_dump") else update)

    async def request_permission(self, session_id, tool_call, options, **kwargs):
        self.asked.append((tool_call, options))
        return {"outcome": {"outcome": "selected", "optionId": self.answer}}

    async def ext_method(self, method, params):
        return {}

    async def ext_notification(self, method, params):
        return None


def test_a_client_sees_tool_calls_a_plan_a_permission_request_with_its_preview_and_a_closing_report():
    folder = tempfile.mkdtemp(prefix="acp-")
    client = Recorder("refuse")

    async def script(conn, init, session_id):
        return await conn.prompt(session_id=session_id, prompt=[{"type": "text", "text": "ship it"}])
    response = asyncio.run(with_agent(client, folder, script))
    kinds = [u["sessionUpdate"] for u in client.updates]
    assert {"tool_call", "tool_call_update", "plan", "agent_message_chunk"} <= set(kinds)
    assert [c["kind"] for c in client.updates if c["sessionUpdate"] == "tool_call" and c["title"].startswith(("read", "edit"))][:2] == ["read", "read"]
    tool_call, options = client.asked[0]
    preview = (tool_call.content[0] if hasattr(tool_call, "content") else tool_call["content"][0])
    assert "deploy" in str(tool_call) and "will change" in str(preview).lower() or "creates" in str(preview)
    assert not Path(folder, "deployed.txt").exists()
    refused = [u for u in client.updates if u["sessionUpdate"] == "tool_call_update" and "you refused it" in u.get("title", "")][-1]
    assert refused["status"] == "failed" and "not run because you refused it" in refused["title"]
    last = [u for u in client.updates if u["sessionUpdate"] == "agent_message_chunk"][-1]["content"]["text"]
    assert "checks passing: before 1, after 1" in last          # the refused deploy did not move the metric
    assert response.field_meta["hub"]["outcome"] in ("met", "unmet")


def test_cancel_stops_the_turn_keeping_work_and_load_then_prompt_resumes_it():
    folder = tempfile.mkdtemp(prefix="acp-")
    client = Recorder("approve")

    async def script(conn, init, session_id):
        running = asyncio.create_task(conn.prompt(session_id=session_id, prompt=[{"type": "text", "text": "ship it"}]))
        await asyncio.sleep(0.6)
        await conn.cancel(session_id=session_id)
        first = await running
        await conn.load_session(cwd=folder, session_id=session_id, mcp_servers=[])
        second = await conn.prompt(session_id=session_id, prompt=[{"type": "text", "text": "go on"}])
        return first, second
    first, second = asyncio.run(with_agent(client, folder, script))
    assert first.stop_reason == "cancelled" and first.field_meta["hub"]["outcome"] == "stopped" and first.field_meta["hub"]["sessionId"]
    assert second.stop_reason == "end_turn" and second.field_meta["hub"]["outcome"] == "met"
    assert second.field_meta["hub"]["sessionId"] == first.field_meta["hub"]["sessionId"]
    texts = " ".join(u["content"]["text"] for u in client.updates if u["sessionUpdate"] == "agent_message_chunk")
    assert "Stopped: finished work is kept" in texts and "Resuming session" in texts


def test_steering_with_no_turn_running_is_answered_prompt_required():
    folder = tempfile.mkdtemp(prefix="acp-")
    client = Recorder()

    async def script(conn, init, session_id):
        return await conn.ext_method("session/steering", {"sessionId": session_id, "prompt": [{"type": "text", "text": "hello"}], "_meta": {"steering": {"idleBehavior": "promptRequired"}}})
    assert asyncio.run(with_agent(client, folder, script))["outcome"] == "promptRequired"
