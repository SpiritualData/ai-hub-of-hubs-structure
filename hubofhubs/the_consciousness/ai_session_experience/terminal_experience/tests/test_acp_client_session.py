"""The ACP client arm: the launch command it builds, availability when the client or the SDK is missing, the fall back to the standard terminal with the reason shown, and a real
launch of a stand-in client program (a script that records how it was started). The real client (Toad) is never imported or bundled; it is only a program."""
import json
import os
import shlex
import stat
import sys
from pathlib import Path

import pytest

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import acp_client_session as arm


def test_the_default_client_is_toad_launched_as_toad_acp_agent_command_then_folder():
    agent = arm.agent_command("/work", {"harness": "stream", "tier": "fast", "person": "Sam", "max_spend": None})
    assert agent[-8:] == ["--folder", "/work", "--harness", "stream", "--tier", "fast", "--as", "Sam"] and agent[:2] in (["ahohs", "acp"], [sys.executable, "-m"])
    command = arm.client_command(agent, "/work")
    assert command[:2] == ["toad", "acp"] and command[3] == "/work" and shlex.split(command[2]) == agent


def test_a_configured_client_may_place_the_agent_and_folder_or_have_them_appended():
    agent = ["ahohs", "acp", "--folder", "/w w"]
    assert arm.client_command(agent, "/w w", "myclient --agent {agent} --dir {folder}") == ["myclient", "--agent", shlex.join(agent), "--dir", "/w w"]
    assert arm.client_command(agent, "/w", "otherclient --flag") == ["otherclient", "--flag", shlex.join(agent), "/w"]
    assert arm.client_command(agent, "/w", "toad")[:2] == ["toad", "acp"]


def test_a_missing_client_is_reported_unavailable_with_the_install_line(tmp_path):
    reason = arm.unavailable("", {"PATH": str(tmp_path)})
    assert "'toad' is not installed" in reason and "uv tool install" in reason
    assert "'nope'" in arm.unavailable("nope --x", {"PATH": str(tmp_path)})


def test_the_availability_mechanism_reports_the_arm_unmet_and_names_the_client_and_the_sdk(tmp_path):
    from hubofhubs.the_self.assembler import availability
    from hubofhubs.the_self.assembler.resolution import HUB
    why = availability.unmet(HUB, "terminal-session", "acp_client_session", {"PATH": str(tmp_path)}, {})
    assert "toad" in why.lower()


class FakeTerminal:
    name = "stream"

    def __init__(self):
        self.said, self.arm, self.ran = [], None, []

    def say(self, text):
        self.said.append(text)

    def run(self, goal, resume):
        self.ran.append((goal, resume))
        return 0


def test_without_the_client_the_terminal_says_why_and_the_standard_terminal_runs(tmp_path):
    terminal = FakeTerminal()
    code = arm.AcpClientSession().host_terminal(terminal, "do it", "sess-1", environ={"PATH": str(tmp_path)})
    assert code == 0 and terminal.ran == [("do it", "sess-1")]
    assert "not installed" in terminal.said[0] and "standard terminal" in terminal.said[0]
    assert type(terminal.arm).__name__ == "LiveSession"


def test_with_a_client_on_the_path_it_is_started_as_its_own_program_pointed_at_the_agent(tmp_path):
    pytest.importorskip("acp")
    record = tmp_path / "argv.json"
    client = tmp_path / "fakeclient"
    client.write_text(f"#!{sys.executable}\nimport json, sys\nopen({str(record)!r}, 'w').write(json.dumps(sys.argv[1:]))\n")
    client.chmod(client.stat().st_mode | stat.S_IEXEC)
    session = arm.AcpClientSession(client=str(client))
    session.configure(folder=str(tmp_path), harness="loop", tier="fast")
    code = session.host_terminal(FakeTerminal(), environ={"PATH": "/usr/bin:/bin"})
    argv = json.loads(record.read_text())
    assert code == 0 and argv[-1] == str(tmp_path)
    started = shlex.split(argv[-2])
    assert "acp" in started and started[started.index("--harness") + 1] == "loop" and started[started.index("--tier") + 1] == "fast"


def test_the_arm_is_declared_with_its_requirements_and_never_imports_the_client():
    assert [r.name if hasattr(r, "name") else r.module for r in arm.AcpClientSession.REQUIRES] == ["acp", "toad"]
    source = Path(arm.__file__).read_text()
    assert "import toad" not in source and "from toad" not in source
    assert arm.AcpClientSession.presentation == "external"
