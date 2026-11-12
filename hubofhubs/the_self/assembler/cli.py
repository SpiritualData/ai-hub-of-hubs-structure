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


def work_command(args: argparse.Namespace, hub: object, context_provider=None) -> int:
    """``ahohs work``: the arguments checked and turned into one ``WorkTerminal`` (the terminal itself knows no harness, folder or environment). ``context_provider(focus)`` is a
    consumer's own source of saved notes (see ``the_intelligence/subconscious/focus_context/settings.py``)."""
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
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_memory import SessionMemory, resolve_resume
        memory = SessionMemory(folder)
        args.resume, remembered, said, missing = resolve_resume(memory, args.resume, args.harness)       # the harness that ran a session is recorded with it
        if missing:
            raise ValueError(missing)
        if said:
            print(said, file=sys.stderr)
        name, why = (args.harness, "chosen by you") if args.harness else ((remembered, "the one that ran that session") if remembered else terminal.default_harness())
        if name not in terminal.HARNESSES:
            raise ValueError(f"no harness named {name!r}; choose one of {', '.join(terminal.HARNESSES)}")
        holder: dict = {}
        build = terminal.harness_builder(folder=folder, tier=main_session_tier(getattr(args, "task_kind", ""), args.tier), ceiling_usd=usd, ceiling_seconds=seconds, permission=args.permission, environ=process_environment(),
                                         solution=args.solution, milestone=args.milestone, stop_inputs=lambda: holder["terminal"].stop_inputs(),
                                         setting_sources=args.setting_sources)
        from hubofhubs.the_intelligence.subconscious.focus_context.grounded import grounded_builder
        from hubofhubs.the_intelligence.subconscious.focus_context.settings import configured, replace_focus
        settings = replace_focus(configured(getattr(args, "context", ""), process_environment()), getattr(args, "focus", ""))
        build = grounded_builder(build, settings, context_provider, process_environment())       # the person's own context (None without a settings file or provider)
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
    if hasattr(arm, "configure"):       # an arm that starts a program of its own (the ACP client arm) is told what the agent it points at is started with
        arm.configure(harness=name, folder=folder, tier=args.tier, max_spend=args.max_spend, max_time=args.max_time, permission=args.permission, solution=args.solution,
                      milestone=args.milestone, person=args.person, setting_sources=args.setting_sources, environ=process_environment(), mode=getattr(args, "opencode_mode", ""))
    code = arm.host_terminal(session, args.goal, args.resume) if interactive and hasattr(arm, "host_terminal") else session.run(args.goal, args.resume)
    for ended in session.reports:        # what ran each session is kept with its id, so `--resume <id>` needs no `--harness`
        if ended.final is not None and ended.final.session_id:
            memory.record(ended.final.session_id, ended.view.harness or session.name, args.tier)
    last = session.last.final if session.last else None
    return code if last is None or last.outcome in ("met", "stopped", "unmet") else 1


def acp_command(args: argparse.Namespace) -> int:
    """``ahohs acp``: the hub's session harness served as an Agent Client Protocol agent on stdin and stdout, for an ACP terminal client to draw. A client launches it: ``toad acp "ahohs acp" .``.
    Nothing is printed to stdout but protocol messages; a missing optional library is said on stderr with the install line (exit 2)."""
    from pathlib import Path
    from hubofhubs.the_consciousness.ai_session_experience.acp_agent.server import AcpUnavailable, HubAgent, sdk, serve
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import work as terminal
    from hubofhubs.the_self.assembler.resolution import process_environment
    try:
        sdk()
        usd = terminal.dollars_of(args.max_spend) if args.max_spend is not None else None
        seconds = terminal.seconds_of(args.max_time) if args.max_time is not None else None
        usd = "unlimited" if usd is None and args.max_spend is not None else usd
        seconds = "unlimited" if seconds is None and args.max_time is not None else seconds
        name = args.harness or terminal.default_harness()[0]
        if name not in terminal.HARNESSES:
            raise ValueError(f"no harness named {name!r}; choose one of {', '.join(terminal.HARNESSES)}")

        def build(folder: str):
            return terminal.harness_builder(folder=str(Path(folder).resolve()), tier=main_session_tier("", args.tier), ceiling_usd=usd, ceiling_seconds=seconds, permission=args.permission,
                                            environ=process_environment(), solution=args.solution, milestone=args.milestone, setting_sources=args.setting_sources)(name)
        steering = bool(build(args.folder).capabilities.steer)
    except AcpUnavailable as error:
        print(error, file=sys.stderr)
        return 2
    except ValueError as error:
        print(f"failed: {error}", file=sys.stderr)
        return 2
    serve(HubAgent(build, folder=args.folder, steering=steering, acting_for=args.person))
    return 0


def main_session_choice(task_kind: str = "", requested: str = "", standing=None):
    """The tier choice of a deep-work session (a ``TierChoice``: tier, source and reason, ``record()`` for the run's record): the tier the person names now
    (``requested``, the ``--tier`` or ``--model`` flag; a model the hub serves is run as named), else the tier their standing guidance names (``standing``, a function role to tier a consumer supplies; the command line
    has none), else the cheapest tier measured good enough for deep work, for the role of the task kind (gather, implementation, structure, review) or the
    implementation role when the kind is not given."""
    from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers, tiers
    model = tiers.explicit_model("anthropic", requested) if role_tiers.normalise(requested) not in role_tiers.TIERS else None
    if model:       # a model the hub serves, named instead of a tier: the session runs on exactly that model (its name stands where the tier would)
        return role_tiers.TierChoice(role_tiers.deep_work_role(task_kind), model, "current_input", "the person named this model in the current request")
    return role_tiers.task_choice(task_kind, requested, standing=standing)


def main_session_tier(task_kind: str = "", requested: str = "", standing=None) -> str:
    """The tier of a deep-work session: ``main_session_choice(...).tier``."""
    return main_session_choice(task_kind, requested, standing).tier


def task_kind_choices() -> tuple:
    """The task kinds the role table knows, for the command line."""
    from hubofhubs.the_world.model_plumbing.model_tier_chooser.role_tiers import task_kinds
    return tuple(sorted(task_kinds()))


def main(argv: Optional[List[str]] = None) -> int:
    import hubofhubs
    parser = argparse.ArgumentParser(prog="ahohs", description="Run the hub from one line.")
    sub = parser.add_subparsers(dest="command", required=False)
    work = sub.add_parser("work", help="run a goal on a real harness in the live terminal; with no goal, a prompt (also what bare ahohs opens)")
    work.add_argument("goal", nargs="?", default="", help="what to get done in this folder; leave out for a prompt, and type follow-ups that continue the session")
    work.add_argument("--harness", default="", help="native, adaptive, solution_agents, stream or loop (default: the hub's own pick for a person at a terminal)")
    work.add_argument("--tier", default="", help="model tier: fast, balanced, quality or best (strong reads as quality); default: the cheapest tier measured good enough for deep work (the role table), unless your standing guidance names another")
    work.add_argument("--model", default="", help="an explicit model the hub serves, instead of a tier (see the models in the opencode picker or tiers.served_models); the session runs on exactly that model")
    work.add_argument("--task-kind", default="", choices=("",) + task_kind_choices(), help="the kind of the task (gather, implementation, structure or review), which sets the default tier; unknown reads as implementation")
    work.add_argument("--folder", default=".", help="the folder the work happens in (default: this one)")
    work.add_argument("--resume", default="", metavar="SESSION", help="continue a session an earlier run named, in the same folder: its id, or last for the most recent one (the harness that ran it is used unless you give --harness)")
    work.add_argument("--max-spend", default=None, metavar="USD", help="spend ceiling in dollars, or unlimited (default: the hub's high default)")
    work.add_argument("--max-time", default=None, metavar="TIME", help="time ceiling like 90s, 30m, 2h, or unlimited (default: the hub's high default)")
    work.add_argument("--permission", default="acceptEdits", choices=("acceptEdits", "skip"), help="acceptEdits: files may be read and changed, commands are refused and listed; skip: no permission checks")
    work.add_argument("--solution", default="", help="the solution this work serves (shown in the header; helpers are placed under it)")
    work.add_argument("--milestone", default="", help="the milestone it serves")
    work.add_argument("--records", default="", help="the ESOI records the structure view reads (default: this folder when it has esoi.toml)")
    work.add_argument("--as", dest="person", default="", metavar="NAME", help="act for this representative (its authority and stop limits apply; /as switches)")
    work.add_argument("--terminal", default="", help="the screen: live_session, textual_session, polished_session, adopted_session (the interface of an existing terminal agent, vendored), acp_client_session (an installed ACP client such as Toad draws it) or line_repl (default: the hub's selected one; the best-measured arm that can run stands in when one's library or program is missing, with the reason shown)")
    work.add_argument("--setting-sources", default="project", help="which of the Claude CLI's setting sources a session loads: project (default: this folder's own, never your user-level settings and hooks), or a list such as user,project")
    work.add_argument("--structure-watch", default="on", choices=("on", "off"), help="on (default): one small best-tier look at the records after a run that changed something, when there are records; off: never")
    work.add_argument("--context", default="", metavar="FILE", help="the file of your own context sources (default: $AHOHS_CONTEXT, else ~/.config/ahohs/context.toml when it exists; none means no saved context)")
    work.add_argument("--focus", default="", help="the focus whose saved notes are used first (default: the one in the context file)")
    work.add_argument("--plain", action="store_true", help="plain lines even on a terminal")
    work.add_argument("--opencode-mode", default="", choices=("", "full", "inline"), help="with --terminal opencode_client_session: full (the client's full-screen interface, default) or inline (opencode mini, into the terminal's own scrollback)")
    from hubofhubs.the_consciousness.ai_session_experience.opencode_server.command import add_arguments as add_opencode_server
    add_opencode_server(sub)
    acp = sub.add_parser("acp", help="serve the hub's session harness as an Agent Client Protocol agent on stdio (an ACP terminal client launches it, for example: toad acp \"ahohs acp\" .); needs the extra acp")
    acp.add_argument("--harness", default="", help="native, adaptive, solution_agents, stream or loop (default: the hub's own pick)")
    acp.add_argument("--tier", default="", help="model tier: fast, balanced, quality or best")
    acp.add_argument("--model", default="", help="an explicit model the hub serves, instead of a tier")
    acp.add_argument("--folder", default=".", help="the folder a session works in when the client names none")
    acp.add_argument("--max-spend", default=None, metavar="USD", help="spend ceiling in dollars, or unlimited")
    acp.add_argument("--max-time", default=None, metavar="TIME", help="time ceiling like 90s, 30m, 2h, or unlimited")
    acp.add_argument("--permission", default="acceptEdits", choices=("acceptEdits", "skip"), help="acceptEdits: commands are refused and listed; skip: no permission checks")
    acp.add_argument("--solution", default="", help="the solution this work serves")
    acp.add_argument("--milestone", default="", help="the milestone it serves")
    acp.add_argument("--as", dest="person", default="", metavar="NAME", help="who the AI acts for, said in the first message")
    acp.add_argument("--setting-sources", default="project", help="which of the Claude CLI's setting sources a session loads")
    one = sub.add_parser("run", help="answer one input with the best-measured arm of the whole hub, or of one id")
    one.add_argument("input")
    one.add_argument("--id", default="hub-of-hubs", help="the solution or intent to run (default: the whole hub)")
    one.add_argument("--arm", action="append", default=[], metavar="ID=ARM", help="override one solution's arm")
    one.add_argument("--lock", default=None, help="an esoi.lock.json to keep the locked arms")
    one.add_argument("--json", action="store_true", help="print the result as one JSON object")
    talk = sub.add_parser("chat", help="talk to the whole hub line by line (/help inside lists the commands)")
    talk.add_argument("--arm", action="append", default=[], metavar="ID=ARM", help="override one solution's arm")
    talk.add_argument("--lock", default=None, help="an esoi.lock.json to keep the locked arms")
    record = sub.add_parser("investigation", help="write an investigation (research that informs a solution, arm, metric or registry finding) from a JSON file: `ahohs investigation record FILE`")
    record.add_argument("action", choices=("record",), help="record: check the file against the knowledge search standard and write its rows into investigations.csv and investigation_items.csv")
    record.add_argument("file", help="JSON with `investigation` (the cells of investigations.csv) and `items` (one object per kept item); cells left out are filled")
    record.add_argument("--folder", default=None, help="the folder holding the two files (default: the hub's registry)")
    record.add_argument("--allow-gaps", action="store_true", help="write the record even when it lacks parts of its size (the gaps are printed)")
    args = parser.parse_args(argv)
    if getattr(args, "model", ""):       # --model is a tier-less way to name the session's model: it travels where the tier travels
        if args.tier:
            print("failed: give --tier or --model, not both", file=sys.stderr)
            return 2
        args.tier = args.model
    if args.command == "investigation":
        from hubofhubs.the_world.learning.investigation_store import record_investigation
        try:
            done = record_investigation(args.file, args.folder, allow_gaps=args.allow_gaps)
        except (ValueError, OSError) as error:
            print(f"failed: {error}", file=sys.stderr)
            return 1
        print(done["investigation_id"])
        for gap in done["gaps"]:
            print(f"gap: {gap}", file=sys.stderr)
        return 0
    if args.command is None:
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            parser.print_help()
            return 0
        args = parser.parse_args(["work"])
    if args.command == "work":
        return work_command(args, hubofhubs)
    if args.command == "acp":
        return acp_command(args)
    if args.command == "opencode-server":
        from hubofhubs.the_consciousness.ai_session_experience.opencode_server.command import serve_command
        return serve_command(args)
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
