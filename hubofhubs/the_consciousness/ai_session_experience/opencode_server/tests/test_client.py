"""Launching and checking the client: the command line for both interfaces, the per-run folder and environment (plugin, settings, own data and state, update check and model fetch off), availability
with the install hint, the version warning, the mode choice, the plugin's source and the slots it records. Nothing here starts the real client or reads the process environment."""
import json
import os
import stat
import sys

import pytest

from hubofhubs.the_consciousness.ai_session_experience.opencode_server import client


def test_the_full_screen_interface_is_the_default_and_inline_is_opencode_mini():
    full = client.client_command("/bin/oc", "http://127.0.0.1:9", "ses_1", "full", "What is today?")
    inline = client.client_command("/bin/oc", "http://127.0.0.1:9", "ses_1", "inline", "")
    assert full == ["/bin/oc", "--server", "http://127.0.0.1:9", "--session", "ses_1", "--prompt", "What is today?"]
    assert inline == ["/bin/oc", "mini", "--server", "http://127.0.0.1:9", "--session", "ses_1"]


def test_the_mode_is_the_option_then_the_given_environment_then_full_and_anything_else_is_refused():
    assert client.mode_of("", {}) == "full" and client.mode_of("", {client.MODE_ENV: "inline"}) == "inline" and client.mode_of("full", {client.MODE_ENV: "inline"}) == "full"
    with pytest.raises(ValueError, match="full, inline"):
        client.mode_of("mini", {})


def test_a_run_folder_holds_the_plugin_and_settings_and_the_clients_data_stays_inside_it(tmp_path):
    folder = client.prepare_run_folder("full", str(tmp_path))
    try:
        run = tmp_path / os.path.basename(folder)
        assert (run / "config" / "plugins" / "hub_session" / "tui.tsx").is_file() and (run / "data").is_dir() and (run / "state").is_dir() and (run / "cache").is_dir()
        assert json.loads((run / "config" / "cli.json").read_text())["session"]["grouping"] == "none"
        env = client.client_environment({"PATH": "/usr/bin", "PYTHONPATH": "/x", "KEEP": "1"}, folder, "tok", "full")
        assert env["OPENCODE_PASSWORD"] == "tok" and env["OPENCODE_CONFIG_DIR"] == str(run / "config") and env["XDG_DATA_HOME"] == str(run / "data") and env["XDG_STATE_HOME"] == str(run / "state")
        assert env["OPENCODE_DISABLE_AUTOUPDATE"] == "1" and env["OPENCODE_DISABLE_MODELS_FETCH"] == "1" and env["KEEP"] == "1" and "PYTHONPATH" not in env
        assert json.loads(env["OPENCODE_CLI_CONFIG_CONTENT"])["session"]["markdown"] == "rendered"
    finally:
        import shutil
        shutil.rmtree(folder)
    assert not os.path.exists(folder)


def test_the_inline_settings_show_tool_calls():
    assert client.settings("inline") == {"mini": {"tools": "show"}} and client.settings("full")["session"]["verbosity"] == "high"


def test_a_missing_client_is_unavailable_with_the_install_hint_and_the_tested_version(tmp_path):
    reason = client.unavailable("", {"PATH": str(tmp_path)})
    assert "'opencode' is not installed" in reason and client.TESTED_VERSION in reason and "npm install" in reason and client.CLIENT_ENV in reason
    assert "'/nope/oc'" in client.unavailable("/nope/oc", {"PATH": str(tmp_path)})


def test_the_client_is_found_by_the_option_then_the_given_environment_then_the_path(tmp_path):
    program = tmp_path / "oc"
    program.write_text("#!/bin/sh\necho 'opencode v2.2.7'\n")
    program.chmod(program.stat().st_mode | stat.S_IEXEC)
    assert client.find(str(program), {}) == str(program) and client.find("", {client.CLIENT_ENV: str(program)}) == str(program)
    assert client.find("oc", {"PATH": str(tmp_path)}) == str(program) and client.find("", {"PATH": str(tmp_path)}) == ""
    assert client.unavailable(str(program), {}) == "" and client.version_of(str(program), {"PATH": "/usr/bin:/bin"}) == "2.2.7"


def test_another_major_version_is_warned_about_and_the_tested_one_is_not():
    assert client.version_note("2.9.1") == "" and client.version_note("2.2.7") == ""
    assert "version 3.0.0" in client.version_note("3.0.0") and "unversioned" in client.version_note("3.0.0")
    assert "did not report a version" in client.version_note("")


def test_the_plugin_is_a_small_readable_source_file_that_records_the_slots_it_uses():
    source = (client.PLUGIN_DIR / client.PLUGIN_ID / "tui.tsx").read_text()
    for slot in ("session.composer.top", "sidebar.content", "session.panel"):
        assert f'append: "{slot}"' in source and slot in source.split("export default")[0]       # each slot is recorded in the header comment
    assert 'slash: { name: "structure" }' in source and len(source.splitlines()) < 120
    assert "quest" not in source.lower()


def test_no_client_function_reads_the_process_environment():
    import ast
    tree = ast.parse(open(client.__file__).read())
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.Attribute) and n.attr in ("environ", "getenv")]
    assert "os" not in {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}


def test_the_server_package_imports_only_the_standard_library_and_the_hub():
    import ast
    from pathlib import Path
    allowed = set(sys.stdlib_module_names) | {"hubofhubs", "esoi"}
    for path in Path(client.__file__).parent.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text())):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) and not node.level else []
            for name in names:
                assert name.split(".")[0] in allowed, (path.name, name)


def test_an_unnamed_client_prefers_the_tested_major_over_an_older_one_on_the_path(tmp_path, monkeypatch):
    """With no client named, the usual places are searched and the tested major version wins, so no setting is needed for the hub's selected terminal to open."""
    old, new = tmp_path / "bin" / "opencode", tmp_path / "tools" / "opencode" / "bin" / "opencode"
    for path, version in ((old, "1.19.5"), (new, "2.2.7")):
        path.parent.mkdir(parents=True)
        path.write_text(f"#!/bin/sh\necho {version}\n")
        path.chmod(0o755)
    environ = {"HOME": str(tmp_path), "PATH": str(old.parent)}
    assert client.find("", environ) == str(new)
    assert client.find("", {"HOME": str(tmp_path), "PATH": str(old.parent), client.CLIENT_ENV: str(old)}) == str(old)
