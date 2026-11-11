"""``ahohs``: the hub's command line. Bare ``ahohs`` opens the interactive prompt of ``ahohs work`` (in a terminal; piped, it prints the short help). ``ahohs work "<goal>"`` runs a goal on a real harness in
the live terminal of ``the_consciousness/ai_session_experience/terminal_experience/work.py``. ``ahohs chat`` is the line REPL of ``the_consciousness/ai_session_experience/terminal_experience/repl.py`` over the same call. ``ahohs run "<input>"`` is a thin wrapper over ``hubofhubs.run``: it runs the whole hub on the
input, or the solution named with ``--id``, and prints the answer with its sources (``--json`` prints one JSON object). Exit code 0
ran, 2 needs setup (the lines say what to set), 1 the run failed. Standard library only."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from esoi import EntryError, Pending

from hubofhubs.the_self.assembler.oneline import Result


def work_command(args: argparse.Namespace, hub: object) -> int:
    """``ahohs work``: the arguments checked and turned into one ``WorkTerminal`` (the terminal itself knows no harness, folder or environment)."""
    from pathlib import Path
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import work as terminal
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import TtyKeys
    from hubofhubs.the_self.assembler.resolution import process_environment
    folder = str(Path(args.folder).resolve())
    if not Path(folder).is_dir():
        print(f"failed: {args.folder} is not a folder", file=sys.stderr)
        return 1
    try:
        usd = terminal.dollars_of(args.max_spend) if args.max_spend is not None else None
        seconds = terminal.seconds_of(args.max_time) if args.max_time is not None else None
        usd = "unlimited" if usd is None and args.max_spend is not None else usd
        seconds = "unlimited" if seconds is None and args.max_time is not None else seconds
        name, why = (args.harness, "chosen by you") if args.harness else terminal.default_harness()
        if name not in terminal.HARNESSES:
            raise ValueError(f"no harness named {name!r}; choose one of {', '.join(terminal.HARNESSES)}")
        holder: dict = {}
        build = terminal.harness_builder(folder=folder, tier=args.tier, ceiling_usd=usd, ceiling_seconds=seconds, permission=args.permission, environ=process_environment(),
                                         solution=args.solution, milestone=args.milestone, stop_inputs=lambda: holder["terminal"].stop_inputs(),
                                         setting_sources=args.setting_sources)
    except ValueError as error:
        print(f"failed: {error}", file=sys.stderr)
        return 2
    interactive = sys.stdin.isatty() and sys.stdout.isatty() and not args.plain
    try:
        arm, arm_name, arm_why = terminal.terminal_arm("" if args.plain and not args.terminal else args.terminal, process_environment())
    except Exception as error:  # noqa: BLE001 -- an arm the person named that cannot run is said, not a traceback
        print(f"failed: the terminal {args.terminal!r} cannot be used: {error}", file=sys.stderr)
        return 2
    if args.plain and not args.terminal:
        arm, arm_name = terminal.LiveSession(), "live_session"
    records = args.records or (folder if (Path(folder) / "esoi.toml").is_file() else None)
    session = terminal.WorkTerminal(build, sys.stdout, harness=name, why=why, keys=TtyKeys() if interactive else None, records=records,
                                    live=None if interactive else False, represent=lambda person: hub.run("the-representatives", person), person=args.person,
                                    front_door=lambda text: hub.run("hub-of-hubs", text), once=bool(args.goal) and not interactive, arm=arm)
    from hubofhubs.the_intelligence.nervous_system.structure_watch.session import work_hook
    from hubofhubs.the_body.internal_context.run_store.runs import RunStore
    from hubofhubs.the_body.internal_context.run_store.jsonl_ledger import private_directory
    from hubofhubs.the_consciousness.judgment_calls.judgment import SeverityPolicy
    session.structure_watch = work_hook(records, RunStore(private_directory("hubofhubs-structure-watch") or ""), judge=SeverityPolicy().decide,
                                         ask=lambda prompt, tier, cap: hub.run("model-plumbing", {"prompt": prompt, "tier": tier}), off=args.structure_watch == "off",
                                         ceilings={"ceiling_usd": usd if isinstance(usd, (int, float)) else None, "ceiling_seconds": seconds if isinstance(seconds, (int, float)) else None})
    holder["terminal"] = session
    if not args.goal and not interactive:
        print("ahohs work needs a goal when it is not on a terminal: ahohs work \"<goal>\"", file=sys.stderr)
        return 2
    code = arm.host_terminal(session, args.goal, args.resume) if interactive and hasattr(arm, "host_terminal") else session.run(args.goal, args.resume)
    last = session.last.final if session.last else None
    return code if last is None or last.outcome in ("met", "stopped", "unmet") else 1


def main_session_tier() -> str:
    """The default tier of the main session, read from the role tier table (balanced)."""
    from hubofhubs.the_world.model_plumbing.model_tier_chooser.role_tiers import tier_for
    return tier_for("main_session")


def main(argv: Optional[List[str]] = None) -> int:
    import hubofhubs
    parser = argparse.ArgumentParser(prog="ahohs", description="Run the hub from one line.")
    sub = parser.add_subparsers(dest="command", required=False)
    work = sub.add_parser("work", help="run a goal on a real harness in the live terminal; with no goal, a prompt (also what bare ahohs opens)")
    work.add_argument("goal", nargs="?", default="", help="what to get done in this folder; leave out for a prompt, and type follow-ups that continue the session")
    work.add_argument("--harness", default="", help="native, adaptive, solution_agents, stream or loop (default: the hub's own pick for a person at a terminal)")
    work.add_argument("--tier", default=main_session_tier(), help="model tier: fast, balanced, quality or best (strong reads as quality); default: the tier policy of the main session")
    work.add_argument("--folder", default=".", help="the folder the work happens in (default: this one)")
    work.add_argument("--resume", default="", metavar="SESSION", help="continue a session an earlier run named (with the same --harness, in the same folder)")
    work.add_argument("--max-spend", default=None, metavar="USD", help="spend ceiling in dollars, or unlimited (default: the hub's high default)")
    work.add_argument("--max-time", default=None, metavar="TIME", help="time ceiling like 90s, 30m, 2h, or unlimited (default: the hub's high default)")
    work.add_argument("--permission", default="acceptEdits", choices=("acceptEdits", "skip"), help="acceptEdits: files may be read and changed, commands are refused and listed; skip: no permission checks")
    work.add_argument("--solution", default="", help="the solution this work serves (shown in the header; helpers are placed under it)")
    work.add_argument("--milestone", default="", help="the milestone it serves")
    work.add_argument("--records", default="", help="the ESOI records the structure view reads (default: this folder when it has esoi.toml)")
    work.add_argument("--as", dest="person", default="", metavar="NAME", help="act for this representative (its authority and stop limits apply; /as switches)")
    work.add_argument("--terminal", default="", help="the screen: textual_session, live_session or line_repl (default: the hub's selected one; live_session stands in when Textual is not installed)")
    work.add_argument("--setting-sources", default="project", help="which of the Claude CLI's setting sources a session loads: project (default: this folder's own, never your user-level settings and hooks), or a list such as user,project")
    work.add_argument("--structure-watch", default="on", choices=("on", "off"), help="on (default): one small best-tier look at the records after a run that changed something, when there are records; off: never")
    work.add_argument("--plain", action="store_true", help="plain lines even on a terminal")
    one = sub.add_parser("run", help="answer one input with the best-measured arm of the whole hub, or of one id")
    one.add_argument("input")
    one.add_argument("--id", default="hub-of-hubs", help="the solution or intent to run (default: the whole hub)")
    one.add_argument("--arm", action="append", default=[], metavar="ID=ARM", help="override one solution's arm")
    one.add_argument("--lock", default=None, help="an esoi.lock.json to keep the locked arms")
    one.add_argument("--json", action="store_true", help="print the result as one JSON object")
    talk = sub.add_parser("chat", help="talk to the whole hub line by line (/help inside lists the commands)")
    talk.add_argument("--arm", action="append", default=[], metavar="ID=ARM", help="override one solution's arm")
    talk.add_argument("--lock", default=None, help="an esoi.lock.json to keep the locked arms")
    args = parser.parse_args(argv)
    if args.command is None:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            parser.print_help()
            return 0
        args = parser.parse_args(["work"])
    if args.command == "work":
        return work_command(args, hubofhubs)
    if args.command == "chat":
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.repl import LineRepl
        chosen = dict(item.split("=", 1) for item in args.arm)
        return LineRepl().converse(lambda text: hubofhubs.run("hub-of-hubs", text, arms=chosen or None, lock=args.lock), sys.stdin, sys.stdout)
    arms = dict(item.split("=", 1) for item in args.arm)
    try:
        result = hubofhubs.run(args.id, args.input, arms=arms or None, lock=args.lock)
    except Pending as error:
        print(error, file=sys.stderr)
        return 2
    except EntryError as error:
        print(f"failed: {error}", file=sys.stderr)
        return 1
    if isinstance(result, Result):
        if args.json:
            print(json.dumps({"type": "run", **result.to_dict()}))
            return 0
        print(result.answer)
        if result.note:
            print(f"({result.note})", file=sys.stderr)
        for item in result.items:
            link = item.get('url') or item.get('doi') or ''
            if link and link in (result.answer or ""):       # the answer already lists this source
                continue
            print(f"- {item.get('title') or item.get('id', '')} {link}".rstrip())
        if result.arms:                                      # which arms were named for this run; nothing to say when none were
            print("[" + ", ".join(f"{s}={a}" for s, a in result.arms.items()) + "]", file=sys.stderr)
    else:
        print(json.dumps(result, default=repr) if args.json else repr(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
