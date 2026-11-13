"""Running the full-screen client on the person's terminal and leaving its own closing text out of the scrollback. When the client exits it prints a "Continue  opencode -s <id>" box
after it leaves the alternate screen; that is the client's own resume command, and the program that hosts the session has its own (``qar --resume <id>``), so the box would show a command that
reopens the wrong thing. The client runs on a pseudo-terminal this module relays byte for byte (input, output, window size), except that once the client has left the alternate screen only its
terminal-control sequences are passed on (the cursor and colours are restored) and the first printed text after them is dropped. Standard library only; with no terminal on this side the client
simply runs as a child process."""
from __future__ import annotations

import fcntl
import os
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import tty
from typing import Mapping, Sequence

LEAVE_SCREEN = b"\x1b[?1049l"


class ExitTextFilter:
    """Passes the client's output through, and after the client leaves the alternate screen drops everything from its first printed character on (control sequences before it still pass)."""

    def __init__(self) -> None:
        self.tail = b""
        self.left = False                # the client has left the alternate screen
        self.dropping = False
        self.state = "text"              # text, escape, csi, osc, osc_escape (inside a control sequence)

    def feed(self, data: bytes) -> bytes:
        out = bytearray()
        for byte in data:
            if self.dropping:
                continue
            if not self.left:
                out.append(byte)
                self.tail = (self.tail + bytes([byte]))[-len(LEAVE_SCREEN):]
                if self.tail == LEAVE_SCREEN:
                    self.left, self.state = True, "text"
                continue
            if self.state == "text":
                if byte == 0x1B:
                    self.state = "escape"
                    out.append(byte)
                else:
                    self.dropping = True
            elif self.state == "escape":
                out.append(byte)
                self.state = "csi" if byte == 0x5B else "osc" if byte == 0x5D else "text"
            elif self.state == "csi":
                out.append(byte)
                if 0x40 <= byte <= 0x7E:
                    self.state = "text"
            elif self.state == "osc":
                out.append(byte)
                if byte == 0x07:
                    self.state = "text"
                elif byte == 0x1B:
                    self.state = "osc_escape"
            else:                         # osc_escape: the string ends with ESC followed by a backslash
                out.append(byte)
                self.state = "text"
        return bytes(out)


def on_terminal() -> bool:
    return sys.stdin.isatty() and sys.stdout.isatty()


def copy_window_size(source: int, target: int) -> None:
    try:
        fcntl.ioctl(target, termios.TIOCSWINSZ, fcntl.ioctl(source, termios.TIOCGWINSZ, struct.pack("HHHH", 0, 0, 0, 0)))
    except OSError:
        pass


def run_full_screen(invocation: Sequence[str], cwd: str, env: Mapping[str, str]) -> int:
    """Run the client on this terminal and return its exit code, without the client's own closing text. Without a terminal on this side it is an ordinary child process."""
    if not on_terminal():
        return subprocess.run(list(invocation), cwd=cwd, env=dict(env), check=False).returncode
    child, master = pty.fork()
    if child == 0:                       # the client's side: its own terminal, this folder, this environment
        try:
            os.chdir(cwd)
            os.execvpe(invocation[0], list(invocation), dict(env))
        finally:
            os._exit(127)
    stdin, stdout = sys.stdin.fileno(), sys.stdout.fileno()
    saved = termios.tcgetattr(stdin)
    previous = signal.getsignal(signal.SIGWINCH)
    copy_window_size(stdout, master)
    signal.signal(signal.SIGWINCH, lambda *_: (copy_window_size(stdout, master), os.kill(child, signal.SIGWINCH)))
    filtered = ExitTextFilter()
    status = 0
    try:
        tty.setraw(stdin)
        reading = True
        while True:
            ready, _, _ = select.select([master] + ([stdin] if reading else []), [], [], 0.5)
            if stdin in ready:
                data = os.read(stdin, 65536)
                if data:
                    os.write(master, data)
                else:
                    reading = False
            if master in ready:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    break
                if not data:
                    break
                shown = filtered.feed(data)
                if shown:
                    os.write(stdout, shown)
    finally:
        termios.tcsetattr(stdin, termios.TCSADRAIN, saved)
        signal.signal(signal.SIGWINCH, previous)
        try:
            os.close(master)
        except OSError:
            pass
        try:
            _, status = os.waitpid(child, 0)
        except ChildProcessError:
            status = 0
    return os.waitstatus_to_exitcode(status) if status else 0


__all__ = ["ExitTextFilter", "run_full_screen"]
