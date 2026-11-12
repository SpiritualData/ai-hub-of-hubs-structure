"""The opencode client arm of Terminal Experience: the stock opencode terminal client (V2, MIT) draws the hub through the HTTP API it already speaks.

The arm draws nothing itself. ``host_terminal`` starts the hub's own server (``opencode_server``: the subset of opencode's API the client needs, over the hub's session ``Harness``, on the loopback
interface with a per-run password), launches the installed client as a SEPARATE PROGRAM pointed at it, with a per-run folder holding the hub's client plugin and the client's own settings (its update
check and model fetch turned off), waits for it to exit, and removes the folder. The client is never bundled, vendored or imported; the person installs it. Two interfaces: the full-screen one (default)
and ``inline`` (``opencode mini``: it streams into the terminal's own scrollback), chosen by the option ``mode`` (``ahohs work --opencode-mode inline``) or ``AHOHS_OPENCODE_MODE``.

When the client is missing, availability reports the arm unavailable with the install hint and the best-measured arm stands in. The client's API is unversioned and marked experimental: the tested
client version is named in the message and another major version is warned about. What the client cannot show (no key for a structure tree without the plugin, no mini plugin slots, no stopping one
helper) is the arm's protocol ceiling, named in its record. Outside a terminal it falls back to the standard-library arm's plain lines.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, TextIO

from esoi import implementation

from hubofhubs.the_consciousness.ai_session_experience.opencode_server import client as launch
from hubofhubs.the_consciousness.ai_session_experience.session_events import Harness
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionReport
from hubofhubs.the_self.assembler import arm_needs as needs


@implementation("terminal-session", "opencode_client_session")
class OpencodeClientSession:
    """The stock opencode terminal client drawing the hub through ``opencode_server``; the screen, its keys and its look are the client's, with the hub's plugin in its own slots."""
    REQUIRES = (needs.OPENCODE_BINARY,)
    presentation = "external"                  # the presentation metric does not capture it in process: the client draws it in its own program
    external_scenarios = "opencode_external"   # the module of the metric that runs the real client on a pseudo-terminal (evaluation/terminal_presentation)
    # The words and the marker the client's own screen uses (full-screen interface), declared so the presentation metric judges the fact (a choice to allow and one to refuse, a hint for stopping,
    # the person's message set apart) and not the hub's wording. The metric requires each on the screen at the right moment; the control round trips prove each does what it says.
    screen_labels = {"allow": "Allow once", "refuse": "Reject", "stop": "esc interrupt", "person": "┃"}

    def __init__(self, client: str = "") -> None:
        self.client = client
        self.options: Dict[str, Any] = {}

    def configure(self, **options: Any) -> None:
        """What the server is started with (the harness, the folder, the tier, the ceilings, who the AI acts for) and the interface (``mode``), handed in by the command."""
        self.options.update(options)

    # --- the arm's surface: only a terminal is the client's; the rest is the standard-library arm's ---------------------------------

    def structure_lines(self, view: Any, width: int = 100) -> List[str]:
        return LiveSession().structure_lines(view, width)

    def converse(self, front_door: Optional[Callable[[str], Any]] = None, lines: Iterable[str] = (), out: Optional[TextIO] = None, viewer_id: str = "", prompt: str = "> ") -> int:
        return LiveSession().converse(front_door, lines, out, viewer_id, prompt)

    def attend(self, harness: Harness, goal: str, out: TextIO, keys: Any = None, resume_session_id: str = "", **options: Any) -> SessionReport:
        """Outside a client's own screen the run is drawn by the standard-library arm (a client cannot be driven from inside a process)."""
        return LiveSession().attend(harness, goal, out, keys, resume_session_id, **options)

    def work(self, build: Callable[[str], Harness], out: TextIO, goal: str = "", resume: str = "", lines: Optional[Iterable[str]] = None, **options: Any) -> Any:
        return LiveSession().work(build, out, goal, resume, lines, **options)

    def host_terminal(self, terminal: Any, goal: str = "", resume: str = "", environ: Optional[Mapping[str, str]] = None) -> int:
        """Serve the session, launch the client on this terminal pointed at it, and return its exit code. If the client is missing, say why and run in the standard-library terminal."""
        from hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge import Bridge
        from hubofhubs.the_consciousness.ai_session_experience.opencode_server.server import OpencodeServer
        from hubofhubs.the_self.assembler.resolution import process_environment
        env = dict(environ if environ is not None else process_environment())
        reason = launch.unavailable(self.client, env)
        folder = str(self.options.get("folder") or ".")
        if reason:
            terminal.say(f"{reason}; using the standard terminal instead")
            terminal.arm = LiveSession()
            return terminal.run(goal, resume)
        path = launch.find(self.client, env)
        note = launch.version_note(launch.version_of(path, env))
        if note:
            terminal.say("note: " + note)
        mode = launch.mode_of(str(self.options.get("mode") or ""), env)
        from hubofhubs.the_consciousness.ai_session_experience.opencode_server import command as serving
        chosen = serving.default_tier(self.options)
        build_tier = serving.tier_builder(self.options, env, getattr(terminal, "stop_inputs", None))

        def build(where: str, tier: str = "") -> Harness:
            # the tier in use when the person has not picked another is the terminal's own harness (its records and stop inputs); a tier they pick in the client's model picker builds that tier's
            return terminal.harness() if not tier or tier == chosen else build_tier(where, tier)

        bridge = Bridge(build, folder, acting_for=str(self.options.get("person") or ""), command=getattr(terminal, "command", "ahohs work"), folder_name=mode == "full",
                        tiers=serving.offered_choices(), tier=chosen)
        bridge.resume_id = resume
        run = launch.prepare_run_folder(mode)
        server = OpencodeServer(bridge).start()
        try:
            command = launch.client_command(path, server.url, bridge.root, mode, goal)
            code = subprocess.run(command, cwd=folder, env=launch.client_environment(env, run, server.token, mode), check=False).returncode
        finally:
            server.stop()
            shutil.rmtree(run, ignore_errors=True)
        view = bridge.translator.view
        if mode == "full" and view.final is not None:       # a full-screen client leaves nothing in the scrollback, so the closing line and the resume command are said once it is gone
            color = bool(getattr(terminal, "interactive", lambda: False)()) and not os.environ.get("NO_COLOR")   # coloured like the native screen, on a real terminal only
            for row in present.outcome_rows(view, color=color) + present.resume_lines(view):
                terminal.say(row)
        return code
