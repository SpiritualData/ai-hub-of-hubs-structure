"""The library entry point for a program that wants the stock opencode terminal client as its own terminal: ``host_in_opencode`` serves a session over the loopback interface, launches the installed client on this
terminal pointed at it, waits for the client to exit and says the closing line once the full-screen client is gone. What is the program's own comes in through the arguments, never through a copy of
this wiring: ``build(folder, tier)`` gives the ``Harness`` that does one run (or ``build(folder)`` with no tiers), ``commands`` are its slash commands, ``header`` its short lines beside who the work serves,
``person`` who the AI acts for and ``command`` how its own command line starts (for the resume command). ``opencode_available`` says why the client cannot run here. Standard library only."""
from __future__ import annotations

import shutil
import subprocess
from typing import Any, Callable, List, Mapping, Optional, Sequence, Tuple

from hubofhubs.the_consciousness.ai_session_experience.opencode_server import client as launch
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge import Bridge, SlashCommand
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.server import OpencodeServer
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present


def opencode_available(client: str = "", environ: Optional[Mapping[str, str]] = None) -> str:
    """Why the client cannot run here (one plain clause with the install hint), or an empty string when it can. A client of another major version than the tested one counts as not available here: a program
    that chooses its screen by this answer must not hand the person a client that cannot read the hub's server (the hub's own arm only warns)."""
    reason = launch.unavailable(client, environ)
    if reason:
        return reason
    note = launch.version_note(launch.version_of(launch.find(client, environ), environ))
    return f"{note}; {launch.INSTALL_HINT}" if note else ""


def host_in_opencode(build: Callable[..., Any], folder: str, *, client: str = "", mode: str = "", environ: Optional[Mapping[str, str]] = None, person: str = "", command: str = "ahohs work",
         goal: str = "", resume: str = "", tiers: Tuple[str, ...] = (), tier: str = "", commands: Sequence[SlashCommand] = (), header: Optional[Callable[[], Sequence[str]]] = None,
         say: Callable[[str], None] = print, color: bool = False, on_bridge: Optional[Callable[[Bridge], None]] = None) -> int:
    """Serve the session and run the client on this terminal until it exits; returns the client's exit code. ``say`` takes the notes and the closing rows (``color`` colours the closing line).
    ``on_bridge`` gets the ``Bridge`` before the client starts (a program that needs to read the run's view or push header changes keeps it). Raises ``RuntimeError`` with the reason when the client is
    not installed: a caller checks ``opencode_available`` first and uses its own terminal instead."""
    from hubofhubs.the_self.assembler.resolution import process_environment
    env = dict(environ if environ is not None else process_environment())
    reason = launch.unavailable(client, env)
    if reason:
        raise RuntimeError(reason)
    path = launch.find(client, env)
    note = launch.version_note(launch.version_of(path, env))
    if note:
        say("note: " + note)
    chosen_mode = launch.mode_of(mode, env)
    bridge = Bridge(build, folder, acting_for=person, command=command, folder_name=chosen_mode == "full", tiers=tuple(tiers), tier=tier, commands=commands, header=header)
    bridge.resume_id = resume
    if on_bridge is not None:
        on_bridge(bridge)
    run = launch.prepare_run_folder(chosen_mode)
    server = OpencodeServer(bridge).start()
    try:
        invocation = launch.client_command(path, server.url, bridge.root, chosen_mode, goal)
        code = subprocess.run(invocation, cwd=folder, env=launch.client_environment(env, run, server.token, chosen_mode), check=False).returncode
    finally:
        server.stop()
        shutil.rmtree(run, ignore_errors=True)
    view = bridge.translator.view
    if chosen_mode == "full" and view.final is not None:       # a full-screen client leaves nothing in the scrollback, so the closing line and the resume command are said once it is gone
        for row in present.outcome_rows(view, color=color and not env.get("NO_COLOR")) + present.resume_lines(view):
            say(row)
    return code


__all__ = ["opencode_available", "host_in_opencode", "SlashCommand"]
