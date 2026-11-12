"""The sub-agent hierarchy scenarios of the presentation metric (revision 4): a run with helpers nested to depth 1, 2 and 4, driven by a scripted event stream (no model) and read back from the
screen through the same capture as every other scenario (the terminal emulator for a stream arm, Textual's ``run_test`` for a Textual arm).

The person's side is scripted with the keys the arm declares: ``agent_keys`` (the tokens a script presses for enter, leave, next, message and stop; the hub arms take ``open``, ``close``, ``down``, ``line``
and ``esc``) and ``agent_labels`` (the words its screen uses for them, like ``screen_labels``). The harness side is a ``NestedHarness`` that records every control it takes with the agent id it was
aimed at, so "the message reached the right agent" is asserted on the harness and "the message visibly landed" on the screen.

Observed on the screen at named moments (``Probe.marks``): the main view lists each helper one level down with its state; entering a helper shows a breadcrumb and its live activity; leaving
goes back; a message typed inside a helper is aimed at that helper (and one typed at the top at the main session); Escape inside a helper stops that helper and not the run; a helper's own helpers
are entered the same way at any depth, and one key goes up one level; a finished helper stays in its parent's list, its result is shown once there, and it can be entered to read what it did; and the
screen at depth 4 is as wide, as tall in header and footer, as quick and as full of key hints as at depth 1 (the tolerances are in ``TOLERANCE``, stated once and recorded in the metric's record).
Standard library only (the capture uses the emulator).
"""
from __future__ import annotations

import json
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import checks as C
from screen import SIZES, Capture

from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    MAIN, AgentEnded, AgentStarted, Capabilities, Finished, RunStarted, Step, Steer, Stop, Usage, event_from_dict)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys

#: the words of the helpers: the first of each is in its task, its breadcrumb name (the first ten characters of the task), the file it reads and its row
NAMES = (("alpha", "survey alpha beds"), ("bravo", "check bravo moon"), ("charlie", "read charlie soil"), ("delta", "scan delta seeds"))
SIBLING = ("zulu", "note zulu extra")
DEFAULT_KEYS = {"enter": ("open", ""), "leave": ("close", ""), "next": ("down", ""), "stop": ("esc", "")}
DEFAULT_LABELS = {"enter": "Right", "leave": "Left", "message": "type + Enter", "stop": "Esc"}
PAUSE = 0.5          # the fixed wait of a harness that cannot look at the screen
LIMIT = 8.0          # the longest a scripted person waits for a screen to answer a key before reading it as it is (a screen slower than this fails the check on what it shows)
SETTLE = 0.2
#: stated once (and recorded in the metric): at depth 4 the content may start at most 2 columns further right than at depth 1, the header and the footer may differ by at most 1 row, entering a
#: helper may take at most 0.25 s more than at depth 1 and never more than 1.5 times as long, and every key label shown at depth 1 is shown at depth 4
TOLERANCE = {"indent_columns": 2, "chrome_rows": 1, "latency_seconds": 0.25, "latency_ratio": 1.5}
CHAIN = "agent-{}"
NOT_DRIVEN = ("revision 4 (2026-11-12): the checks of the agent hierarchy are not run on a third-party client: its own keys for going into a helper are not driven by this metric yet, so they are "
              "listed as not run and are neither a pass nor a fail")


class Probe:
    """What the scripted run recorded: when each moment was reached, what the harness received, and the helpers of the run."""

    def __init__(self, depth: int, tasks: Sequence[Tuple[str, str]], sibling: Optional[Tuple[str, str]]) -> None:
        self.depth, self.tasks, self.sibling = depth, list(tasks), sibling
        self.marks: Dict[str, float] = {}
        self.presses: Dict[str, float] = {}
        self.received: List[Tuple[str, str, str, float]] = []        # (control type, agent id, text, time)
        self.stop_all_at: Optional[float] = None

    def word(self, level: int) -> str:
        return self.tasks[level - 1][0]

    def crumb(self, level: int) -> str:
        return self.tasks[level - 1][1][:10]


class NestedHarness:
    """A harness that runs a scripted tree of helpers while a script presses the person's keys, and takes controls aimed at one agent."""
    name = "native"
    capabilities = Capabilities(stop=True, resume=False, steer=True, approve=False, target_agents=True, live_usage=True, live_agents=True, steer_ack=True)

    def __init__(self, keys: ScriptedKeys, depth: int, arm: Any, pause: float = PAUSE, replay: Optional[List[Dict[str, Any]]] = None) -> None:
        self.keys, self.depth, self.pause, self.replay = keys, depth, pause, replay
        self.token = {**DEFAULT_KEYS, **dict(getattr(arm, "agent_keys", None) or {})}
        tasks = NAMES[:depth] if replay is None else self.replayed_tasks(replay)
        self.probe = Probe(depth, tasks, SIBLING if replay is None else None)
        self.sink: Callable[[Any], None] = lambda event: None
        self.release = threading.Event()
        self.parents: Dict[str, str] = {}
        self.goal = "Use a helper to look into the notes, then tell me what you think"
        self.t0 = 0.0
        self.peek: Optional[Callable[[], Tuple[str, Sequence[str]]]] = None

    @staticmethod
    def replayed_tasks(events: List[Dict[str, Any]]) -> List[Tuple[str, str]]:
        return [(str(e["task"]).split()[-1], str(e["task"])) for e in events if e.get("type") == "agent-started"][:1]

    # --- the person's side ----------------------------------------------------------------------------------------------------

    def press(self, name: str, text: str = "") -> None:
        token, default = self.token[name] if name in self.token else ("line", "")
        self.probe.presses[name + "@" + str(len(self.probe.presses))] = time.monotonic()
        self.keys.press(token, text or default)

    def message(self, text: str) -> None:
        self.keys.press("line", text)

    def mark(self, name: str) -> None:
        self.probe.marks[name] = time.monotonic()

    def wait(self, factor: float = 1.0) -> None:
        time.sleep(self.pause * factor)

    def until(self, ready: Callable[[str, Sequence[str]], bool], timeout: float = LIMIT) -> None:
        """Wait for the screen to show what the key should have made it show (``ready(text, rows)``), as a person does, up to a generous ``timeout``; then a short settle. A screen that never
        shows it is read as it is, and the check fails on what it shows. Without a way to look at the screen (``peek``) it waits the fixed ``pause``."""
        if self.peek is None:
            self.wait()
            return
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            try:
                text, rows = self.peek()
            except Exception:  # noqa: BLE001 -- a screen that cannot be read yet is not ready
                text, rows = "", ()
            if ready(text, rows):
                break
            time.sleep(0.1)
        time.sleep(SETTLE)

    def in_crumb(self, level: int) -> Callable[[str, Sequence[str]], bool]:
        return lambda text, rows: self.probe.crumb(level) in crumb_row(rows)

    def at_main(self, text: str, rows: Sequence[str]) -> bool:
        return bool(rows) and not crumb_row(rows) and any(self.probe.word(1) in r and "running" in r or self.probe.word(1) in r and "stopped" in r for r in rows)

    def shows(self, word: str) -> Callable[[str, Sequence[str]], bool]:
        return lambda text, rows: word in text

    # --- the Harness contract -----------------------------------------------------------------------------------------------------

    def control(self, control: Any) -> bool:
        kind, who, text = control.type, getattr(control, "agent_id", "") or "", getattr(control, "text", "") or ""
        self.probe.received.append((kind, who, text, time.monotonic()))
        if isinstance(control, Steer):
            threading.Timer(0.15, lambda: self.sink(Step(agent_id=who or MAIN, step_id=control.message_id, kind="message-received", label=text))).start()
            return True
        if isinstance(control, Stop):
            if who:
                for ident in self.under(who):
                    word = next((w for i, (w, _) in enumerate(self.probe.tasks, 1) if CHAIN.format(i) == ident), "zulu")
                    self.sink(AgentEnded(agent_id=ident, state="stopped", calls=1, summary=f"RESULT-{word.upper()} stopped when asked"))
                return True
            self.probe.stop_all_at = time.monotonic()
            self.release.set()
            return True
        return False

    def under(self, who: str) -> List[str]:
        found = [who]
        for _ in range(len(self.parents)):
            more = [child for child, parent in self.parents.items() if parent in found and child not in found]
            if not more:
                break
            found.extend(more)
        return list(reversed(found))        # the deepest first, so a screen never shows a parent ended while a child still runs

    def start(self, goal: str, sink: Callable[[Any], None], resume_session_id: str = "") -> Finished:
        self.sink = sink
        self.t0 = time.monotonic()
        if self.replay is not None:
            return self.play_replay(sink)
        sink(RunStarted(goal=goal, harness="native"))
        sink(Step(step_id="plan", kind="read", label="plan.txt", state="done"))
        prior = MAIN
        for level, (word, task) in enumerate(self.probe.tasks, 1):
            ident = CHAIN.format(level)
            self.parents[ident] = prior
            sink(AgentStarted(agent_id=ident, parent_id=prior, task=task))
            sink(Step(agent_id=prior, step_id=ident, kind="delegate", label=task, state="running"))
            sink(Step(agent_id=ident, step_id=f"{ident}-read", kind="read", label=f"{word}.md", state="running"))
            sink(Usage(agent_id=ident, tokens=1000 * level, calls=level))
            prior = ident
        sibling_word, sibling_task = SIBLING
        self.parents["agent-z"] = MAIN
        sink(AgentStarted(agent_id="agent-z", parent_id=MAIN, task=sibling_task))
        sink(Step(agent_id="agent-z", step_id="z-read", kind="read", label=f"{sibling_word}.md", state="running"))
        sink(Usage(cost_usd=0.001, tokens=100, calls=2))
        self.until(lambda text, rows: any(probe_word in r and "running" in r for r in rows for probe_word in (self.probe.word(1),)))
        self.mark("main")
        for level in range(1, self.depth + 1):                 # in, to any depth
            self.press("enter")
            self.until(self.in_crumb(level))
            sink(Step(agent_id=CHAIN.format(level), step_id=f"{CHAIN.format(level)}-run", kind="run", label=f"checking {self.probe.word(level)} notes", state="running"))
            self.wait(0.5)
            self.mark(f"in:{level}")
        self.message("MSG-DEEP")
        self.until(self.shows("MSG-DEEP"))
        self.mark("msg-deep")
        for level in range(self.depth - 1, 0, -1):             # out, one key a level
            self.press("leave")
            self.until(lambda text, rows, level=level: self.probe.crumb(level) in crumb_row(rows) and self.probe.crumb(level + 1) not in crumb_row(rows))
            self.mark(f"up:{level}")
        self.press("leave")
        self.until(self.at_main)
        self.mark("main2")
        self.press("enter")                                    # the first helper alone: a message to it, then a stop of it only
        self.until(self.in_crumb(1))
        self.message("MSG-ONE")
        self.until(self.shows("MSG-ONE"))
        self.mark("msg-one")
        self.press("stop")
        self.until(self.shows("stopped"))
        self.mark("one-stopped")
        sink(AgentEnded(agent_id="agent-z", state="met", calls=1, tokens=50, summary="RESULT-ZULU two finds"))
        sink(Step(agent_id=MAIN, step_id="agent-z", kind="delegate", label=sibling_task, state="done"))
        self.press("leave")
        self.until(lambda text, rows: self.at_main(text, rows) and any("stopped" in r for r in rows))
        self.mark("main3")
        self.press("next")                                     # the finished sibling stays in the list and can be entered
        self.press("enter")
        self.until(lambda text, rows: SIBLING[1][:10] in crumb_row(rows))      # inside the finished helper (its result is already in the parent's rows, so the result is not the sign)
        self.mark("zulu-in")
        self.press("leave")
        self.until(self.at_main)
        self.mark("main4")
        self.message("MSG-MAIN")
        self.until(self.shows("MSG-MAIN"))
        self.mark("msg-main")
        self.press("stop")                                     # at the top Escape stops the run
        self.release.wait(3)
        done = Finished(outcome="stopped", report="Stopped.", session_id="scripted")
        sink(done)
        return done

    def play_replay(self, sink: Callable[[Any], None]) -> Finished:
        """The recorded real run: its events in order, paced, with the same walk in and out of the one helper while it works and after it ended."""
        done: Optional[Finished] = None
        began = time.monotonic()
        helper_ended = False
        entered = False
        for item in self.replay or []:
            event = event_from_dict(item)
            if isinstance(event, Finished):
                break
            sink(event)
            time.sleep(0.03)
            if isinstance(event, AgentStarted) and not entered:
                entered = True
                self.wait(2)
                self.mark("main")
                self.press("enter")
                self.wait()
                self.mark("in:1")
                self.press("leave")
                self.wait()
                self.mark("main2")
            if isinstance(event, AgentEnded) and not helper_ended:
                helper_ended = True
                self.wait()
                self.mark("main3")
                self.press("enter")
                self.wait()
                self.mark("zulu-in")
                self.press("leave")
                self.wait()
                self.mark("main4")
        for item in self.replay or []:
            if item.get("type") == "finished":
                done = event_from_dict(item)
        sink(done or Finished(outcome="met", report=""))
        return done or Finished(outcome="met")


class Kit:
    def __init__(self, harness: NestedHarness) -> None:
        self.harness, self.goal = harness, harness.goal


# --- reading the screen at a moment ---------------------------------------------------------------------------------------------

def snapshot_at(cap: Capture, when: float) -> Any:
    found = None
    for snap in cap.snapshots:
        if snap.at <= when - cap.begun + 1e-6:
            found = snap
    return found or (cap.snapshots[0] if cap.snapshots else None)


def screen(cap: Capture, probe: Probe, name: str) -> Tuple[str, Tuple[str, ...]]:
    """``(whole text with the scrollback, the visible rows)`` at the moment ``name``, or empty when the run never reached it."""
    when = probe.marks.get(name)
    snap = snapshot_at(cap, when) if when is not None else None
    return (cap.text_at(snap), snap.rows) if snap is not None else ("", ())


def crumb_row(rows: Sequence[str]) -> str:
    return next((r for r in rows if "main" in r and re.search(r" [>›] ", r)), "")


def row_with(rows: Sequence[str], *words: str) -> str:
    return next((r for r in rows if all(w in r for w in words)), "")


# --- the checks: each over one capture and its probe, True, False, or None when the run never got there --------------------

def listed_with_state(cap: Capture, probe: Probe) -> Optional[bool]:
    text, rows = screen(cap, probe, "main")
    if not rows:
        return False
    first = row_with(rows, probe.word(1), "running")
    sibling = row_with(rows, probe.sibling[0], "running") if probe.sibling else "running"
    return bool(first and sibling)


def enter_and_leave(cap: Capture, probe: Probe) -> Optional[bool]:
    _, inside = screen(cap, probe, "in:1")
    text_in, _ = screen(cap, probe, "in:1")
    _, back = screen(cap, probe, "main2")
    if not inside or not back:
        return False
    here = probe.crumb(1) in crumb_row(inside) and any(f"{probe.word(1)}.md" in r or "moon.md" in r or "beds.md" in r for r in inside)
    returned = not crumb_row(back) or probe.crumb(1) not in crumb_row(back).split(">")[-1]
    still = (probe.sibling is None or any(probe.sibling[0] in r for r in back)) and any(probe.word(1) in r for r in back)
    return bool(here and returned and still)


def message_to_the_right_agent(cap: Capture, probe: Probe, received: Optional[List[Tuple[str, str, str, float]]] = None) -> Optional[bool]:
    got = {text: who for kind, who, text, _ in (received if received is not None else probe.received) if kind == "steer"}
    right = got.get("MSG-DEEP") == CHAIN.format(probe.depth) and got.get("MSG-ONE") == CHAIN.format(1) and got.get("MSG-MAIN") == ""
    seen = all(text in screen(cap, probe, mark)[0] for text, mark in (("MSG-DEEP", "msg-deep"), ("MSG-ONE", "msg-one"), ("MSG-MAIN", "msg-main")))
    return bool(right and seen)


def stop_only_that_agent(cap: Capture, probe: Probe) -> Optional[bool]:
    stops = [(who, at) for kind, who, _, at in probe.received if kind == "stop"]
    only = [who for who, _ in stops if who] == [CHAIN.format(1)]
    whole = [at for who, at in stops if not who]
    alive = len(whole) == 1 and whole[0] >= probe.marks.get("msg-main", 0.0)      # the only stop of the whole run is the last key
    _, rows = screen(cap, probe, "main3")
    marked = bool(row_with(rows, probe.word(1), "stopped")) and bool(row_with(rows, probe.sibling[0] if probe.sibling else probe.word(1)))
    return bool(only and alive and marked)


def any_depth(cap: Capture, probe: Probe) -> Optional[bool]:
    for level in range(1, probe.depth + 1):
        _, rows = screen(cap, probe, f"in:{level}")
        crumb = crumb_row(rows)
        if not crumb or probe.crumb(level) not in crumb or (level > 1 and "main" not in crumb):
            return False
    return True


def one_key_up(cap: Capture, probe: Probe) -> Optional[bool]:
    for level in range(probe.depth - 1, 0, -1):
        _, rows = screen(cap, probe, f"up:{level}")
        crumb = crumb_row(rows)
        if probe.crumb(level) not in crumb or probe.crumb(level + 1) in crumb:
            return False
    _, rows = screen(cap, probe, "main2")
    return not crumb_row(rows) or probe.crumb(1) not in crumb_row(rows)


def finished_enterable(cap: Capture, probe: Probe) -> Optional[bool]:
    text, rows = screen(cap, probe, "zulu-in")
    if probe.sibling is None:
        return bool(rows) and "moon.md" in text or "beds.md" in text
    return bool(rows) and "RESULT-ZULU" in text and f"{probe.sibling[0]}.md" in text and bool(crumb_row(rows))


def result_once(cap: Capture, probe: Probe) -> Optional[bool]:
    text, rows = screen(cap, probe, "main3")
    if probe.sibling is None:
        return bool(rows) and len(re.findall(r"\bmoon note\b|\bmost interesting\b", text)) <= 3 and "interesting" in text
    return bool(rows) and text.count("RESULT-ZULU") == 1


# --- depth: the screen at depth 4 against depth 1 -------------------------------------------------------------------------------

def measures(cap: Capture, probe: Probe, labels: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """What the screen is like inside the deepest helper: where its content starts, the rows above the breadcrumb and below the key hints, the key labels shown, and how long entering took."""
    _, rows = screen(cap, probe, f"in:{probe.depth}")
    crumb = crumb_row(rows)
    if not rows or not crumb:
        return None
    start = rows.index(crumb)
    body = [r for r in rows[start + 1:] if r.strip()]
    hints = next((r for r in reversed(rows) if labels["stop"] in r and labels["leave"] in r), "")
    indent = min((len(r) - len(r.lstrip()) for r in body[:-1] if r.strip()), default=0)
    after = len(rows) - 1 - rows.index(hints) if hints else None
    entered = [at for name, at in probe.presses.items() if name.startswith("enter@")]
    seen = None
    if len(entered) >= probe.depth:
        pressed = sorted(entered)[probe.depth - 1]
        for snap in cap.snapshots:
            if snap.at >= pressed - cap.begun and probe.crumb(probe.depth) in crumb_row(snap.rows):
                seen = snap.at - (pressed - cap.begun)
                break
    return {"indent": indent, "above": start, "below": after, "labels": {k for k, v in labels.items() if hints and v in hints}, "latency": seen}


def depth_keeps_screen(small: Dict[str, Any], deep: Dict[str, Any]) -> bool:
    """Depth 4 is within the stated tolerance of depth 1 in content indent, header rows, footer rows and key hints."""
    return bool(deep["indent"] - small["indent"] <= TOLERANCE["indent_columns"] and abs(deep["above"] - small["above"]) <= TOLERANCE["chrome_rows"]
                and small["below"] is not None and deep["below"] is not None and abs(deep["below"] - small["below"]) <= TOLERANCE["chrome_rows"]
                and small["labels"] <= deep["labels"] and small["labels"])


def depth_keeps_latency(small: Dict[str, Any], deep: Dict[str, Any]) -> bool:
    if small["latency"] is None or deep["latency"] is None:
        return False
    return bool(deep["latency"] <= max(small["latency"] * TOLERANCE["latency_ratio"], small["latency"] + TOLERANCE["latency_seconds"]))


# --- the scenarios ----------------------------------------------------------------------------------------------------------------

def run_at(arm: Any, depth: int, size: Tuple[int, int], replay: Optional[List[Dict[str, Any]]] = None) -> Tuple[Capture, Probe]:
    import scenarios as S
    keys = ScriptedKeys()
    keys.waits_for_input = False
    harness = NestedHarness(keys, depth, arm, replay=replay)
    cap = S.capture(arm, Kit(harness), keys, size)
    return cap, harness.probe


def hierarchy(arm: Any, depth: int) -> Dict[str, Any]:
    results: Dict[str, List[Optional[bool]]] = {}
    for size in SIZES:
        cap, probe = run_at(arm, depth, size)
        for name, check in (("agents-shown-with-state", listed_with_state), ("agent-view-enter-and-leave", enter_and_leave), ("message-reaches-the-right-agent", message_to_the_right_agent),
                            ("stop-only-that-agent", stop_only_that_agent), ("children-enterable-at-any-depth", any_depth), ("one-key-up-one-level", one_key_up),
                            ("finished-agent-enterable", finished_enterable), ("agent-result-once", result_once)):
            results.setdefault(name, []).append(check(cap, probe))
    return {"checks": {name: C.combine(values) for name, values in results.items()}}


def depth_compare(arm: Any) -> Dict[str, Any]:
    labels = {**DEFAULT_LABELS, **dict(getattr(arm, "agent_labels", None) or {})}
    keeps, quick = [], []
    for size in ((80, 24), (120, 40)):
        cap1, probe1 = run_at(arm, 1, size)
        cap4, probe4 = run_at(arm, 4, size)
        small, deep = measures(cap1, probe1, labels), measures(cap4, probe4, labels)
        keeps.append(bool(small and deep and depth_keeps_screen(small, deep)))
        quick.append(bool(small and deep and depth_keeps_latency(small, deep)))
    return {"checks": {"depth-keeps-the-screen": C.combine(keeps), "depth-keeps-latency": C.combine(quick)}}


def real_agents(arm: Any) -> Dict[str, Any]:
    """The recorded real run (a fast-tier session over made-up garden notes: one helper that read two files, its report, the main session's own answer): the same walk in and out of the helper
    while it works and after it ended, with the real events and the real timing of its figures."""
    events = json.loads((Path(__file__).resolve().parent / "real_agents_run.json").read_text())
    results: Dict[str, List[Optional[bool]]] = {}
    for size in SIZES:
        cap, probe = run_at(arm, 1, size, replay=events)
        probe.tasks = [(NestedHarness.replayed_tasks(events)[0][0], NestedHarness.replayed_tasks(events)[0][1])]
        for name, check in (("agents-shown-with-state", lambda c, p: bool(screen(c, p, "main")[1]) and bool(row_with(screen(c, p, "main")[1], p.crumb(1)[:6], "running"))),
                            ("agent-view-enter-and-leave", lambda c, p: bool(screen(c, p, "in:1")[1]) and p.crumb(1) in crumb_row(screen(c, p, "in:1")[1])
                             and (not crumb_row(screen(c, p, "main2")[1]) or p.crumb(1) not in crumb_row(screen(c, p, "main2")[1]).split(">")[-1])),
                            ("finished-agent-enterable", lambda c, p: bool(screen(c, p, "zulu-in")[1]) and "moon.md" in screen(c, p, "zulu-in")[0] and bool(crumb_row(screen(c, p, "zulu-in")[1]))),
                            ("agent-result-once", lambda c, p: bool(screen(c, p, "main3")[1]) and screen(c, p, "main3")[0].count("Most interesting") + screen(c, p, "main3")[0].count("most interesting") <= 1),
                            ("answer-once", lambda c, p: C.answer_once(c))):
            results.setdefault(name, []).append(check(cap, probe))
    return {"checks": {name: C.combine(values) for name, values in results.items()}}


SCENARIOS: Dict[str, Callable[[Any], Dict[str, Any]]] = {"agents_depth1": lambda arm: hierarchy(arm, 1), "agents_depth2": lambda arm: hierarchy(arm, 2), "agents_depth4": lambda arm: hierarchy(arm, 4),
                                                       "agents_depth_compare": depth_compare, "real_agents": real_agents}
HIERARCHY_CHECKS = ("agents-shown-with-state", "agent-view-enter-and-leave", "message-reaches-the-right-agent", "stop-only-that-agent", "children-enterable-at-any-depth",
                    "one-key-up-one-level", "finished-agent-enterable", "agent-result-once")
SCENARIO_CHECKS = {"agents_depth1": HIERARCHY_CHECKS, "agents_depth2": HIERARCHY_CHECKS, "agents_depth4": HIERARCHY_CHECKS,
                   "agents_depth_compare": ("depth-keeps-the-screen", "depth-keeps-latency"),
                   "real_agents": ("agents-shown-with-state", "agent-view-enter-and-leave", "finished-agent-enterable", "agent-result-once", "answer-once")}
