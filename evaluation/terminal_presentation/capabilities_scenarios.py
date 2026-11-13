"""The capability scenario of the presentation metric (revision 6, 2026-11-12): what a person can DO from the screen beyond watching, scored for every arm, the stock clients included.

The owner tried every terminal arm and named what revisions 1 to 5 did not measure: the richness of the screen (a command palette, many commands, tabs or switching between sessions, going
in and out of helpers, a different presentation for each kind of update). Each capability is a measurable probe of the arm's own screen, never an assertion:

* the arm's discovery action is pressed (the hub arms: the help line; the opencode client: its command palette, then the palette filtered by a word; Toad: its footer, its palette and its
  sessions key), and what the screen then shows is read back (rows, through the same emulator as every other scenario);
* ``command-surface-listed``: the discovery screen shows at least ``MIN_LISTED`` rows that were not on the screen before (a palette or help that lists, not a one-line hint);
* ``command-surface-broad``: the discovery screens together show at least ``MIN_BROAD`` such rows (many commands, not a handful);
* ``session-list-and-resume``: the surfaces name a list of sessions and a way to resume one (an arm that cannot be driven for it can show it in the protocol layer: Toad's agent says it loads a session);
* ``session-switching``: the surfaces name tabs, a session picker or a switch between sessions;
* ``agent-navigation``: a person can go into a helper and back. A hub arm is driven through its own keys (the scenario ``agents_depth1``); a client is read through its surface (an entry that names
  a helper or sub-agent and a verb of going into it);
* ``kind-presentation``: the rows for a read, an edit, a command, a command that did not work and a helper are drawn with at least ``MIN_KINDS`` different markers (the glyph that begins the row);
  a screen that begins them all with the same tick presents every update kind alike.

Limits, stated: the diff body and the plan are not part of the hub's event vocabulary yet (a step carries a label and a state, no diff text and no list of plan items), so they are not scored and
the kind check reads the rows the hub does send; the marker is read from the screen's text, so colour and typeface differences are not seen (they are judged by the contrast check and layer 2);
the thresholds are judgement fixed in advance with the weights (``[balance.terminal_presentation.check_weights]``), not fitted to any arm. Standard library and the hub only."""
from __future__ import annotations

import os
import re
import shlex
import shutil
import sys
import tempfile
import time
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import checks as C
from screen import Capture, Snapshot

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import (
    delegate, edit, fail_run, read, report, run, stream_kit, turn)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys

SIZE = (120, 40)
MIN_LISTED, MIN_BROAD, MIN_KINDS = 5, 12, 4
CHECKS = ("command-surface-listed", "command-surface-broad", "session-list-and-resume", "session-switching", "agent-navigation", "kind-presentation")
NOT_DRIVEN = "revision 6 (2026-11-12): this arm's screen could not be driven for the capability probes (client missing)"
SESSIONS = re.compile(r"\bsessions\b|session list|switch session|\bhistory\b")
RESUME = re.compile(r"\bresume\b|\bcontinue (the )?(last )?session|--continue|switch session|open session|session picker")      # a picker that opens an earlier session resumes it
SWITCHING = re.compile(r"\btabs\b|\b(new|close|reopen closed|next|previous) tab\b|switch session|session picker|next session|sessions[\s\S]{0,400}select|select[\s\S]{0,400}sessions")       # the key named Tab is not a tab
NAVIGATION = re.compile(r"(sub-?agents?|helpers?|child|agents?)")
NAVIGATE_VERB = re.compile(r"\b(open|enter|picker|pick|switch|cycle|next|previous|toggle)\b")
FRAME = " ┃│▎▌▊▏▕|╹▀╭╮╰╯─"
KIND_ROWS = (("failed", re.compile(r"did not work|failed|error|not found|couldn't")), ("edit", re.compile(r"\bedit(ed)?\b|\bwrote\b|\bwrite\b")), ("run", re.compile(r"\bran\b|\brun\b|\$ ")),
             ("read", re.compile(r"\bread\b")), ("helper", re.compile(r"helper|sub-?agent")))
PRESENTATION_NOTE = "a row that begins with the same marker as another kind's row presents it alike"


def rows_of(snapshot: Snapshot, left: int = 0) -> List[str]:
    return [r[left:].strip() for r in snapshot.rows if r[left:].strip()]


def new_rows(shots: Sequence[Snapshot], baseline: Any, left: int = 0) -> List[str]:
    """The distinct rows the discovery screens show that the baseline (a screen, or every screen of a control run that pressed nothing) did not."""
    before = set(rows_of(baseline, left)) if isinstance(baseline, Snapshot) else {r for s in baseline for r in rows_of(s, left)}
    seen: List[str] = []
    for shot in shots:
        for row in rows_of(shot, left):
            if row not in before and row not in seen:
                seen.append(row)
    return seen


def marker(row: str) -> str:
    """The glyph that begins a row: its first symbols before the first letter or digit, after the frame characters a client draws around a block."""
    text = row.lstrip(FRAME)
    glyph = ""
    for char in text:
        if char.isalnum():
            break
        if not char.isspace():
            glyph += char
    return glyph[:3]


TOKENS = {"read": "ka.txt", "edit": "kb.txt", "run": "kc", "helper": "write the tests"}      # the words the scripted run gives each kind of step, so its row is found by name


def kind_markers(texts: Sequence[str], tokens: bool = True) -> Dict[str, str]:
    """The marker of the first row of each update kind found on the screens (a kind not on the screen is left out). The scripted run's own words find the rows of the read, the edit, the command
    and the helper; a row that says a command did not work is found by those words. A run the scenario did not script (Toad's, driven against the hub's demo agent) is read by the verbs instead."""
    found: Dict[str, str] = {}
    for text in texts:
        for row in text.splitlines():
            line = row.lower()
            if not row.strip() or line.strip().startswith(("do the work", "❯", "you")) or row.strip().startswith(("Changed", "Agents")):
                continue
            for kind, pattern in KIND_ROWS:
                named = TOKENS.get(kind)
                hit = (named in line) if (tokens and named) else bool(pattern.search(line))
                if kind == "failed":
                    hit = bool(pattern.search(line)) and not any(t in line for t in TOKENS.values())
                if kind not in found and hit:
                    found[kind] = marker(row)
                    break
    return found


def verdicts(surface: str, listed: Sequence[str], broad: Sequence[str], navigation: Optional[bool], kinds: Dict[str, str], extra: str = "") -> Dict[str, Optional[bool]]:
    """The six checks from what the probes read. ``surface`` is the text of every discovery screen, ``extra`` the evidence a protocol layer adds (Toad's agent loads a session)."""
    text = (surface + "\n" + extra).lower()
    nav = navigation
    if nav is None:
        entries = [line for line in text.splitlines() if NAVIGATION.search(line) and NAVIGATE_VERB.search(line)]
        nav = bool(entries)
    return {"command-surface-listed": len(listed) >= MIN_LISTED, "command-surface-broad": len(broad) >= MIN_BROAD,
            "session-list-and-resume": bool(SESSIONS.search(text)) and bool(RESUME.search(text)), "session-switching": bool(SWITCHING.search(text)),
            "agent-navigation": nav, "kind-presentation": len(set(kinds.values())) >= MIN_KINDS}


def details(listed: Sequence[str], broad: Sequence[str], kinds: Dict[str, str]) -> str:
    return f"rows listed {len(listed)} (need {MIN_LISTED}), rows in all {len(broad)} (need {MIN_BROAD}), markers {kinds or 'none found'} ({len(set(kinds.values()))} distinct, need {MIN_KINDS})"


# --- an arm drawn in this process (the hub's own terminals) -----------------------------------------------------------------------------------------------------------------------

def script(keys: ScriptedKeys, hook: Optional[Callable[[], None]]) -> Any:
    import scenarios as S
    helper = delegate("write the tests", turn(edit("t.txt"), report("tests done")))
    return stream_kit(S.folder(), [turn(read("ka.txt"), hook=hook), turn(edit("kb.txt"), run("echo kc"), fail_run("false")), turn(helper), turn(report("All done."))], pause=0.6)


def in_process(arm: Any) -> Dict[str, Any]:
    import agents_scenarios as A
    import scenarios as S
    discovery = tuple(getattr(arm, "capability_discovery", None) or ("line", "/help"))
    pressed: Dict[str, float] = {}
    keys = ScriptedKeys()
    cap = S.capture(arm, script(keys, lambda: (pressed.setdefault("at", time.monotonic()), keys.press(*discovery))), keys, SIZE)
    at = pressed.get("at", cap.begun) - cap.begun
    shots = [s for s in cap.snapshots if at <= s.at <= at + 2.5]
    control = S.capture(arm, script(ScriptedKeys(), None), ScriptedKeys(), SIZE)         # the same run with nothing pressed: whatever it shows is not the discovery surface
    listed = new_rows(shots, control.snapshots)
    surface = "\n".join(listed)
    walk = A.SCENARIOS["agents_depth1"](arm)["checks"]
    navigation = bool(walk.get("agents-shown-with-state")) and bool(walk.get("agent-view-enter-and-leave"))
    kinds = kind_markers([cap.final_text(), cap.all_text()])
    out = verdicts(surface, listed, listed, navigation, kinds)
    return {"checks": out, "ceiling": {}, "note": details(listed, listed, kinds)}


# --- the stock opencode client, driven in a pseudo-terminal -------------------------------------------------------------------------------------------------------------------------

PALETTE_WORDS = ("session", "agent", "tab")


def opencode() -> Dict[str, Any]:
    import opencode_external as O
    if not O.client_path():
        return {"checks": {}, "ceiling": {}, "not_run": list(CHECKS), "note": NOT_DRIVEN}
    O.drive(stream_kit(O.folder(), [turn(report("warm"))], pause=0.0).harness, "warm", SIZE)

    def palette(word: str) -> Capture:
        kit = stream_kit(O.folder(), [turn(read("ka.txt"), report("All done."))], pause=0.3)
        reactions: List[Any] = [(O.shown("All done"), b"\x10"), (O.shown("Commands"), word.encode())] if word else [(O.shown("All done"), b"\x10")]
        return O.drive(kit.harness, "do the work", SIZE, reactions, settle=1.5)

    def open_rows(cap: Capture) -> Tuple[List[Snapshot], int]:
        shots = [s for s in cap.snapshots if any("Commands" in r and r.rstrip().endswith("esc") for r in s.rows)]
        column = next((r.index("Commands") for s in shots[-1:] for r in s.rows if "Commands" in r and r.rstrip().endswith("esc")), 0)
        return shots, column

    plain = palette("")
    shots, column = open_rows(plain)
    base = next((s for s in plain.snapshots if not any("Commands" in r for r in s.rows)), Snapshot(0.0, ()))
    listed = new_rows(shots, base, column)
    broad = list(listed)
    surface = list(listed)
    for word in PALETTE_WORDS:
        cap = palette(word)
        found, where = open_rows(cap)
        for row in new_rows(found, base, where):
            if row not in broad:
                broad.append(row)
        surface += new_rows(found, base, where)
    kit = stream_kit(O.folder(), [turn(read("ka.txt")), turn(edit("kb.txt"), run("echo kc"), fail_run("false")), turn(delegate("write the tests", turn(edit("t.txt"), report("tests done")))), turn(report("All done."))], pause=0.5)
    shown = O.drive(kit.harness, "do the work", SIZE)
    kinds = kind_markers([shown.final_text(), shown.all_text()])
    out = verdicts("\n".join(surface), listed, broad, None, kinds)
    return {"checks": out, "ceiling": {}, "note": "the real client drew these screens: " + details(listed, broad, kinds)}


# --- Toad, driven in a pseudo-terminal against the hub's protocol agent --------------------------------------------------------------------------------------------------------------

def toad() -> Dict[str, Any]:
    import external as X
    import opencode_external as O
    if not shutil.which("toad"):
        return {"checks": {}, "ceiling": {}, "not_run": list(CHECKS), "note": NOT_DRIVEN}
    try:
        import acp  # noqa: F401
    except ImportError:
        return {"checks": {}, "ceiling": {}, "not_run": list(CHECKS), "note": "the Agent Client Protocol SDK is not installed (pip install 'hubofhubs[acp]')"}
    folder, home = O.folder(), tempfile.mkdtemp(prefix="toad-home-")
    paths = os.pathsep.join(os.path.abspath(p) for p in sys.path if p)
    agent = "env PYTHONPATH=" + shlex.quote(paths) + " " + " ".join(shlex.quote(a) for a in X.AGENT)        # the agent gets the hub's path; the client, its own, so no path of ours leaks into its interpreter
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "TERM": "xterm-256color", "HOME": home}
    term = O.Pty(["toad", "acp", agent, folder], SIZE, env, folder, history=False)
    seen: List[Snapshot] = []
    try:
        term.pump(8)

        def shot() -> Snapshot:
            return Snapshot(time.monotonic(), term.rows())
        idle = shot()
        surfaces = [idle]
        term.send(b"ship it\r")                    # a run first (the hub's demo agent), read for the kinds of rows; then the palette and the sessions screen are opened over it
        term.pump(14)
        seen.append(shot())
        for key in (b"\x10", b"\x13"):
            term.send(key)
            term.pump(3)
            surfaces.append(shot())
            term.send(b"\x1b")
            term.pump(1)
    finally:
        term.close()
        shutil.rmtree(home, ignore_errors=True)
    before = [idle, *seen]                         # the screens before anything was opened
    listed = new_rows(surfaces[1:2], before)
    broad = new_rows(surfaces[1:], before)
    surface = "\n".join(["\n".join(s.rows) for s in surfaces[:1]] + broad)        # the idle screen's key footer (it lists the sessions key) and what the palette and the sessions screen added
    kinds = kind_markers(["\n".join(s.rows) for s in seen], tokens=False)
    protocol = "resume: the agent loads a session (agent capability load_session)" if load_session_declared() else ""
    out = verdicts(surface, listed, broad, None, kinds, protocol)
    return {"checks": out, "ceiling": {}, "note": "the real client drew these screens: " + details(listed, broad, kinds)}


def load_session_declared() -> bool:
    """Whether the hub's protocol agent tells a client it can load (resume) a session: read from its initialize reply."""
    import asyncio

    import external as X

    async def ask() -> bool:
        from hubofhubs.the_world.tools.delegated_agent_sessions.acp_session import open_agent_connection
        client = X.Client(tempfile.mkdtemp(prefix="acp-"))
        async with open_agent_connection(client, X.AGENT, env={**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}, cwd=client.folder) as (conn, _):
            reply = await conn.initialize(protocol_version=1, client_capabilities={"fs": {"readTextFile": False, "writeTextFile": False}})
            return bool(getattr(reply.agent_capabilities, "load_session", False))
    try:
        return asyncio.run(ask())
    except Exception:  # noqa: BLE001 -- an agent that cannot be asked has not shown the capability
        return False
