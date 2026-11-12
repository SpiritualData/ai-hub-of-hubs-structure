"""The opencode client arm: availability and the fall back to the standard terminal when the client is missing, the real launch of a stand-in client program (a script that records how it was
started and what the server answers it), the choice of interface, the lazy import boundary and the declared requirement. The real client is never imported or bundled; it is only a program."""
import json
import stat
import subprocess
import sys
from pathlib import Path

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import opencode_client_session as arm


class FakeTerminal:
    name = "stream"
    command = "ahohs work"

    def __init__(self):
        self.said, self.arm, self.ran = [], None, []

    def say(self, text):
        self.said.append(text)

    def run(self, goal, resume):
        self.ran.append((goal, resume))
        return 0

    def harness(self):
        raise AssertionError("the stand-in client never starts a run")


def stand_in(tmp_path, version="2.2.7"):
    record = tmp_path / "launch.json"
    program = tmp_path / "opencode"
    program.write_text(f"""#!{sys.executable}
import base64, json, sys, os, urllib.request
if sys.argv[1:] == ["--version"]:
    print("opencode v{version}")
    raise SystemExit(0)
url = sys.argv[sys.argv.index("--server") + 1]
request = urllib.request.Request(url + "/api/info", headers={{"authorization": "Basic " + base64.b64encode(("opencode:" + os.environ["OPENCODE_PASSWORD"]).encode()).decode()}})
info = json.load(urllib.request.urlopen(request))
open({str(record)!r}, "w").write(json.dumps({{"argv": sys.argv[1:], "info": info, "config": os.environ["OPENCODE_CONFIG_DIR"], "plugin": os.path.exists(os.environ["OPENCODE_CONFIG_DIR"] + "/plugins/hub_session/tui.tsx"),
                                              "autoupdate": os.environ["OPENCODE_DISABLE_AUTOUPDATE"], "models": os.environ["OPENCODE_DISABLE_MODELS_FETCH"]}}))
""")
    program.chmod(program.stat().st_mode | stat.S_IEXEC)
    return program, record


def test_without_the_client_the_terminal_says_why_and_the_standard_terminal_runs(tmp_path):
    terminal = FakeTerminal()
    code = arm.OpencodeClientSession().host_terminal(terminal, "do it", "sess-1", environ={"PATH": str(tmp_path)})
    assert code == 0 and terminal.ran == [("do it", "sess-1")]
    assert "not installed" in terminal.said[0] and "npm install" in terminal.said[0] and "standard terminal" in terminal.said[0]
    assert type(terminal.arm).__name__ == "LiveSession"


def test_the_availability_mechanism_reports_the_arm_unmet_and_names_the_client(tmp_path):
    from hubofhubs.the_self.assembler import availability
    from hubofhubs.the_self.assembler.resolution import HUB
    why = availability.unmet(HUB, "terminal-session", "opencode_client_session", {"PATH": str(tmp_path)}, {})
    assert "opencode" in why.lower()


def test_with_a_client_it_is_started_as_its_own_program_pointed_at_the_servers_session_with_the_run_folder(tmp_path):
    program, record = stand_in(tmp_path)
    session = arm.OpencodeClientSession(client=str(program))
    session.configure(folder=str(tmp_path), mode="inline")
    terminal = FakeTerminal()
    code = session.host_terminal(terminal, "What is today?", environ={"PATH": "/usr/bin:/bin"})
    seen = json.loads(record.read_text())
    assert code == 0 and seen["argv"][0] == "mini" and seen["argv"][-2:] == ["--prompt", "What is today?"] and "--session" in seen["argv"]
    assert seen["argv"][seen["argv"].index("--server") + 1].startswith("http://127.0.0.1:") and seen["info"]["version"] == "2.2.7"
    assert seen["plugin"] is True and seen["autoupdate"] == "1" and seen["models"] == "1" and not Path(seen["config"]).exists()       # the run folder is removed
    assert terminal.said == []                                       # no version note for the tested version; nothing to add after an inline run


def test_the_full_screen_interface_is_the_default_and_a_note_is_said_for_another_major_version(tmp_path):
    program, record = stand_in(tmp_path, version="3.1.0")
    session = arm.OpencodeClientSession(client=str(program))
    session.configure(folder=str(tmp_path))
    terminal = FakeTerminal()
    assert session.host_terminal(terminal, "go", environ={"PATH": "/usr/bin:/bin"}) == 0
    assert json.loads(record.read_text())["argv"][0] == "--server"
    assert terminal.said and "version 3.1.0" in terminal.said[0] and "2.2.7" in terminal.said[0]


def test_the_arm_is_declared_with_its_requirement_and_is_an_external_presentation():
    assert [r.name if hasattr(r, "name") else r.module for r in arm.OpencodeClientSession.REQUIRES] == ["opencode"]
    assert arm.OpencodeClientSession.presentation == "external" and arm.OpencodeClientSession.external_scenarios == "opencode_external"


def test_importing_the_arm_does_not_load_the_server_the_client_or_a_socket_library():
    code = ("import sys\nimport hubofhubs.the_consciousness.ai_session_experience.terminal_experience.opencode_client_session\n"
            "bad=[m for m in ('http.server','hubofhubs.the_consciousness.ai_session_experience.opencode_server.server','hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge') if m in sys.modules]\n"
            "print(bad)\n")
    run = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[5]))
    assert run.stdout.strip() == "[]", run.stdout + run.stderr


def test_the_presentation_metric_marks_every_check_not_run_when_the_client_is_absent(monkeypatch, tmp_path):
    root = Path(__file__).resolve().parents[5]
    monkeypatch.syspath_prepend(str(root / "evaluation" / "terminal_presentation"))
    monkeypatch.syspath_prepend(str(root / "evaluation"))
    monkeypatch.setenv("PATH", str(tmp_path))
    monkeypatch.delenv("AHOHS_OPENCODE_CLIENT", raising=False)
    import opencode_external
    done = opencode_external.run_scenario("watch")
    import checks
    assert done["checks"] == {} and set(done["not_run"]) == set(checks.REQUIREMENTS) and "not installed" in done["note"]


def test_the_command_adds_the_opencode_server_and_refuses_a_public_host(capsys):
    from hubofhubs.the_self.assembler import cli
    code = cli.main(["opencode-server", "--host", "0.0.0.0", "--harness", "native"])
    assert code == 2 and "loopback" in capsys.readouterr().err
