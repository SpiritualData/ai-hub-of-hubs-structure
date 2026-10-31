"""The ACP deep runner (``hubofhubs.deep.acp_*``): offline, the protocol connection is a scripted fake, nothing is spawned.

Settings are arguments: the Node and agent fallbacks, the names a consumer gives them in the messages, the escalation marker, the
environment the child starts from and the object an escalated permission ask becomes are all passed in.
"""
from __future__ import annotations

import asyncio
import subprocess
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from hubofhubs.deep import acp_config, acp_runner
from hubofhubs.deep.acp_config import (
    ALLOW,
    HUMAN,
    REJECT,
    AcpConfig,
    AcpSettings,
    EscalationAsk,
    build_agent_argv,
    classify_permission,
    permission_response,
    resolve_agent_entry,
    resolve_node_binary,
    select_option,
)
from hubofhubs.deep.acp_protocol import (
    PHASE_DONE,
    PHASE_MESSAGE,
    PHASE_TOOL_RESULT,
    landed_file_change,
    translate_session_update,
    usage_from_prompt_response,
)
from hubofhubs.deep.acp_runner import AcpDeepRunner, acp_model_family
from hubofhubs.deep.settings import GoalSettings
from hubofhubs.ports.events import EVENT_EXEC


def ns(**kwargs: Any) -> SimpleNamespace:
    return SimpleNamespace(**kwargs)


class FakeConn:
    def __init__(self, *, updates=None, stop_reason="end_turn", usage=None, permission_asks=None):
        self.updates, self.stop_reason, self.usage = updates or [], stop_reason, usage
        self.permission_asks, self.permission_answers, self.client = permission_asks or [], [], None

    async def initialize(self, *, protocol_version, client_capabilities=None, **kw):
        return ns(field_meta={})

    async def new_session(self, *, cwd, mcp_servers=None, **kw):
        self.cwd = cwd
        return ns(session_id="sess-1", config_options=[], modes=None)

    async def prompt(self, *, session_id, prompt):
        self.prompt_sent = prompt
        for update in self.updates:
            await self.client.session_update(session_id, update)
        for ask in self.permission_asks:
            self.permission_answers.append(await self.client.request_permission(session_id, ask["tool_call"], ask["options"]))
        return ns(stop_reason=self.stop_reason, usage=self.usage)

    async def cancel(self, *, session_id):
        pass

    async def close_session(self, *, session_id):
        pass


def install(monkeypatch, conn):
    @asynccontextmanager
    async def fake_open(client, argv, *, env, cwd):
        conn.client, conn.argv, conn.env = client, argv, env
        client.on_connect(conn)
        yield conn, None

    monkeypatch.setattr(acp_runner, "open_agent_connection", fake_open)


def config(**over: Any) -> AcpConfig:
    base: Dict[str, Any] = dict(working_dir="/work", agent_command="/opt/acp/agent", steering_poll_seconds=0.01,
                                heartbeat_seconds=1000.0, timeout_seconds=20.0)
    base.update(over)
    return AcpConfig(**base)


def chunk(text: str, message_id: str = "m1") -> Dict[str, Any]:
    return {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": text}, "messageId": message_id}


def test_the_stream_reaches_the_sink_and_the_last_message_is_the_result(monkeypatch):
    conn = FakeConn(updates=[chunk("looking"), {"sessionUpdate": "tool_call", "toolCallId": "t1", "title": "ls", "kind": "execute"},
                             {"sessionUpdate": "tool_call_update", "toolCallId": "t1", "status": "completed"},
                             chunk("Done.", "m2")], usage=ns(input_tokens=100, output_tokens=40))
    install(monkeypatch, conn)
    events = []
    result = AcpDeepRunner(config()).run_goal(goal="g", brief="b", emit=events.append, run_id="run-1")
    assert result.met and result.output == "Done." and result.tokens == 140
    assert all(e.type == EVENT_EXEC and e.data["run_id"] == "run-1" for e in events)
    phases = [e.data["phase"] for e in events]
    assert phases.count(PHASE_MESSAGE) == 2 and PHASE_TOOL_RESULT in phases and phases[-1] == PHASE_DONE


def test_the_consumers_marker_pauses_the_run_and_the_default_reads_none(monkeypatch):
    install(monkeypatch, FakeConn(updates=[chunk("asked.\nPAUSED-ON: dec_99")]))
    settings = AcpSettings(goal=GoalSettings(escalation_marker="PAUSED-ON:"))
    result = AcpDeepRunner(config(), settings=settings).run_goal(goal="g", brief="b")
    assert not result.met and result.decision_id == "dec_99"
    install(monkeypatch, FakeConn(updates=[chunk("asked.\nPAUSED-ON: dec_99")]))
    assert AcpDeepRunner(config()).run_goal(goal="g", brief="b").met


def test_a_non_clean_stop_and_a_silent_no_op_are_never_met(monkeypatch):
    install(monkeypatch, FakeConn(updates=[chunk("partial")], stop_reason="max_tokens"))
    result = AcpDeepRunner(config()).run_goal(goal="g", brief="b")
    assert not result.met and "TOKEN limit" in result.error
    install(monkeypatch, FakeConn())
    assert not AcpDeepRunner(config()).run_goal(goal="g", brief="b").met


def ask(tool="Bash"):
    options = [ns(kind="allow_always", option_id="allow_always"), ns(kind="reject_once", option_id="reject")]
    return {"tool_call": {"title": "run it", "_meta": {"claudeCode": {"toolName": tool}}}, "options": options}


def test_an_escalated_permission_ask_is_built_by_the_consumers_factory(monkeypatch):
    raised = []

    class Sink:
        def escalate(self, escalation):
            raised.append(escalation)
            return "decision-42"

    conn = FakeConn(updates=[chunk("asking")], permission_asks=[ask()])
    install(monkeypatch, conn)
    result = AcpDeepRunner(config(skip_permissions=False, escalation=Sink(), escalation_assignee="pat")).run_goal(
        goal="send the mail", brief="b")
    assert result.decision_id == "decision-42" and not result.met
    assert isinstance(raised[0], EscalationAsk) and raised[0].assignee == "pat" and raised[0].default_on_silence == "hold"
    assert "Bash" in raised[0].summary
    assert conn.permission_answers == [{"outcome": {"outcome": "selected", "optionId": "reject"}}]

    made = []

    def factory(**kwargs):
        made.append(kwargs)
        return ns(summary=kwargs["summary"])

    install(monkeypatch, FakeConn(updates=[chunk("asking")], permission_asks=[ask()]))
    AcpDeepRunner(config(skip_permissions=False, escalation=Sink()), settings=AcpSettings(make_escalation=factory)).run_goal(
        goal="g", brief="b")
    assert made[0]["cfg"].skip_permissions is False and made[0]["kind"] == "approve"


def test_permission_policy_is_pure():
    assert classify_permission(config(), "Bash")[0] == ALLOW
    assert classify_permission(config(disallowed_tools=["Bash"]), "Bash")[0] == REJECT
    assert classify_permission(config(allowed_tools=["Read"]), None)[0] == REJECT
    assert classify_permission(config(skip_permissions=False), "Bash")[0] == HUMAN
    options = [ns(kind="allow_once", option_id="a1"), ns(kind="reject_once", option_id="r1")]
    assert select_option(options, ("allow_always", "allow_once")) == "a1" and select_option(options, ("nope",)) is None
    assert permission_response(None) == {"outcome": {"outcome": "cancelled"}}


def test_the_child_environment_comes_from_the_settings(monkeypatch):
    conn = FakeConn(updates=[chunk("ok")])
    install(monkeypatch, conn)
    def requester(env, user_id):
        env["WHO"] = user_id
        return env

    goal = GoalSettings(run_id_env="MY_RUN", environment=lambda: {"PATH": "/bin", "ANTHROPIC_API_KEY": "k", "CLAUDECODE": "1"},
                        apply_requester=requester)
    AcpDeepRunner(config(), settings=AcpSettings(goal=goal)).run_goal(goal="g", brief="b", run_id="r1", requester_user_id="u9")
    assert conn.env["MY_RUN"] == "r1" and conn.env["WHO"] == "u9"
    assert "ANTHROPIC_API_KEY" not in conn.env and "CLAUDECODE" not in conn.env


def fake_node(monkeypatch, version):
    monkeypatch.setattr(acp_config.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(cmd, 0, stdout=version.encode(), stderr=b""))


def test_node_discovery_uses_the_settings_fallbacks_and_names_them(monkeypatch, tmp_path):
    entry = tmp_path / "index.js"
    entry.write_text("// agent\n")
    settings = AcpSettings(node_path_fallback="/opt/node22/bin/node", agent_command_fallback="/opt/acp/index.js",
                           node_path_name="MY_NODE", agent_command_name="MY_AGENT")
    assert resolve_node_binary(None, settings) == "/opt/node22/bin/node" and resolve_node_binary("/explicit/node", settings) == "/explicit/node"
    assert resolve_agent_entry(None, settings) == "/opt/acp/index.js" and resolve_agent_entry(None) != "/opt/acp/index.js"
    fake_node(monkeypatch, "v22.1.0")
    assert build_agent_argv(agent_command=str(entry), agent_args=["-v"], node_path="/n/node") == (["/n/node", str(entry), "-v"], None)
    fake_node(monkeypatch, "v20.1.0")
    argv, error = build_agent_argv(agent_command=str(entry), agent_args=[], node_path="/n/node", settings=settings)
    assert argv == [] and "Node >= 22" in error and "AcpConfig.node_path or MY_NODE" in error
    _, plain = build_agent_argv(agent_command=str(entry), agent_args=[], node_path="/n/node")
    assert "AcpConfig.node_path " in plain and "MY_NODE" not in plain
    monkeypatch.setattr(acp_config.shutil, "which", lambda name: None)
    _, missing = build_agent_argv(agent_command=None, agent_args=[], node_path=None, settings=AcpSettings(agent_command_name="MY_AGENT"))
    assert "claude-agent-acp" in missing and "AcpConfig.agent_command / MY_AGENT" in missing


def test_updates_are_translated_and_file_changes_are_read_from_structure():
    assert translate_session_update({"sessionUpdate": "available_commands_update"}) is None
    plan = translate_session_update({"sessionUpdate": "plan", "entries": [{"content": "a", "status": "completed"}, {"content": "b"}]})
    assert plan["text"] == "Plan: 2 task(s), 1 done"
    kinds, names = {}, {}
    assert landed_file_change({"sessionUpdate": "tool_call", "toolCallId": "t", "kind": "edit", "status": "pending"}, kinds, names) is None
    assert landed_file_change({"sessionUpdate": "tool_call_update", "toolCallId": "t", "status": "completed"}, kinds, names) == "t"
    assert landed_file_change({"sessionUpdate": "tool_call_update", "toolCallId": "r", "kind": "read", "status": "completed"}, kinds, names) is None
    assert usage_from_prompt_response(ns(usage=ns(total_tokens=9))) == (9, 0.0) and usage_from_prompt_response(ns()) == (0, 0.0)
    assert acp_model_family("claude-sonnet-4-5") == "sonnet" and acp_model_family("gpt-4o") is None


def test_a_missing_agent_program_is_a_reported_result_not_a_spawn(monkeypatch):
    monkeypatch.setattr(acp_config.shutil, "which", lambda name: None)
    result = AcpDeepRunner(AcpConfig(working_dir="/w")).run_goal(goal="g", brief="b")
    assert not result.met and "claude-agent-acp" in result.error
