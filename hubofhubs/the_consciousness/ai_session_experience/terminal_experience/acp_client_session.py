"""The ACP client arm of Terminal Experience: an existing open-source agent terminal draws the hub through the Agent Client Protocol.

The arm draws nothing itself. ``host_terminal`` launches an installed ACP terminal client (by default Toad, https://github.com/batrachianai/toad) as a SEPARATE PROGRAM
pointed at ``ahohs acp`` (``acp_agent``), which serves the hub's session ``Harness`` over the protocol. Toad is AGPL-3.0: it is only ever started as its own process, never
imported, vendored or made a dependency of this package, so its licence does not reach the hub's Apache-2.0 code. The client command is configurable by the option ``client`` or
the environment variable ``AHOHS_ACP_CLIENT`` (a command line in which ``{agent}`` and ``{folder}`` stand for the agent command and the folder; without them the agent command and the
folder are appended, the form ``toad acp COMMAND PATH``). The protocol layer is the official Python SDK, an optional extra (``acp``).

When the client or the SDK is missing, availability (``REQUIRES``) reports the arm unavailable and the best-measured arm stands in, with the reason shown. The surface does what the
protocol carries: tool calls, plans, messages, permission requests, cancel, and the hub's steering extension; what it cannot carry (a structure tree on request, a live spend gauge,
stopping one helper) is the protocol ceiling, named in the arm's record. Run outside a terminal it falls back to the standard-library arm's plain lines.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
import sys
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, TextIO

from esoi import implementation

from hubofhubs.the_consciousness.ai_session_experience.session_events import Harness
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import SessionReport
from hubofhubs.the_self.assembler import arm_needs as needs

CLIENT_ENV = "AHOHS_ACP_CLIENT"
DEFAULT_CLIENT = "toad"
AGENT_OPTIONS = (("harness", "--harness"), ("tier", "--tier"), ("max_spend", "--max-spend"), ("max_time", "--max-time"), ("permission", "--permission"), ("solution", "--solution"),
                 ("milestone", "--milestone"), ("person", "--as"), ("setting_sources", "--setting-sources"))


def agent_command(folder: str, options: Mapping[str, Any], path: str = "") -> List[str]:
    """The command a client runs to start the hub's ACP agent: ``ahohs acp`` when ``ahohs`` is on the path, else this interpreter running the same entry (so the extras that are
    installed here are the ones the agent sees)."""
    base = ["ahohs", "acp"] if shutil.which("ahohs", path=path or None) else [sys.executable, "-m", "hubofhubs.the_self.assembler.cli", "acp"]
    args = ["--folder", folder]
    for key, flag in AGENT_OPTIONS:
        value = options.get(key)
        if value not in (None, ""):
            args += [flag, str(value)]
    return base + args


def client_command(agent: Sequence[str], folder: str, client: str = "") -> List[str]:
    """The argument list that launches the client: ``toad acp "<agent command>" <folder>`` by default; a configured client may place ``{agent}`` and ``{folder}`` itself."""
    text = shlex.join(agent)
    if not client or client.strip() == DEFAULT_CLIENT:
        return [DEFAULT_CLIENT, "acp", text, folder]
    words = shlex.split(client)
    if any("{agent}" in w or "{folder}" in w for w in words):
        return [w.replace("{agent}", text).replace("{folder}", folder) for w in words]
    return words + [text, folder]


def unavailable(client: str = "", environ: Optional[Mapping[str, str]] = None) -> str:
    """Why this arm cannot run here (one plain clause), or an empty string. ``environ`` is a mapping handed in; nothing reads the process environment here."""
    path = (environ or {}).get("PATH", "")
    program = shlex.split(client)[0] if client.strip() else DEFAULT_CLIENT
    if not shutil.which(program, path=path or None):
        return f"the ACP terminal client {program!r} is not installed (Toad: uv tool install -U batrachian-toad --python 3.14)"
    try:
        import acp  # noqa: F401
    except ImportError:
        return "the Agent Client Protocol SDK is not installed (pip install 'hubofhubs[acp]')"
    return ""


@implementation("terminal-session", "acp_client_session")
class AcpClientSession:
    """An existing agent terminal (an ACP client run as its own program) drawing the hub through ``ahohs acp``; the screen, its keys and its look are the client's."""
    REQUIRES = (needs.ACP_SDK, needs.TOAD_BINARY)
    presentation = "external"        # the presentation metric does not capture it in process: the client draws it in its own program

    def __init__(self, client: str = "") -> None:
        self.client = client
        self.options: Dict[str, Any] = {}

    def configure(self, **options: Any) -> None:
        """What the agent is started with (the harness, the folder, the tier, the ceilings, who it acts for), handed in by the command."""
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
        """Launch the client on this terminal, pointed at the agent, and return its exit code. If the client or the SDK is missing, say why and run in the standard-library terminal."""
        from hubofhubs.the_self.assembler.resolution import process_environment
        env = dict(environ if environ is not None else process_environment())
        client = self.client or env.get(CLIENT_ENV, "")
        reason = unavailable(client, env)
        folder = str(self.options.get("folder") or ".")
        if reason:
            terminal.say(f"{reason}; using the standard terminal instead")
            terminal.arm = LiveSession()
            return terminal.run(goal, resume)
        options = {**self.options, "harness": self.options.get("harness") or terminal.name}
        command = client_command(agent_command(folder, options, env.get("PATH", "")), folder, client)
        return subprocess.run(command, cwd=folder, env=env, check=False).returncode
