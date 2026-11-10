"""The real-entry stage of Terminal Session: each arm is driven the way a person uses it, through ``ahohs work`` on a real pseudo-terminal (python ``pty``), with a real
fast-tier session on the Claude CLI subscription login. Nothing is scripted but the person's keys: the scenario types, presses Escape or Tab and reads the screen exactly as a
person would, and a check passes only when the files, the exit code and the text on that screen show it. A key is sent when a file appears in the folder (not when a screen
word appears), because a full-screen application repaints in pieces.

Scenarios (one real session each): ``complete`` (a run to its end and the closing report), ``escape_resume`` (Escape stops and keeps the work, resume finishes every step once),
``steer`` (a message typed during the run is shown and acted on), ``structure`` (a helper is drawn, the structure opens on Tab, the helper's file counts as changed),
``follow_up`` (a line after a run continues the same session), ``harness_switch`` (``/harness`` and a run on the other harness), ``refused`` (a command the permission mode
refuses shows its reason), ``markdown`` (a long markdown answer is rendered, not shown with its marks). The line REPL has no keys, so a scenario that needs one is run until it
ends by itself and fails on what the person could not do.

    python3 -m esoi run terminal_session --impl <arm> --max-calls 200

Standard library only; needs the Claude CLI login (``claude`` on the PATH) and the hub on the path of the process."""
from __future__ import annotations

import fcntl
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

ANSI = re.compile(r"\x1b\[[0-9;?<>=]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[()][A-Z0-9]|\x1b[=>78]")
ARM_NAMES = {"LiveSession": "live_session", "TextualSession": "textual_session", "LineRepl": "line_repl"}
SLOTS = threading.Semaphore(2)       # never more than two model sessions at once
ROOT = Path(__file__).resolve().parents[2]


class Screen:
    """One ``ahohs work`` process on a pseudo-terminal: what it printed (as raw bytes and with escape codes removed) and the keys sent to it."""

    def __init__(self, arm: str, folder: str, goal: str = "", extra: Optional[List[str]] = None, columns: int = 120, rows: int = 40):
        self.folder, self.raw, self.began = folder, b"", time.monotonic()
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        env = {"HOME": os.environ.get("HOME", ""), "PATH": os.environ.get("PATH", ""), "TERM": "xterm-256color", "LANG": "C.UTF-8", "COLUMNS": str(columns), "LINES": str(rows),
               "PYTHONPATH": os.pathsep.join([str(ROOT), str(ROOT.parent / "evolvable-structure" / "implementations" / "python")]), "PYTHONUNBUFFERED": "1"}
        argv = [sys.executable, "-m", "hubofhubs.the_self.assembler.cli", "work", "--terminal", arm, "--harness", "stream", "--tier", "fast", "--folder", folder,
                "--max-spend", "2", "--max-time", "8m", *(extra or []), *([goal] if goal else [])]

        def controlling() -> None:
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        self.process = subprocess.Popen(argv, stdin=slave, stdout=slave, stderr=slave, cwd=folder, env=env, preexec_fn=controlling, close_fds=True)
        os.close(slave)
        self.master = master
        self.lock = threading.Lock()
        threading.Thread(target=self.pump, daemon=True).start()

    def pump(self) -> None:
        while True:
            try:
                ready, _, _ = select.select([self.master], [], [], 0.1)
                if ready:
                    data = os.read(self.master, 65536)
                    if not data:
                        return
                    with self.lock:
                        self.raw += data
                elif self.process.poll() is not None:
                    return
            except OSError:
                return

    def text(self) -> str:
        with self.lock:
            return ANSI.sub("", self.raw.decode("utf-8", errors="replace")).replace("\r", "")

    def send(self, keys: str) -> None:
        try:
            os.write(self.master, keys.encode())
        except OSError:
            pass

    def line(self, text: str) -> None:
        self.send(text)
        time.sleep(0.15)
        self.send("\r")

    def wait_file(self, name: str, seconds: float = 150.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if Path(self.folder, name).exists():
                return True
            if self.process.poll() is not None:
                return Path(self.folder, name).exists()
            time.sleep(0.2)
        return False

    def wait_text(self, pattern: str, seconds: float = 150.0) -> bool:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if re.search(pattern, self.text()):
                return True
            if self.process.poll() is not None:
                return bool(re.search(pattern, self.text()))
            time.sleep(0.2)
        return False

    def worker_alive(self) -> bool:
        """True while the model worker (the Claude CLI) is running below the ahohs process: the objective sign that a run is going, whatever the screen shows."""
        parent: Dict[int, int] = {}
        names: Dict[int, str] = {}
        for entry in Path("/proc").iterdir():
            if entry.name.isdigit():
                try:
                    stat = (entry / "stat").read_text()
                    parent[int(entry.name)] = int(stat.rsplit(")", 1)[1].split()[1])
                    names[int(entry.name)] = stat[stat.index("(") + 1:stat.rindex(")")]
                except (OSError, ValueError, IndexError):
                    continue
        for pid, name in names.items():
            if "claude" not in name:
                continue
            up = pid
            for _ in range(12):
                up = parent.get(up, 0)
                if up == self.process.pid:
                    return True
        return False

    def idle(self, seconds: float = 3.0, cap: float = 240.0, start: float = 60.0) -> None:
        """Wait until a run has started and its worker has been gone for ``seconds`` (the run ended and the prompt waits), the process exits, or ``cap`` runs out. A screen that
        repaints a blinking cursor never goes quiet, so the worker's own presence is what tells a run is over."""
        end, seen, gone = time.monotonic() + cap, False, None
        began = time.monotonic()
        while time.monotonic() < end and self.process.poll() is None:
            alive = self.worker_alive()
            seen = seen or alive
            if alive:
                gone = None
            elif seen or time.monotonic() - began > start:
                gone = gone or time.monotonic()
                if time.monotonic() - gone >= seconds:
                    return
            time.sleep(0.4)

    def leave(self) -> int:
        """Ctrl-D at the prompt, then wait for the process; a process that does not leave is ended."""
        for _ in range(3):
            self.send("\x04")
            time.sleep(0.5)
        try:
            code = self.process.wait(timeout=20)
        except subprocess.TimeoutExpired:
            os.killpg(self.process.pid, signal.SIGTERM)
            try:
                code = self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                code = -9
        time.sleep(0.3)
        return code

    def close(self) -> None:
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except OSError:
                pass
        try:
            os.close(self.master)
        except OSError:
            pass


def folder_with(files: Dict[str, str]) -> str:
    path = tempfile.mkdtemp(prefix="pty-session-")
    for name, text in files.items():
        Path(path, name).write_text(text)
    return path


def complete(arm: str, meter) -> List[str]:
    folder = folder_with({"a.txt": "alpha\n"})
    screen = Screen(arm, folder, "Read a.txt, then create b.txt containing the word beta, then reply with one short sentence.")
    failed = []
    try:
        screen.wait_file("b.txt")
        screen.idle()
        code = screen.leave()
        shown = screen.text()
        if not Path(folder, "b.txt").exists():
            failed.append("work-done")
        if "a.txt" not in shown or "b.txt" not in shown:
            failed.append("steps-shown-by-name")
        if "Changed (1): b.txt" not in shown:
            failed.append("closing-report-names-the-file")
        if "To continue later" not in shown:
            failed.append("resume-command-named")
        if code != 0:
            failed.append("exit-code-zero")
    finally:
        screen.close()
    return failed


def escape_resume(arm: str, meter) -> List[str]:
    folder = folder_with({})
    goal = "Create the 25 files n1.txt to n25.txt, one at a time with a separate Write call each, each containing its own number. Then reply done."
    screen = Screen(arm, folder, goal)
    failed = []
    try:
        screen.wait_file("n2.txt")
        screen.send("\x1b")
        screen.idle(cap=60, start=20)       # the run ends at the stop
        have = len(list(Path(folder).glob("n*.txt")))
        if have >= 25:
            failed.append("stop-came-before-the-end")
        screen.line("resume")
        screen.wait_file("n25.txt", 240)
        screen.idle(start=30)
        if len(list(Path(folder).glob("n*.txt"))) != 25:
            failed.append("resume-finishes-all-files")
        screen.leave()
        shown = screen.text()
        if not re.search(r"Stopped: your work is kept|stopped", shown):
            failed.append("stop-shown")
        if "goal was met" not in shown:
            failed.append("resumed-run-ends-met")
    finally:
        screen.close()
    return failed


def steer(arm: str, meter) -> List[str]:
    folder = folder_with({})
    screen = Screen(arm, folder, "Create one.txt, then two.txt, then three.txt, one at a time with separate Write calls, each containing its own name. Then reply done.")
    failed = []
    try:
        screen.wait_file("one.txt")
        screen.line("also create four.txt containing four")
        screen.wait_file("three.txt", 200)
        screen.idle()
        screen.leave()
        shown = screen.text()       # read after the screen closes: a full-screen arm prints its transcript on the way out
        if "also create four" not in shown:
            failed.append("message-shown-as-sent")
        if not ("queued" in shown or "taken up" in shown):
            failed.append("queued-or-taken-up-said")
        if not Path(folder, "four.txt").exists():
            failed.append("message-acted-on")
    finally:
        screen.close()
    return failed


def structure(arm: str, meter) -> List[str]:
    folder = folder_with({})
    goal = "Use the Task tool to start one helper whose description begins with [tests] and that writes h.txt containing the word helper. Wait for it. Then reply done."
    screen = Screen(arm, folder, goal, extra=["--solution", "tests", "--milestone", "tests exist"])
    failed = []
    try:
        time.sleep(7)
        screen.send("\t")
        screen.wait_file("h.txt", 200)
        screen.idle()
        screen.leave()
        shown = screen.text()       # read after the screen closes: a full-screen arm prints its transcript on the way out
        if "structure" not in shown:
            failed.append("structure-opens-on-tab")
        if "(tests)" not in shown:
            failed.append("helper-named-by-solution")
        if "Changed (1): h.txt" not in shown and "h.txt" not in shown.split("Changed")[-1]:
            failed.append("helper-file-counts-as-changed")
        if "goal was met" in shown and "still running" in shown:
            failed.append("not-met-while-helper-runs")
    finally:
        screen.close()
    return failed


def follow_up(arm: str, meter) -> List[str]:
    folder = folder_with({})
    screen = Screen(arm, folder, "Create b.txt containing beta, then reply done.")
    failed = []
    try:
        screen.wait_file("b.txt")
        screen.idle()
        screen.line("now also create c.txt containing gamma, then reply done")
        screen.wait_file("c.txt", 200)
        screen.idle(cap=120)
        screen.leave()
        shown = screen.text()       # read after the screen closes: a full-screen arm prints its transcript on the way out
        if not Path(folder, "c.txt").exists():
            failed.append("follow-up-runs")
        if "resumed" not in shown and shown.count("To continue later") < 2:
            failed.append("same-session-continued")
    finally:
        screen.close()
    return failed


def harness_switch(arm: str, meter) -> List[str]:
    folder = folder_with({})
    screen = Screen(arm, folder, "")
    failed = []
    try:
        time.sleep(4)
        screen.line("/harness native")
        time.sleep(3)
        screen.line("Create n.txt containing native, then reply done.")
        screen.wait_file("n.txt", 240)
        screen.idle(cap=120)
        screen.leave()
        shown = screen.text()       # read after the screen closes: a full-screen arm prints its transcript on the way out
        if "harness is now native" not in shown:
            failed.append("switch-said")
        if not Path(folder, "n.txt").exists():
            failed.append("run-on-the-new-harness")
    finally:
        screen.close()
    return failed


def refused(arm: str, meter) -> List[str]:
    folder = folder_with({})
    screen = Screen(arm, folder, "Use the Bash tool to run exactly: echo hi > x.txt . Then tell me in one sentence what happened.")
    failed = []
    try:
        screen.idle(cap=150)
        screen.leave()
        shown = screen.text()
        if Path(folder, "x.txt").exists():
            failed.append("command-really-refused")
        if "Blocked or refused" not in shown:
            failed.append("refusals-listed")
        if not re.search(r"(?i)permission|refused:|not allowed|haven.t granted|approval", shown.split("Blocked or refused")[-1] if "Blocked or refused" in shown else shown):
            failed.append("reason-shown")
    finally:
        screen.close()
    return failed


def markdown(arm: str, meter) -> List[str]:
    folder = folder_with({})
    screen = Screen(arm, folder, "Without using any tool, answer in markdown with a '## ' heading, a bullet list, a numbered list, bold text and a fenced code block: two ways to sort a list in Python, 30 lines in all.")
    failed = []
    try:
        screen.idle(cap=150)
        screen.leave()
        shown = screen.text()
        tail = shown.split("Done: the goal was met")[-1] if "Done: the goal was met" in shown else shown
        if "Done: the goal was met" not in shown and "goal was met" not in shown:
            failed.append("answer-reported")
        if re.search(r"\*\*\w|^```|^## ", tail, re.M):
            failed.append("markdown-rendered-not-raw")
    finally:
        screen.close()
    return failed


def history(arm: str, meter) -> List[str]:
    """Up recalls the line typed before (every reviewed terminal keeps a history): the same goal is run again with two keys."""
    folder = folder_with({})
    screen = Screen(arm, folder, "")
    failed = []
    try:
        time.sleep(4)
        screen.line("Read log.txt if it exists, then write log.txt back with one more line containing the word ran at the end (create it if missing). Reply done.")
        screen.wait_file("log.txt")
        screen.idle()
        screen.send("\x1b[A")
        time.sleep(1.5)
        screen.send("\r")
        time.sleep(3)
        screen.idle(start=30)
        screen.leave()
        text = Path(folder, "log.txt").read_text() if Path(folder, "log.txt").exists() else ""
        if text.count("ran") < 2:
            failed.append("up-recalls-the-previous-line")
    finally:
        screen.close()
    return failed


SCENARIOS: Dict[str, Callable] = {"history": history, "complete": complete, "escape_resume": escape_resume, "steer": steer, "structure": structure, "follow_up": follow_up,
                                  "harness_switch": harness_switch, "refused": refused, "markdown": markdown}


def run_pty_case(implementation, scenario: str, meter=None) -> List[str]:
    """The failed checks of one scenario on one arm (an empty list is right). One real fast-tier session, started only when a slot is free."""
    arm = ARM_NAMES.get(getattr(implementation, "__name__", ""), str(implementation))
    with SLOTS:
        began = time.monotonic()
        try:
            failed = SCENARIOS[scenario](arm, meter)
        except Exception as error:  # noqa: BLE001 -- an arm that cannot be driven fails the scenario
            failed = [f"raised {type(error).__name__}: {error}"]
        if meter is not None:
            meter.record()
        return failed
