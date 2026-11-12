"""Launching and checking the opencode terminal client (a separate program, MIT-licensed, never bundled, vendored or imported): where it is, whether this version is the tested one, the
per-run folder it is given (its plugin folder, its settings and its own data and state, so a run leaves nothing in the person's own client setup), the settings that turn off its update check and
model fetch, and the command line that points it at the hub's server. Pure functions over a mapping handed in: nothing here reads the process environment. Standard library only."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

CLIENT_ENV = "AHOHS_OPENCODE_CLIENT"
MODE_ENV = "AHOHS_OPENCODE_MODE"
DEFAULT_CLIENT = "opencode"
TESTED_VERSION = "2.2.7"
MODES = ("full", "inline")
INSTALL_HINT = (f"install the opencode V2 terminal client (MIT; npm package @opencode/cli, tested with {TESTED_VERSION}) into a folder of your own, for example "
                f"npm install --prefix ~/tools/opencode @opencode/cli@{TESTED_VERSION}, and name its bin/opencode in {CLIENT_ENV} or the option client")
PLUGIN_DIR = Path(__file__).resolve().parent / "plugin"
PLUGIN_ID = "hub_session"
OFF = {"OPENCODE_DISABLE_AUTOUPDATE": "1", "OPENCODE_DISABLE_MODELS_FETCH": "1", "OPENCODE_DISABLE_CLAUDE_CODE": "1", "OPENCODE_DISABLE_FILEWATCHER": "1"}
VERSION = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def program(client: str, environ: Optional[Mapping[str, str]] = None) -> str:
    """The client program named by the option, else by ``AHOHS_OPENCODE_CLIENT`` in the mapping, else ``opencode``."""
    return (client or (environ or {}).get(CLIENT_ENV, "") or DEFAULT_CLIENT).strip()


def find(client: str, environ: Optional[Mapping[str, str]] = None) -> str:
    """The path of the client program, or an empty string when it is not there."""
    name = program(client, environ)
    if "/" in name:
        return name if Path(name).is_file() else ""
    return shutil.which(name, path=(environ or {}).get("PATH") or None) or ""


def version_of(path: str, environ: Optional[Mapping[str, str]] = None) -> str:
    """The client's version (``2.2.7``) by running ``--version``, or an empty string when it will not say."""
    try:
        run = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=20, env=dict(environ) if environ is not None else None)
    except (OSError, subprocess.SubprocessError):
        return ""
    found = VERSION.search(run.stdout + run.stderr)
    return found.group(0) if found else ""


def version_note(version: str) -> str:
    """One plain clause when the client is not of the tested major version (its API is unversioned and moves), else empty."""
    found = VERSION.fullmatch(version or "")
    if not found:
        return f"the client did not report a version; the tested one is {TESTED_VERSION}"
    if found.group(1) != TESTED_VERSION.split(".")[0]:
        return f"the client is version {version}; this arm was tested with {TESTED_VERSION} and the client's server API is unversioned, so what is drawn may be wrong"
    return ""


def unavailable(client: str = "", environ: Optional[Mapping[str, str]] = None) -> str:
    """Why this arm cannot run here (one plain clause with the install hint), or an empty string."""
    if not find(client, environ):
        return f"the opencode terminal client {program(client, environ)!r} is not installed ({INSTALL_HINT})"
    return ""


def settings(mode: str) -> Dict[str, Any]:
    """The client's own settings for a run: every transcript item drawn on its own (a read is named, never counted), tool detail open, markdown drawn; the sidebar left to its width."""
    if mode == "inline":
        return {"mini": {"tools": "show"}}
    return {"session": {"grouping": "none", "verbosity": "high", "markdown": "rendered", "sidebar": "auto"}}


def prepare_run_folder(mode: str, parent: str = "", plugin: bool = True) -> str:
    """A fresh folder holding the client's configuration for one run: the hub's plugin (unless ``plugin`` is false, to see the client alone), and empty data, state and cache folders. The caller
    removes it (``shutil.rmtree``) when the run ends."""
    run = Path(tempfile.mkdtemp(prefix="ahohs-opencode-", dir=parent or None))
    config = run / "config"
    config.mkdir()
    if plugin:
        shutil.copytree(PLUGIN_DIR / PLUGIN_ID, config / "plugins" / PLUGIN_ID)
    for name in ("data", "state", "cache"):
        (run / name).mkdir()
    (config / "cli.json").write_text(json.dumps(settings(mode)))
    return str(run)


def client_environment(environ: Mapping[str, str], run_folder: str, token: str, mode: str) -> Dict[str, str]:
    """The environment the client is started with: the caller's, plus its folders under the run folder, the per-run password, and the switches that turn off its update check and model fetch."""
    run = Path(run_folder)
    env = dict(environ)
    env.update(OFF)
    env.update({"OPENCODE_CONFIG_DIR": str(run / "config"), "XDG_CONFIG_HOME": str(run / "config"), "XDG_DATA_HOME": str(run / "data"), "XDG_STATE_HOME": str(run / "state"),
                "XDG_CACHE_HOME": str(run / "cache"), "OPENCODE_PASSWORD": token, "OPENCODE_CLI_CONFIG_CONTENT": json.dumps(settings(mode))})
    env.pop("PYTHONPATH", None)
    return env


def client_command(path: str, url: str, session_id: str, mode: str = "full", goal: str = "") -> List[str]:
    """The command that points the client at the server's session: the full-screen interface by default, ``mini`` (inline, into the terminal's own scrollback) for ``inline``."""
    command = [path] + (["mini"] if mode == "inline" else []) + ["--server", url, "--session", session_id]
    return command + (["--prompt", goal] if goal else [])


def mode_of(option: str, environ: Optional[Mapping[str, str]] = None) -> str:
    """``full`` or ``inline``: the option, else ``AHOHS_OPENCODE_MODE``, else full."""
    chosen = (option or (environ or {}).get(MODE_ENV, "") or "full").strip().lower()
    if chosen not in MODES:
        raise ValueError(f"the opencode mode must be one of {', '.join(MODES)}, not {chosen!r}")
    return chosen
