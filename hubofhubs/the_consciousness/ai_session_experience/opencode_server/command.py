"""``ahohs opencode-server``: serve the hub's session harness over the opencode API on the loopback interface, and print how to point the stock client at it. The command line is added to ``ahohs`` by
``add_arguments`` and run by ``serve_command``; both are called from ``hubofhubs/the_self/assembler/cli.py``. A person who runs it by hand starts the client themselves with the printed line."""
from __future__ import annotations

import argparse
import sys
from typing import Any, Callable

from hubofhubs.the_consciousness.ai_session_experience.opencode_server import client as launch


def add_arguments(sub: Any) -> None:
    """Register ``opencode-server`` on the ``ahohs`` sub-parsers."""
    parser = sub.add_parser("opencode-server", help="serve the hub's session harness over the opencode API on the loopback interface, for the stock opencode terminal client to draw (the arm opencode_client_session starts it for you)")
    parser.add_argument("--harness", default="", help="native, adaptive, solution_agents, stream or loop (default: the hub's own pick)")
    parser.add_argument("--tier", default="", help="model tier: fast, balanced, quality or best")
    parser.add_argument("--folder", default=".", help="the folder the session works in")
    parser.add_argument("--max-spend", default=None, metavar="USD", help="spend ceiling in dollars, or unlimited")
    parser.add_argument("--max-time", default=None, metavar="TIME", help="time ceiling like 90s, 30m, 2h, or unlimited")
    parser.add_argument("--permission", default="acceptEdits", choices=("acceptEdits", "skip"), help="acceptEdits: commands are refused and listed; skip: no permission checks")
    parser.add_argument("--solution", default="", help="the solution this work serves")
    parser.add_argument("--milestone", default="", help="the milestone it serves")
    parser.add_argument("--as", dest="person", default="", metavar="NAME", help="who the AI acts for, shown in the client's sidebar")
    parser.add_argument("--setting-sources", default="project", help="which of the Claude CLI's setting sources a session loads")
    parser.add_argument("--host", default="127.0.0.1", help="the address to listen on; only a loopback address is accepted unless --allow-remote is given")
    parser.add_argument("--port", type=int, default=0, help="the port (default: a free one the system picks)")
    parser.add_argument("--allow-remote", action="store_true", help="accept a non-loopback --host (the server is then reachable by other machines; the per-run password is the only protection)")


def build_for(args: argparse.Namespace, environ: Any) -> Callable[[str], Any]:
    """``build(folder)`` for the harness the arguments name (the same builder ``ahohs work`` and ``ahohs acp`` use)."""
    from pathlib import Path
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import work as terminal
    from hubofhubs.the_self.assembler.cli import main_session_tier
    usd = terminal.dollars_of(args.max_spend) if args.max_spend is not None else None
    seconds = terminal.seconds_of(args.max_time) if args.max_time is not None else None
    usd = "unlimited" if usd is None and args.max_spend is not None else usd
    seconds = "unlimited" if seconds is None and args.max_time is not None else seconds
    name = args.harness or terminal.default_harness()[0]
    if name not in terminal.HARNESSES:
        raise ValueError(f"no harness named {name!r}; choose one of {', '.join(terminal.HARNESSES)}")
    return lambda folder: terminal.harness_builder(folder=str(Path(folder).resolve()), tier=main_session_tier("", args.tier), ceiling_usd=usd, ceiling_seconds=seconds, permission=args.permission,
                                                   environ=environ, solution=args.solution, milestone=args.milestone, setting_sources=args.setting_sources)(name)


def serve_command(args: argparse.Namespace) -> int:
    """Start the server and wait for the client to be closed with Ctrl-C. Exit 0 ended, 2 refused (a host that is not loopback, a harness that is not known)."""
    from pathlib import Path
    from hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge import Bridge
    from hubofhubs.the_consciousness.ai_session_experience.opencode_server.server import OpencodeServer
    from hubofhubs.the_self.assembler.resolution import process_environment
    try:
        build = build_for(args, process_environment())
        folder = str(Path(args.folder).resolve())
        server = OpencodeServer(Bridge(build, folder, acting_for=args.person), host=args.host, port=args.port, allow_remote=args.allow_remote)
    except ValueError as error:
        print(f"failed: {error}", file=sys.stderr)
        return 2
    print(f"serving the hub session on {server.url} (loopback only unless --allow-remote)")
    print(f"point the stock client at it:  OPENCODE_PASSWORD={server.token} opencode --server {server.url} --session {server.bridge.root}")
    print(f"(inline interface: add the word mini after opencode; tested client version {launch.TESTED_VERSION})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
    return 0
