"""Where a person's keys come from. A key source calls ``press(token, text)`` from its own thread: ``esc``, ``interrupt``, ``line`` (with the text), ``typing``
(the line so far) or ``eof``. ``TtyKeys`` reads a real terminal in cbreak mode with the standard library (Escape alone is told from an arrow key by a
short wait); ``ScriptedKeys`` is for tests and demos, and can react to what appears on screen ("when the question shows, press y")."""
from __future__ import annotations

import os
import select
import sys
import threading
from typing import Any, Callable, List, Optional, Tuple

Press = Callable[[str, str], None]


class ScriptedKeys:
    """Keys sent by a script. ``press`` is callable at any time (from a hook inside a harness); ``when`` presses a key after an event of a type is drawn."""
    waits_for_input = False

    def __init__(self) -> None:
        self.press: Press = lambda token, text="": None
        self.reactions: List[Tuple[str, str, str, int]] = []

    def attach(self, press: Press) -> None:
        self.press = press

    def detach(self) -> None:
        pass

    def when(self, event_type: str, token: str, text: str = "", times: int = 1) -> "ScriptedKeys":
        self.reactions.append((event_type, token, text, times))
        return self

    def react(self, event: Any) -> None:
        for index, (kind, token, text, times) in enumerate(self.reactions):
            if times > 0 and getattr(event, "type", "") == kind:
                self.reactions[index] = (kind, token, text, times - 1)
                self.press(token, text)


class TtyKeys:
    """Reads single keys from a terminal. Enter sends the line, Escape stops, Ctrl-D on an empty line leaves; Ctrl-C stays a signal (the driver handles it)."""
    waits_for_input = True

    def __init__(self, stream: Any = None):
        self.stream = stream or sys.stdin
        self.thread: Optional[threading.Thread] = None
        self.quit = threading.Event()
        self.saved: Any = None

    def attach(self, press: Press) -> None:
        import termios
        import tty
        descriptor = self.stream.fileno()
        self.saved = termios.tcgetattr(descriptor)
        tty.setcbreak(descriptor)
        self.quit.clear()
        self.thread = threading.Thread(target=self.read, args=(descriptor, press), daemon=True)
        self.thread.start()

    def detach(self) -> None:
        self.quit.set()
        if self.saved is not None:
            import termios
            termios.tcsetattr(self.stream.fileno(), termios.TCSADRAIN, self.saved)
            self.saved = None

    def read(self, descriptor: int, press: Press) -> None:
        buffer = ""
        while not self.quit.is_set():
            ready, _, _ = select.select([descriptor], [], [], 0.05)
            if not ready:
                continue
            data = os.read(descriptor, 1)
            if not data:
                press("eof", "")
                return
            char = data.decode("utf-8", errors="ignore")
            if char == "\x1b":
                more, _, _ = select.select([descriptor], [], [], 0.03)
                if more:
                    os.read(descriptor, 8)      # an arrow or other key sequence: not a stop
                    continue
                press("esc", "")
            elif char in ("\r", "\n"):
                press("line", buffer)
                buffer = ""
                press("typing", "")
            elif char in ("\x7f", "\b"):
                buffer = buffer[:-1]
                press("typing", buffer)
            elif char == "\x04":
                if not buffer:
                    press("eof", "")
                    return
            elif char.isprintable():
                buffer += char
                press("typing", buffer)


__all__ = ["Press", "ScriptedKeys", "TtyKeys"]
