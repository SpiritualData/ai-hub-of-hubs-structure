"""The presentation metric for the opencode client arm (``presentation = "external"``): the REAL client's own screen is scored.

For each scenario and each size of the metric, the hub's server (``opencode_server``) is started on the loopback interface over a scripted harness (no model, no network), the installed client is
launched on a pseudo-terminal at that size with the arm's per-run folder (its plugin and settings), its output is replayed through the terminal emulator ``pyte`` (LGPL-3.0, evaluation only), keys are
sent through the pseudo-terminal where the scenario has a person act (approve, refuse, a typed note, stop and resume), and the same checks as every other arm (``checks.py``, weights unchanged) judge
the screen. Two things keep a half-drawn frame out of the judgement: bytes between the client's synchronized-update markers (DEC mode 2026) reach the emulator only when the frame is complete, and a
snapshot is kept only when two consecutive snapshots are identical (a settled frame).

The client is found by the environment variable ``AHOHS_OPENCODE_CLIENT`` (a path or program name), else the path; the interface scored is ``AHOHS_OPENCODE_MODE`` (``full``, the default, or ``inline``);
``AHOHS_OPENCODE_PLUGIN=off`` runs the client alone, without the hub's plugin, to see what the plugin changes.
With no client every check is marked not run. The protocol ceiling column is answered from the client's own screen, with the hub's plugin loaded (what a plugin fixed is the difference between a run
with it and the client alone, recorded in the arm's record)."""
from __future__ import annotations

import fcntl
import os
import pty
import re
import select
import shutil
import signal
import struct
import tempfile
import termios
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import checks as C
from screen import SIZES, Capture, Snapshot, Timed, emulator, row_text, styled_cells

from hubofhubs.the_consciousness.ai_session_experience.opencode_server import client as launch
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.bridge import Bridge
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.server import OpencodeServer
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import delegate, edit, read, report, run, stream_kit, turn, use

PAUSE = 0.5                 # seconds a scripted beat takes: the client needs a settled frame (two identical snapshots) between changes
SECONDS = 60.0
SYNC_ON, SYNC_OFF = b"\x1b[?2026h", b"\x1b[?2026l"
CLIENT_RENDERED = ("each-update-once", "current-step-visible", "no-row-wider-than-the-terminal", "repaints-under-bound", "contrast-4.5", "plain-when-not-a-terminal",
                   "key-hints-present-and-whole", "first-output-within-a-second", "unavailable-control-shown")


def environment() -> Dict[str, str]:
    return {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "TERM": "xterm-256color", "HOME": os.environ.get("HOME", tempfile.gettempdir()), launch.CLIENT_ENV: os.environ.get(launch.CLIENT_ENV, ""),
            launch.MODE_ENV: os.environ.get(launch.MODE_ENV, ""), "AHOHS_OPENCODE_PLUGIN": os.environ.get("AHOHS_OPENCODE_PLUGIN", "")}


def client_path() -> str:
    return launch.find("", environment())


def folder() -> str:
    path = tempfile.mkdtemp(prefix="presentation-")
    Path(path, "a.txt").write_text("alpha\n")
    return path


class Pty:
    """A program on a pseudo-terminal of a given size, its output fed to pyte; it answers the terminal queries the client sends (cursor position, colours, keyboard, mode reports)."""

    def __init__(self, argv: Sequence[str], size: Tuple[int, int], env: Dict[str, str], cwd: str, history: bool) -> None:
        self.width, self.height = size
        self.screen, self.stream = emulator(self.width, self.height)
        self.history = history
        self.held = b""
        self.syncing = False
        self.sync_since = 0.0
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(cwd)
            os.execvpe(argv[0], list(argv), env)
        self.pid, self.fd = pid, fd
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", self.height, self.width, 0, 0))
        self.dead = False

    def answer(self, data: bytes) -> None:
        reply = []
        if b"\x1b[6n" in data:
            reply.append(b"\x1b[1;1R")
        if b"\x1b[c" in data or b"\x1b[0c" in data:
            reply.append(b"\x1b[?62;c")
        if b"\x1b[?u" in data:
            reply.append(b"\x1b[?0u")
        if b"\x1b]10;?" in data:
            reply.append(b"\x1b]10;rgb:ffff/ffff/ffff\x1b\\")
        if b"\x1b]11;?" in data:
            reply.append(b"\x1b]11;rgb:0000/0000/0000\x1b\\")
        for found in re.finditer(rb"\x1b\[\?([0-9;]+)\$p", data):
            reply.append(b"\x1b[?" + found.group(1) + b";2$y")
        if b"\x1b[14t" in data:
            reply.append(b"\x1b[4;%d;%dt" % (self.height * 16, self.width * 8))
        if reply:
            os.write(self.fd, b"".join(reply))

    def feed(self, data: bytes) -> None:
        """Bytes to the emulator, except what lies inside a synchronized update, which goes in when the update ends (a frame is never drawn half way)."""
        self.held += data
        while True:
            if not self.syncing:
                at = self.held.find(SYNC_ON)
                if at < 0:
                    self.stream.feed(self.held.decode("utf-8", "replace"))
                    self.held = b""
                    return
                self.stream.feed(self.held[:at].decode("utf-8", "replace"))
                self.held, self.syncing, self.sync_since = self.held[at + len(SYNC_ON):], True, time.monotonic()
            else:
                at = self.held.find(SYNC_OFF)
                if at < 0:
                    if time.monotonic() - self.sync_since > 0.5:         # an update that never ends is shown anyway after half a second
                        self.stream.feed(self.held.decode("utf-8", "replace"))
                        self.held, self.syncing = b"", False
                    return
                self.stream.feed(self.held[:at].decode("utf-8", "replace"))
                self.held, self.syncing = self.held[at + len(SYNC_OFF):], False

    def pump(self, seconds: float) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            ready, _, _ = select.select([self.fd], [], [], 0.02)
            if not ready:
                if self.syncing:
                    self.feed(b"")
                continue
            try:
                data = os.read(self.fd, 65536)
            except OSError:
                self.dead = True
                return False
            if not data:
                self.dead = True
                return False
            self.answer(data)
            self.feed(data)
        return True

    def send(self, data: bytes) -> None:
        os.write(self.fd, data)

    def rows(self) -> Tuple[str, ...]:
        return tuple(row_text(self.screen.buffer[y], self.width) for y in range(self.height))

    def scrolled(self) -> Tuple[str, ...]:
        return tuple(row_text(line, self.width) for line in self.screen.history.top) if self.history else ()

    def close(self) -> None:
        try:
            os.kill(self.pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            os.waitpid(self.pid, 0)
        except OSError:
            pass
        try:
            os.close(self.fd)
        except OSError:
            pass


def transcript_lines(bridge: Bridge) -> List[str]:
    """The lines the arm wrote (the text it gave the client, before the client wrapped it): what the checks that judge the arm's own words read (``logical_lines``)."""
    lines: List[str] = []
    for message in bridge.store.messages.get(bridge.root, []):
        if message["type"] == "user":
            lines.append(message["text"])
        elif message["type"] == "assistant":
            lines.extend(line for part in message["content"] if part["type"] == "text" for line in part["text"].splitlines())
        elif message["type"] == "synthetic":
            lines.append(message["description"])
    return lines


Reaction = Tuple[Callable[["Capture", str], bool], bytes]


def text_of(cap: Capture, pty_: Pty) -> str:
    return "\n".join(pty_.scrolled() + pty_.rows())


def drive(kit_harness: Any, goal: str, size: Tuple[int, int], reactions: Sequence[Reaction] = (), acting_for: str = "", mode: str = "", limits: Any = None, after_done: Sequence[bytes] = (),
          settle: float = 1.2) -> Capture:
    """One run of the real client at ``size``. ``reactions`` are (condition on the capture so far and the screen text, keys) pairs, each sent once, in order, when its condition holds."""
    mode = mode or launch.mode_of("", environment())
    width, height = size
    cap = Capture("external", width, height)
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.opencode_client_session import OpencodeClientSession
    cap.labels = dict(OpencodeClientSession.screen_labels)       # what the arm declares its screen says (the checks read the fact through these)
    work = folder()
    path = client_path()
    run_dir = launch.prepare_run_folder(mode, plugin=environment()["AHOHS_OPENCODE_PLUGIN"] != "off")
    begun = time.monotonic()
    timed = Timed(kit_harness, cap, begun)
    bridge = Bridge(lambda where: timed, work, acting_for=acting_for, folder_name=mode == "full")
    server = OpencodeServer(bridge).start()
    env = launch.client_environment(environment(), run_dir, server.token, mode)
    term = Pty(launch.client_command(path, server.url, bridge.root, mode, goal), size, env, work, history=mode == "inline")
    done_at = None
    pending = list(reactions)
    last: Optional[Tuple[Tuple[str, ...], Tuple[str, ...]]] = None
    candidate: Optional[Tuple[Tuple[str, ...], Tuple[str, ...]]] = None
    candidate_at = 0.0
    try:
        while time.monotonic() - begun < SECONDS:
            term.pump(0.05)
            now = time.monotonic() - begun
            frame = (term.rows(), term.scrolled())
            if frame == candidate:
                if frame != last:                               # a settled frame: two identical snapshots in a row
                    last = frame
                    cap.snapshots.append(Snapshot(candidate_at, frame[0], frame[1], frame[0], styled_cells(term.screen, width, height)))
            else:
                candidate, candidate_at = frame, now
            if pending and pending[0][0](cap, text_of(cap, term)) and last == frame:
                term.send(pending.pop(0)[1])
            ends = [e for _, e in cap.arrivals if e.type == "finished"]
            if ends and ends[-1].outcome != "stopped" and not bridge.running:        # a stop is not the end of the scenario: the person resumes
                done_at = done_at or now
                if now - done_at > settle and not pending:
                    break
            if term.dead:
                break
        for keys in after_done:
            term.send(keys)
            term.pump(0.5)
        end = (term.rows(), term.scrolled())
        if end != last:                  # the run ended and the screen was left alone for the settle time: what it shows now is the final frame, drawn or not caught between two polls
            cap.snapshots.append(Snapshot(time.monotonic() - begun, end[0], end[1], end[0], styled_cells(term.screen, width, height)))
    finally:
        cap.seconds = time.monotonic() - begun
        cap.requests = list(server.requests)           # what the client asked the server, for a reader of the capture
        cap.client_exited = term.dead
        term.close()
        server.stop()
        shutil.rmtree(run_dir, ignore_errors=True)
    runs = [e for _, e in cap.arrivals if e.type == "run-started"]
    cap.report = SimpleNamespace(runs=runs, text="\n".join(transcript_lines(bridge)), view=bridge.translator.view, final=bridge.translator.view.final)
    cap.wide_rows = 0                    # a pseudo-terminal row cannot be wider than the terminal: the client wraps or cuts, and what it cut is judged by the checks that read the rows
    return cap


# --- the scenarios ---------------------------------------------------------------------------------------------------------------------------------------------------------

def shown(*words: str) -> Callable[[Capture, str], bool]:
    return lambda cap, text: all(w.lower() in text.lower() for w in words)


def event_seen(kind: str, **fields: Any) -> Callable[[Capture, str], bool]:
    return lambda cap, text: any(e.type == kind and all(getattr(e, k, None) == v for k, v in fields.items()) for _, e in cap.arrivals)


def over_sizes(build: Callable[[Tuple[int, int]], Capture]) -> List[Capture]:
    """One run per size, one after the other: the client's first frame is timed (first output within a second), and clients started side by side slow each other's start."""
    return [build(size) for size in SIZES]


def over(caps: Sequence[Capture], check: Callable[[Capture], Optional[bool]]) -> Optional[bool]:
    return C.combine([check(c) for c in caps])


def rendering(caps: Sequence[Capture]) -> Dict[str, Optional[bool]]:
    return {"each-update-once": over(caps, C.each_update_once), "no-row-wider-than-the-terminal": over(caps, C.no_row_wider_than_the_terminal),
            "repaints-under-bound": over(caps, C.repaints_under_bound), "contrast-4.5": over(caps, C.contrast_ok)}


def watch() -> Dict[str, Any]:
    def build(size: Tuple[int, int]) -> Capture:
        kit = stream_kit(folder(), [turn(read("a.txt")), turn(edit("b.txt")), turn(delegate("write the tests", turn(edit("tests.txt"), report("tests done")))), turn(run("echo hi")), turn(report("All done."))], pause=PAUSE)
        return drive(kit.harness, "do the work", size)
    caps = over_sizes(build)
    return {"checks": {**rendering(caps), "current-step-visible": over(caps, C.current_step_visible), "closing-report-complete": over(caps, C.closing_report_complete),
                       "first-output-within-a-second": over(caps, C.first_output), "key-hints-present-and-whole": C.key_hints(caps)}, "ceiling": ceilings()}


def ceilings() -> Dict[str, bool]:
    """What the hub can show that a protocol may not carry, read from the client's own screen at the metric's largest size with the plugin loaded, and the one thing no key reaches."""
    size = max(SIZES)
    kit = stream_kit(folder(), [turn(read("a.txt")), turn(delegate("write the tests", turn(edit("t.txt"), report("ok")))), turn(edit("b.txt")), turn(report("Done."))], pause=PAUSE, limits=(5.0, 1800.0))
    cap = drive(kit.harness, "do the work", size, [(event_seen("agent-started"), b"/structure"), (shown("/structure"), b"\r")], acting_for="Alex", after_done=())
    text = cap.all_text()
    return {"structure-on-request": "structure" in text.lower() and bool(re.search(r"structure \(|Tab hides", text)), "spend-against-ceilings": "of $5.00" in text and "of 30:00" in text,
            "who-the-ai-acts-for": "for Alex" in text, "stop-one-helper": False}


def steer() -> Dict[str, Any]:
    def build(size: Tuple[int, int]) -> Capture:
        kit = stream_kit(folder(), [turn(read("a.txt")), turn(edit("b.txt")), turn(edit("c.txt"), report("Done."))], pause=PAUSE * 4)       # slow enough that the note stays "sent" for a few settled frames before the run takes it up
        return drive(kit.harness, "do the work", size, [(event_seen("step", state="running"), b"use the short name"), (shown("use the short name"), b"\r")])
    caps = over_sizes(build)
    return {"checks": {"correction-sent-then-taken-up": over(caps, C.correction_sent_then_taken_up),
                       "round-trip-steer": over(caps, lambda c: C.round_trip(c, "steer", r"you: use the short name|use the short name", "use the short name"))},
            "ceiling": {"correction-taken-up": bool(over(caps, C.correction_sent_then_taken_up))}}


def stop_resume() -> Dict[str, Any]:
    def build(size: Tuple[int, int]) -> Capture:
        kit = stream_kit(folder(), [turn(edit("one.txt")), turn(edit("two.txt")), turn(edit("three.txt"), report("All three."))], pause=PAUSE * 2)
        started = event_seen("step", label="one.txt")           # the step is the trigger, not its words on the screen (the inline client draws an edit without its file name)
        return drive(kit.harness, "do the work", size, [(started, b"\x1b"), (started, b"\x1b"), (event_seen("finished", outcome="stopped"), b"resume"), (shown("resume"), b"\r")], settle=2.0)
    caps = over_sizes(build)
    return {"checks": {"stop-then-resume-keeps-work": over(caps, C.stop_then_resume_keeps_work), "round-trip-stop": over(caps, lambda c: C.round_trip(c, "stop", r"stopp|type resume|resume to continue")),
                       "round-trip-resume": over(caps, lambda c: C.combine([bool(c.report and sum(1 for _, e in c.arrivals if e.type == "run-started") >= 2 and "resum" in c.all_text().lower())])),
                       "closing-report-complete": over(caps, C.closing_report_complete)}}


def approval(answer: bytes) -> Dict[str, Any]:
    def build(size: Tuple[int, int]) -> Capture:
        kit = stream_kit(folder(), [turn(use("deploy", "release 1.0")), turn(report("Finished."))], pause=0.0)
        inline = launch.mode_of("", environment()) == "inline"
        reactions: List[Reaction] = [(event_seen("waiting") if inline else shown("Allow once"), answer)]
        if inline and answer != b"\r":          # the inline client's Esc opens a "Reject permission" message prompt: Enter confirms the refusal
            reactions.append((shown("Reject permission"), b"\r"))
        return drive(kit.harness, "do the work", size, reactions)
    caps = over_sizes(build)
    word = "approve" if answer == b"\r" else "refuse"
    shown_ = r"deploy" if word == "approve" else r"refus|blocked|reject"
    return {"checks": {"risky-step-waits-with-preview": over(caps, C.risky_step_waits_with_preview), f"round-trip-{word}": over(caps, lambda c: C.round_trip(c, word, shown_))}}


def target() -> Dict[str, Any]:
    """Stopping one helper: the client has no key that reaches a helper, so no such control can be sent; nothing on its screen offers it either."""
    return {"checks": {"unavailable-control-shown": None}, "ceiling": {"stop-one-helper": False}, "not_run": ["unavailable-control-shown"],
            "note": "the client has no control that names one helper, so none could be sent"}


def pasted_run() -> Dict[str, Any]:
    import pasted
    caps = over_sizes(lambda size: drive(pasted.PastedRun(PAUSE), pasted.GOAL, size))
    import scenarios
    return {"checks": {**scenarios.revision_2(caps), "closing-report-complete": over(caps, C.closing_report_complete), "no-row-wider-than-the-terminal": over(caps, C.no_row_wider_than_the_terminal)}}


def real_run() -> Dict[str, Any]:
    """The recorded events of a real native run (``real_native_run.json``) drawn by the client: the answer is on the screen once."""
    import real_run as recorded
    caps = over_sizes(lambda size: drive(recorded.RealRun(PAUSE), recorded.GOAL, size))
    return {"checks": {"answer-once": over(caps, C.answer_once), "no-raw-markdown": over(caps, C.no_raw_markdown), "closing-report-complete": over(caps, C.closing_report_complete),
                       "no-row-wider-than-the-terminal": over(caps, C.no_row_wider_than_the_terminal)}}


def plain() -> Dict[str, Any]:
    import scenarios
    return scenarios.plain(SimpleNamespace(attend=_plain_attend))


def _plain_attend(*args: Any, **kwargs: Any) -> Any:
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession
    return LiveSession().attend(*args, **kwargs)


SCENARIOS = {"watch": watch, "steer": steer, "stop_resume": stop_resume, "approve": lambda: approval(b"\r"), "refuse": lambda: approval(b"\x1b"), "target": target, "plain": plain,
             "pasted_run": pasted_run, "real_run": real_run}


def run_scenario(name: str) -> Dict[str, Any]:
    """The scenario's result from the real client's screen; every check is marked not run when the client is not installed."""
    import agents_scenarios as hierarchy
    import feed_scenarios as feed
    if name in hierarchy.SCENARIO_CHECKS:
        return {"checks": {}, "ceiling": {}, "not_run": list(hierarchy.SCENARIO_CHECKS[name]), "note": hierarchy.NOT_DRIVEN}
    if name in feed.SCENARIO_CHECKS:
        return {"checks": {}, "ceiling": {}, "not_run": list(feed.SCENARIO_CHECKS[name]), "note": feed.NOT_DRIVEN}
    if not client_path():
        return {"checks": {}, "ceiling": {}, "not_run": sorted(C.REQUIREMENTS), "note": launch.unavailable("", environment()) or "the client is not installed"}
    if name not in SCENARIOS:
        return {"checks": {}, "ceiling": {}}
    # one whole run, thrown away, before the first scenario is timed: a client not used for a while is read from disk on its first start (up to two seconds), and first output is judged on a warm start
    drive(stream_kit(folder(), [turn(report("warm"))], pause=0.0).harness, "warm", min(SIZES))
    done = dict(SCENARIOS[name]())
    done["note"] = done.get("note") or f"the real client drew these screens ({launch.mode_of('', environment())} interface)"
    return done
