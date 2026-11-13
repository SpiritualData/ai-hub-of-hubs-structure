"""The reference experience of working with the AI while it works: one driver for any ``Harness``, drawn in a terminal with the standard library only.

``LiveSession().attend(harness, goal, out, keys)`` runs the goal on the harness in its own thread and, in the calling thread, draws the events and takes
the person's keys: Escape or Ctrl-C stops the run at once and keeps the session, ``resume`` continues it, a typed line is sent as steering and shown
as sent, then as taken up, ``y`` and ``n`` answer a question, ``@name text`` steers and ``/stop name`` stops one helper. On a terminal the screen is
redrawn in place; anywhere else (a pipe, a file) it is plain appended lines with no escape codes. The harness is anything that satisfies
``session_events.Harness``; see ``session_harnesses`` for the hub loop and the stream runner.

Run it: ``python -m hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live --help``; ``--demo loop`` or ``--demo stream`` runs a scripted session with no model.
"""
from __future__ import annotations

import argparse
import queue
import shutil
import sys
import threading
import time
import uuid
from dataclasses import replace
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, TextIO, Tuple

from esoi import implementation

from hubofhubs.the_consciousness.ai_session_experience.structure_in_view.tree import flatten, structure_view, tables_of
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import agent_focus, hub_lines, present
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.repl import LineRepl
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.structure_lines import structure_lines
from hubofhubs.the_consciousness.ai_session_experience.session_events import (
    Approve, Control, Finished, Harness, Refuse, SessionEvent, Step, Steer, Stop, Waiting, short)
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import HELP_ROWS, SessionReport, SessionView, clip, event_line, frame, plain_event, report

MAX_RESUMES = 8
REDRAW_SECONDS = 0.1


class Painter:
    """Draws a block of lines and replaces it in place on a terminal; on anything else it only appends."""

    def __init__(self, out: TextIO, live: bool, width: int):
        self.out, self.live, self.width, self.height = out, live, width, 0

    def fit(self, lines: List[str]) -> List[str]:
        """The rows as the screen will show them: none wider than the terminal now and none more than fit, or the cursor-up that erases the old block would count wrong and the
        old block would stay above the new one (the same lines twice, one frame apart). A block too tall keeps its two head rows and its tail (the keys and the input line)."""
        size = shutil.get_terminal_size((self.width, 24))
        wide = max(min(self.width, size.columns) - 1, 20)
        rows = [clip(line, wide) for line in lines]
        room = max(size.lines - 1, 6)
        if len(rows) > room:
            rows = rows[:2] + rows[len(rows) - (room - 2):]
        return rows

    def draw(self, lines: List[str]) -> None:
        if not self.live:
            return
        lines = self.fit(lines)
        self.erase()
        self.out.write("\n".join(lines) + "\n")
        self.height = len(lines)
        self.out.flush()

    def erase(self) -> None:
        if self.live and self.height:
            self.out.write(f"\x1b[{self.height}A\r\x1b[J")
            self.height = 0

    def line(self, text: str) -> None:
        if text:
            self.erase()
            self.out.write(text + "\n")
            self.out.flush()


class Attendance:
    """One attended session: the events in, the keys in, the controls out."""

    panel = False       # True when a live panel is drawn beside a scrolling transcript (the full-screen arm): the transcript then holds only what finished, the panel only what is happening now

    def __init__(self, harness: Harness, goal: str, out: TextIO, keys: Any, clock: Callable[[], float], tick: float, live: bool, width: int, *,
                 records: Any = None, commands: Optional[Mapping[str, Callable[[str], Optional[str]]]] = None,
                 segments: Sequence[Callable[[SessionView], str]] = (), panels: Sequence[Callable[[SessionView], List[str]]] = (), command: str = "",
                 representative: Optional[Mapping[str, Any]] = None, stop_limits: Optional[Mapping[str, Any]] = None):
        self.harness, self.goal, self.out, self.keys, self.clock, self.tick = harness, goal, out, keys, clock, tick
        self.records, self.loaded = records, None
        self.commands_extra = {name.lstrip("/").lower(): fn for name, fn in (commands or {}).items()}
        self.segments, self.panels = list(segments), list(panels)
        self.shape: Tuple[Any, ...] = ()
        self.nodes: List[str] = []
        self.live = live
        self.painter = Painter(out, live, width)
        self.width = width
        self.view = SessionView()
        if command:
            self.view.command = command
        self.view.authority = hub_lines.authority_lines(representative, stop_limits)
        self.view.acting_for = str((representative or {}).get("person") or "")
        self.view.started = self.view.now = clock()
        self.inbox: "queue.Queue[Tuple[Any, ...]]" = queue.Queue()
        self.commands: "queue.Queue[str]" = queue.Queue()
        self.events: List[SessionEvent] = []
        self.controls: List[Tuple[Control, bool]] = []
        self.runs: List[Finished] = []
        self.unsent: List[Steer] = []
        self.stop_wanted = False
        self.running = False
        self.asking = ""
        self.pending_nav = 0           # navigation keys pressed and not yet taken in the main thread
        self.lock = threading.Lock()

    # --- keys, from any thread ----------------------------------------------------------------------------------------------------

    def send(self, control: Control) -> bool:
        ok = bool(self.harness.control(control))
        with self.lock:
            self.controls.append((control, ok))
        self.inbox.put(("control", control, ok))
        return ok

    def agent_keys(self, token: str) -> bool:
        """Up, Down, Right and Left walk the agents (``agent_focus``) when the structure tree is not open and there is a helper to pick or a helper in view. Taken in the main thread, in the
        order the keys were pressed (a Right followed by Escape stops the agent that Right went into). True when the key was taken."""
        view = self.view
        focus = view.focus
        if view.show_structure or token not in ("up", "down", "open", "close"):
            return False
        if not focus.path and not agent_focus.children(view, agent_focus.MAIN):
            return False
        if token in ("up", "down"):
            agent_focus.move(view, focus, 1 if token == "down" else -1)
        elif token == "open":
            said = agent_focus.enter(view, focus)
            if said:
                view.notice(said)
                return True
            self.looked()
        elif agent_focus.leave(focus):
            self.looked()
        return True

    def looked(self) -> None:
        """Where the person is now, said once when the screen cannot show it (plain lines)."""
        self.inbox.put(("looking", agent_focus.breadcrumb(self.view, self.view.focus, 80)))

    def stop_here(self) -> None:
        """Escape: the agent in view is stopped and no other; at the main session the whole run is, and the session is kept."""
        if not self.running:
            return
        if self.view.focus.path:
            who = agent_focus.targets(self.view.focus)
            agent = self.view.agents.get(who)
            if agent is not None and agent.state != "running":
                self.inbox.put(("notice", "That helper has finished; go back with Left to stop the run."))
            elif not self.send(agent_focus.stop_for(self.view.focus)):
                self.inbox.put(("notice", "This harness cannot stop one agent; go back to the top and use Escape to stop the whole run."))
            return
        self.stop_wanted = True
        self.send(Stop())

    def press(self, token: str, text: str = "") -> None:
        if token == "focus":        # a screen that has its own list of helpers says which one the person chose ("" is the main session)
            self.pending_nav += 1
            self.inbox.put(("nav", "focus", text))
            return
        if token in ("up", "down", "open", "close"):
            self.pending_nav += 1
            self.inbox.put(("nav", token, text))
            return
        if token in ("esc", "interrupt"):
            if token == "esc" and (self.view.focus.path or self.pending_nav):      # in a helper, or right after a key that may have moved there: in the order the keys came
                self.inbox.put(("esc",))
            elif self.running:
                self.stop_wanted = True
                self.send(Stop())
            return
        if token == "typing":
            self.inbox.put(("typing", text))
            return
        if token in ("tree", "help", "who"):
            self.inbox.put(("key", token, text))
            return
        if token == "eof":
            self.commands.put("quit")
            self.stop_wanted = self.running
            if self.running:
                self.harness.control(Stop())
            return
        if token == "line":
            self.line(text.strip())

    def line(self, text: str) -> None:
        if not text:
            return
        word = text.lower()
        first = word.split(" ", 1)[0].lstrip("/") if word.startswith("/") else ""
        if first in self.commands_extra:
            try:
                said = self.commands_extra[first](text.split(" ", 1)[1].strip() if " " in text else "")
            except Exception as error:  # noqa: BLE001 -- a consumer's command that raises is shown, never fatal
                said = f"/{first} failed: {type(error).__name__}: {error}"
            if said:
                self.inbox.put(("notice", said))
        elif word in ("/tree", "/help", "?", "/keys", "/who"):
            self.inbox.put(("key", {"/tree": "tree", "/who": "who"}.get(word, "help"), ""))
        elif word.startswith("/open") or word.startswith("/close"):
            self.inbox.put(("key", "open" if word.startswith("/open") else "close", text.split(" ", 1)[1].strip() if " " in text else ""))
        elif word in ("resume", "/resume"):
            if self.stop_wanted or not self.running:
                self.commands.put("resume")
            else:
                self.inbox.put(("notice", "Nothing is stopped. Press Escape to stop the run first."))
        elif word in ("quit", "/quit", "exit"):
            self.commands.put("quit")
            if self.running:
                self.stop_wanted = True
                self.send(Stop())
        elif self.asking and word in ("y", "yes", "approve", "n", "no", "refuse"):
            ask = self.asking
            self.asking = ""
            ok = self.send(Approve(ask_id=ask) if word in ("y", "yes", "approve") else Refuse(ask_id=ask, reason="you refused it"))
            self.inbox.put(("answered", ask, ok))
        elif word.startswith("/enter") or word in ("/up", "/back"):
            if word.startswith("/enter"):
                said = agent_focus.enter(self.view, self.view.focus, text[6:].strip())
                if said:
                    self.inbox.put(("notice", said))
                    return
            elif not agent_focus.leave(self.view.focus):
                self.inbox.put(("notice", "Already at the main session."))
                return
            self.looked()
        elif word.startswith("/stop"):
            name = text[5:].strip()
            agent = self.view.find_agent(name) if name else ""
            if name and not agent:
                self.inbox.put(("notice", f"No single agent matches {name!r}."))
            elif not self.send(Stop(agent_id=agent)) and agent:
                self.inbox.put(("notice", "This harness cannot stop one agent; use Escape to stop the whole run."))
        elif self.running and not self.stop_wanted:
            target, body = agent_focus.targets(self.view.focus), text
            if text.startswith("@") and " " in text:
                name, body = text[1:].split(" ", 1)
                target = self.view.find_agent(name)
                if not target:
                    self.inbox.put(("notice", f"No single agent matches {name!r}."))
                    return
            agent = self.view.agents.get(target)
            if target and agent is not None and agent.state != "running":
                self.inbox.put(("notice", f"{agent_focus.name_of(self.view, target)} has finished: its result is in this view. Go back with Left to steer the run."))
                return
            if target and not getattr(self.harness.capabilities, "target_agents", False):
                self.inbox.put(("notice", "This harness cannot send a message to one agent while it works; go back to the top to steer the run."))
                return
            message = agent_focus.steer_for(self.view.focus, body, uuid.uuid4().hex[:8])
            if target != message.agent_id:
                message = replace(message, agent_id=target)
            ok = self.send(message)
            self.inbox.put(("sent", message, ok))
            if not ok:
                if getattr(self.harness.capabilities, "steer", False):
                    self.unsent.append(message)
                else:
                    self.inbox.put(("notice", "This harness cannot take a message while it works."))
        else:
            self.inbox.put(("notice", "Nothing is running. Type resume to continue a stopped run, or quit."))

    # --- the main thread ----------------------------------------------------------------------------------------------------------

    def run_folder(self) -> str:
        """The folder the run works in (the harness, or the one it wraps, says it), or an empty string."""
        harness = self.harness
        for _ in range(6):
            root = getattr(harness, "root", "") or getattr(getattr(harness, "runner", None), "root", "")
            if root:
                return str(root)
            harness = getattr(harness, "harness", None)
            if harness is None:
                break
        return ""

    def guarded(self, make: Callable[[], Any], event: SessionEvent, fallback: Any = "") -> Any:
        """``make()``, or, when drawing the event fails, the event as one plain line (or ``fallback`` where the caller needs another shape): a render error never ends the session or the
        run. The first error is written once, with its trace, to a log file in the run's own folder; the rest are only counted."""
        try:
            return make()
        except Exception as error:  # noqa: BLE001 -- a view that cannot draw an event is not the run's failure
            self.render_errors = getattr(self, "render_errors", 0) + 1
            if self.render_errors == 1:
                self.log_render_error(event, error)
            return plain_event(event) if fallback == "" else fallback

    def log_render_error(self, event: SessionEvent, error: BaseException) -> None:
        import os
        import traceback
        folder = self.run_folder()
        if not folder:
            return
        try:
            target = os.path.join(folder, ".ahohs")
            os.makedirs(target, exist_ok=True)
            with open(os.path.join(target, "render_errors.log"), "a", encoding="utf-8") as handle:
                handle.write(f"Could not draw a {type(event).__name__} event: {type(error).__name__}: {error}\n" + "".join(traceback.format_exception(error)) + "\n")
        except OSError:
            pass

    def show(self, event: SessionEvent) -> None:
        self.events.append(event)
        self.view.apply(event)
        if isinstance(event, Waiting):
            self.asking = event.ask_id
        if not self.live:
            self.painter.line(self.guarded(lambda: event_line(event, self.view, self.panel), event))
        if hasattr(self.keys, "react"):
            self.keys.react(event)

    def handle(self, item: Tuple[Any, ...]) -> None:
        kind = item[0]
        if kind == "event":
            self.show(item[1])
        elif kind == "typing":
            self.view.typing = item[1]
        elif kind == "sent":
            message, ok = item[1], item[2]
            self.view.sent(message.message_id, message.text, message.agent_id)
            if not self.live and not self.panel:       # with a panel the queued message is shown there until it is taken up, then the transcript gets the taken-up line
                self.painter.line(f"[{int(self.view.now - self.view.started) // 60}:{int(self.view.now - self.view.started) % 60:02d}] You: {short(message.text, 70)} ({'queued, read after the current step' if ok else 'waiting to be sent'})")
        elif kind == "control":
            if isinstance(item[1], Stop) and item[2] and not item[1].agent_id:
                self.view.status = "stopping"
                if not self.live:
                    self.painter.line(hub_lines.stopping_line())
        elif kind == "nav":
            self.pending_nav = max(self.pending_nav - 1, 0)
            if item[1] == "focus":
                if agent_focus.focus_on(self.view, self.view.focus, item[2].strip()):
                    self.looked()
            elif not self.agent_keys(item[1]):
                self.key(item[1], item[2])
        elif kind == "esc":
            self.stop_here()
        elif kind == "looking":
            if not self.live and not self.panel:       # a screen with a panel shows where the person is in its panel
                self.painter.line(f"now viewing: {agent_focus.breadcrumb(self.view, self.view.focus, 100)}")
        elif kind == "key":
            self.key(item[1], item[2])
        elif kind == "answered":
            self.view.asking = None
            self.view.status = "running"
        elif kind == "notice":
            self.view.notice(item[1])
            if not self.live:
                self.painter.line(item[1])

    def tables(self) -> Any:
        if self.loaded is None:
            self.loaded = tables_of(self.records) or {}
        return self.loaded or None

    def refresh_structure(self, force: bool = False) -> Mapping[str, Any]:
        """The compact structure line and the panel, from the events so far and the records; recomputed only when an event or a key changed what they show."""
        view = self.view
        shape = (len(self.events), view.show_structure, view.selected, tuple(view.opened))
        if shape == self.shape and not force:
            return self.data
        self.shape = shape
        data = structure_view(self.events, self.tables(), tuple(view.opened))
        nodes = flatten(data["tree"])
        self.nodes = [node["solution"] for node in nodes]
        view.selected = min(view.selected, max(len(nodes) - 1, 0))
        helpers = sum(len(node["agents"]) for node in nodes) + len(data["unplaced"])
        if not nodes and not helpers:
            view.structure_compact, view.structure_panel = "", ([present.TEXT["structure"] + " (Tab hides)"] +["  " + row for row in view.authority] if view.authority and view.show_structure else [])
        else:
            roots = data["tree"]
            lead = ", ".join(f"{root['name']} [{root['state']}]" + (" > " + ", ".join(c["name"] for c in root["children"]) if root["children"] else "") for root in roots[:2])
            view.structure_compact = f"{lead}; {helpers} helper{'' if helpers == 1 else 's'} {present.TEXT['structure_tab']}" if lead else ""      # with no solution named there is nothing to say here: the Agents block lists the helpers
            selected = self.nodes[view.selected] if self.nodes else ""
            rows = ["  " + row for row in structure_lines(data, max(self.width - 6, 40), selected)] + (["  " + row for row in view.authority] if view.authority else [])
            room = max(shutil.get_terminal_size((80, 24)).lines - 14, 6) if self.live else 10 ** 6      # the frame never grows taller than the screen
            if len(rows) > room:
                rows = rows[:room - 1] + [f"  ... {len(rows) - room + 1} more rows (close a solution with Left)"]
            view.structure_panel = [present.TEXT["structure_hint"]] + rows
        self.data = data
        return data

    data: Mapping[str, Any] = {}

    def key(self, token: str, text: str) -> None:
        """A structure or help key, taken in the main thread. On a terminal the frame shows the change; elsewhere the lines are printed."""
        view = self.view
        data = self.refresh_structure(force=True)
        if token == "who":
            for row in view.authority or ["No representative is named for this run: the hub's default applies."]:
                view.notice(row)
                if not self.live:
                    self.painter.line(row)
            return
        if token == "help":
            view.show_help = not view.show_help
            if not self.live and view.show_help:
                for row in HELP_ROWS:
                    self.painter.line(row)
            return
        if not self.nodes and not data.get("unplaced") and not view.authority:
            self.view.notice("No solution is named for this run yet, so there is no structure to show (give one with --solution).")
            if not self.live:
                self.painter.line(self.view.notices[-1])
            return
        if token == "tree":
            view.show_structure = not view.show_structure
        elif token in ("up", "down"):
            view.show_structure = True
            view.selected = max(0, min(view.selected + (1 if token == "down" else -1), len(self.nodes) - 1))
        elif token in ("open", "close"):
            view.show_structure = True
            name = text.strip() if text.strip() else (self.nodes[view.selected] if self.nodes else "")
            if name == "*" and token == "open":
                view.opened[:] = list(self.nodes)
            elif name == "*":
                view.opened[:] = []
            else:
                known = next((n for n in self.nodes if n == name or n.startswith(name)), "") if name else ""
                if not known:
                    self.view.notice(f"No solution in view matches {name!r}.")
                elif token == "open" and known not in view.opened:
                    view.opened.append(known)
                elif token == "close" and known in view.opened:
                    view.opened.remove(known)
        self.refresh_structure(force=True)
        if not self.live and view.show_structure:
            for row in view.structure_panel:
                self.painter.line(row)

    def retry(self) -> None:
        for message in list(self.unsent):
            agent = self.view.agents.get(message.agent_id) if message.agent_id else None
            if agent is not None and agent.state != "running":      # the helper ended before it could be reached: the message is not sent late to nobody
                self.unsent.remove(message)
                self.view.notice(f"A message to {agent_focus.name_of(self.view, message.agent_id)} was not delivered: it had finished.")
                continue
            if self.harness.control(message):
                self.unsent.remove(message)
                with self.lock:
                    self.controls.append((message, True))

    def redraw(self) -> None:
        self.view.now = self.clock()
        self.refresh_structure()
        try:
            self.view.segments = [fn(self.view) for fn in self.segments]
            self.view.panels = [row for fn in self.panels for row in fn(self.view)]
        except Exception:  # noqa: BLE001 -- a consumer's segment that raises is left out, never fatal
            self.view.segments, self.view.panels = [], []
        if self.live:
            self.painter.draw(frame(self.view, self.width, color=True))

    def run(self, resume_session_id: str) -> Finished:
        holder: Dict[str, Finished] = {}

        def work() -> None:
            try:
                holder["done"] = self.harness.start(self.goal, lambda event: self.inbox.put(("event", self.stamp(event))), resume_session_id)
            except Exception as error:  # noqa: BLE001 -- a harness that raises ends the run as failed
                holder["done"] = Finished(outcome="failed", error=f"{type(error).__name__}: {error}", session_id=resume_session_id)
                self.inbox.put(("event", holder["done"]))
        self.running, self.stop_wanted = True, False
        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        last = 0.0
        try:
            while thread.is_alive() or not self.inbox.empty():
                try:
                    self.handle(self.inbox.get(timeout=self.tick))
                except queue.Empty:
                    pass
                except Exception as error:  # noqa: BLE001 -- an event a view cannot draw never ends the run: it is logged once and the run goes on
                    self.guarded(lambda: (_ for _ in ()).throw(error), Step(kind="note", label=""))
                self.retry()
                if self.clock() - last >= REDRAW_SECONDS:
                    try:
                        self.redraw()
                    except Exception as error:  # noqa: BLE001 -- the same for the live screen
                        self.guarded(lambda: (_ for _ in ()).throw(error), Step(kind="note", label=""))
                    last = self.clock()
        except KeyboardInterrupt:
            self.press("interrupt")
            thread.join(timeout=30)
            while not self.inbox.empty():
                self.handle(self.inbox.get())
        thread.join()
        self.running = False
        return holder["done"]

    def stamp(self, event: SessionEvent) -> SessionEvent:
        """The event with the seconds since the run began, when the harness left them out."""
        return event if event.at else replace(event, at=max(self.clock() - self.view.started, 0.001))

    def attend(self, resume_session_id: str) -> None:
        if self.keys is not None:
            self.keys.attach(self.press)
        try:
            resumes = 0
            while True:
                done = self.run(resume_session_id)
                self.runs.append(done)
                self.redraw()
                if done.outcome != "stopped" or resumes >= MAX_RESUMES:
                    break
                command = self.next_command()
                if command != "resume":
                    break
                resumes += 1
                if not self.live:
                    self.painter.line(f"resuming session {done.session_id}")
                resume_session_id = done.session_id
                self.unsent.extend(Steer(text=text, message_id=uuid.uuid4().hex[:8]) for text in done.unseen)
                self.stop_wanted = False
                self.asking = ""
                self.view.status = "running"
        finally:
            if self.keys is not None:
                self.keys.detach()
            self.close_out()

    def close_out(self) -> None:
        """The closing account, written when the session ends (a surface that draws it differently overrides this)."""
        self.painter.erase()
        for row in report(self.view, color=self.live, width=max(self.width - 1, 40) if self.live else 0):
            self.out.write(row + "\n")
        self.out.flush()

    def next_command(self) -> str:
        """After a stop: a resume or quit already typed, or (on a terminal) wait for one. A script that typed none ends here."""
        try:
            return self.commands.get_nowait()
        except queue.Empty:
            pass
        if not getattr(self.keys, "waits_for_input", False):
            return "quit"
        self.view.status = "stopped"
        while True:
            self.handle_waiting()
            try:
                return self.commands.get(timeout=self.tick)
            except queue.Empty:
                continue

    def handle_waiting(self) -> None:
        while not self.inbox.empty():
            self.handle(self.inbox.get())
        self.redraw()


@implementation("terminal-session", "live_session")
class LiveSession:
    """Drives any harness: live view, Escape stops and keeps the session, resume, steering shown as taken up, sub-agent tree, approvals, closing report; the structure of the
    work (collapsed, opened on request), the ceilings and spend, the hub's stop decision, who the AI acts for, follow-ups that continue a session and a switch of harness."""
    REQUIRES = ()     # the seats it is handed
    agent_labels = dict(agent_focus.KEY_LABELS)          # the words its screen uses to go into a helper, back, message the one in view and stop it (the presentation metric reads these)
    agent_keys = {"enter": ("open", ""), "leave": ("close", ""), "next": ("down", ""), "stop": ("esc", "")}      # the keys a script presses for them

    def structure_lines(self, view: Any, width: int = 100) -> List[str]:
        return LineRepl().structure_lines(view, width)

    def converse(self, front_door: Optional[Callable[[str], Any]] = None, lines: Iterable[str] = (), out: Optional[TextIO] = None, viewer_id: str = "", prompt: str = "> ") -> int:
        return LineRepl().converse(front_door, lines, out, viewer_id, prompt)

    def work(self, build: Callable[[str], Harness], out: TextIO, goal: str = "", resume: str = "", lines: Optional[Iterable[str]] = None, **options: Any) -> Any:
        """The interactive command: run ``goal`` (or ask for one) on the harness ``build(name)`` gives, then take each typed line as a follow-up that continues the session, with
        ``/harness NAME`` to switch between runs. Returns the ``WorkTerminal`` (its ``reports`` hold every run's ``SessionReport``). See ``work.WorkTerminal`` for the options."""
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.work import WorkTerminal
        terminal = WorkTerminal(build, out, lines=lines, **options)
        terminal.run(goal, resume)
        return terminal

    def attend(self, harness: Harness, goal: str, out: TextIO, keys: Any = None, resume_session_id: str = "", clock: Callable[[], float] = time.monotonic,
               tick: float = 0.02, live: Optional[bool] = None, width: int = 0, records: Any = None,
               commands: Optional[Mapping[str, Callable[[str], Optional[str]]]] = None, segments: Sequence[Callable[[SessionView], str]] = (),
               panels: Sequence[Callable[[SessionView], List[str]]] = (), command: str = "", representative: Optional[Mapping[str, Any]] = None,
               stop_limits: Optional[Mapping[str, Any]] = None) -> SessionReport:
        """Run ``goal`` on ``harness`` and return the report. ``live`` (redraw in place) defaults to whether ``out`` is a terminal. ``records`` (a records root or its
        tables) is where an opened solution's fields are read; ``commands`` maps extra slash commands to a function of the rest of the line that returns text to show;
        ``segments`` are functions of the view returning extra header text and ``panels`` functions returning extra lines; ``command`` is how the surface is started."""
        tty = bool(getattr(out, "isatty", lambda: False)()) if live is None else live
        columns = width or (shutil.get_terminal_size((80, 24)).columns if tty else 80)
        session = Attendance(harness, goal, out, keys, clock, tick, tty, columns, records=records, commands=commands, segments=segments, panels=panels, command=command, representative=representative, stop_limits=stop_limits)
        session.attend(resume_session_id)
        final = session.runs[-1] if session.runs else None
        return SessionReport(final=final, runs=tuple(session.runs), events=tuple(session.events), controls=tuple(session.controls), view=session.view,
                             text=out.getvalue() if hasattr(out, "getvalue") else "")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live",
                                     description="Watch, stop, resume and steer an AI run from a terminal. Escape or Ctrl-C stops and keeps the session; type a line to steer; "
                                                 "type resume after a stop; y or n answers a question; @name text steers one helper; /stop name stops one.")
    parser.add_argument("--demo", choices=("loop", "stream"), help="run a scripted session with no model: the hub's own loop, or a fake Claude Code stream session")
    parser.add_argument("--goal", default="Add a changelog entry and ship it", help="the goal shown for the demo")
    parser.add_argument("--slow", type=float, default=0.6, help="seconds the demo pauses between steps, so it can be watched and interrupted")
    parser.add_argument("--plain", action="store_true", help="append plain lines even on a terminal")
    args = parser.parse_args(argv)
    if not args.demo:
        parser.print_help()
        return 0
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.scripted import demo_harness
    import tempfile
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_keys import ScriptedKeys, TtyKeys
    with tempfile.TemporaryDirectory() as folder:
        interactive = sys.stdin.isatty() and sys.stdout.isatty() and not args.plain
        keys: Any = TtyKeys() if interactive else ScriptedKeys().when("waiting", "line", "y")
        harness = demo_harness(args.demo, folder, pause=args.slow, keys=keys)
        session = LiveSession().attend(harness, args.goal, sys.stdout, keys, live=None if interactive else False)
    return 0 if session.final and session.final.outcome in ("met", "stopped") else 1


if __name__ == "__main__":
    raise SystemExit(main())
