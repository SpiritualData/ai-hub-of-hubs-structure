"""The run: what the client's requests do to a hub ``Harness``, and what the harness's events do to the store.

The client sends a prompt, an interrupt and a permission reply; the hub's contract has ``start``, ``Steer``, ``Stop``, ``Approve`` and ``Refuse``. The decisions are made from the server's own state, never from
the words typed: a prompt on a session with no run starts one (a first goal, or a follow-up or a resume that continues the hub session the last run ended with); a prompt while a run works is a ``Steer``
(a harness that cannot take one leaves the message waiting in the inbox, and it starts the next run when this one ends); an interrupt is a ``Stop``; a reply of once or always is ``Approve`` and a
reject is ``Refuse``. Standard library only."""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from pathlib import PurePath
from typing import Any, Callable, Dict, Optional, Sequence, Tuple, Union

from hubofhubs.the_consciousness.ai_session_experience.opencode_server.mapping import Translator
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.projection import Store
from hubofhubs.the_consciousness.ai_session_experience.session_events import Approve, Finished, Harness, Refuse, SessionEvent, Steer, Stop

STEER_WAIT_SECONDS = 3.0


@dataclass(frozen=True)
class SlashCommand:
    """A command a consumer adds to the client's slash menu: ``name`` (typed after the slash), a one-line ``description`` the menu shows, and ``run(argument)``, which does the command and returns
    the lines to say (one quiet row in the transcript) or an empty result to say nothing. It runs on the server's thread, never inside the harness, so a command works while a run works."""
    name: str
    description: str
    run: Callable[[str], Union[str, Sequence[str], None]]


class Bridge:
    """One served session over one harness. ``build(folder)`` gives the harness (built once, on the first prompt)."""

    def __init__(self, build: Callable[[str], Harness], folder: str, *, acting_for: str = "", command: str = "ahohs work", clock: Callable[[], float] = time.time,
                 steer_wait: float = STEER_WAIT_SECONDS, folder_name: bool = True, tiers: Tuple[str, ...] = (), tier: str = "",
                 commands: Sequence[SlashCommand] = (), header: Optional[Callable[[], Sequence[str]]] = None) -> None:
        """With ``tiers`` the client's model picker lists them and ``build(folder, tier)`` is called with the tier in use (the one the person last picked, else ``tier``); without, ``build(folder)``.
        A consumer's own ``commands`` join the client's slash menu (a command typed as a line, such as ``/name argument``, runs the same way), and ``header`` gives the short lines its plugin shows
        beside who the work serves (read again whenever the session's state is published and after each command)."""
        self.build, self.folder, self.steer_wait = build, folder, steer_wait
        self.tier = tier if tier in tiers else ""
        self.built_tier = ""
        # the full-screen client prints the folder in its footer: the name, not the machine's path (the inline client joins it to its own folder, so it is told the real one)
        self.store = Store(folder, clock, shown=PurePath(folder).name if folder_name else "", tiers=tuple(tiers), tier=self.tier)
        self.root = self.store.ids.make("ses")
        self.store.create_session(self.root, "")
        self.commands: Dict[str, SlashCommand] = {c.name: c for c in commands}
        self.translator = Translator(self.store, self.root, acting_for, command, header=header)
        self.lock = threading.RLock()
        self.harness: Optional[Harness] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.starting = ""
        self.resume_id = ""
        self.last_outcome = ""
        self.controls: list = []            # (control, accepted) in order, for a test or a scorer to read

    # --- the harness's side --------------------------------------------------------------------------------------------------------

    def sink(self, event: SessionEvent) -> None:
        with self.lock:
            self.translator.handle(event)

    def start(self, goal: str, message_id: str = "") -> None:
        with self.lock:
            if self.harness is None or self.built_tier != self.tier:        # a tier picked since the last run is the tier of this one (the session continues on the new harness)
                self.harness = self.build(self.folder, self.tier) if self.store.tiers else self.build(self.folder)
                self.built_tier = self.tier
            harness, resume = self.harness, self.resume_id
            self.running, self.starting = True, message_id
            self.thread = threading.Thread(target=self.work, args=(harness, goal, resume), daemon=True)
            self.thread.start()

    def work(self, harness: Harness, goal: str, resume: str) -> None:
        try:
            done = harness.start(goal, self.sink, resume)
        except Exception as error:  # noqa: BLE001 -- a harness that raises ends the run as failed, said plainly
            done = Finished(outcome="failed", error=f"{type(error).__name__}: {error}", session_id=resume)
            self.sink(done)
        follow = ""
        with self.lock:
            if self.starting:                      # the message that started the run is in the transcript even when the run failed before it could say so
                self.store.deliver(self.root, self.starting)
                self.starting = ""
            self.running = False
            self.resume_id = done.session_id or self.resume_id
            self.last_outcome = done.outcome
            if done.outcome != "stopped":
                waiting = self.store.pending[self.root]
                follow = waiting[0]["payload"]["text"] if waiting else ""
        if follow:
            self.start(follow)

    def wait(self, timeout: float = 30.0) -> bool:
        """True when no run is working (a test or a caller that needs the end)."""
        thread = self.thread
        if thread is not None:
            thread.join(timeout)
        return not self.running

    # --- the consumer's commands --------------------------------------------------------------------------------------------------

    def command(self, name: str, argument: str = "") -> bool:
        """Run the consumer's command ``name`` (with or without its slash) and say what it returned as one quiet row. False when no command has that name."""
        found = self.commands.get(name.lstrip("/").strip())
        if found is None:
            return False
        try:
            said = found.run(argument.strip())
        except Exception as error:  # noqa: BLE001 -- a command that fails says so in the transcript and never ends the session
            said = f"/{found.name} failed: {type(error).__name__}: {error}"
        self.say(said)
        return True

    def say(self, lines: Union[str, Sequence[str], None]) -> None:
        """One quiet row in the transcript (the lines joined) for something the program running the session wants the person to read; the header lines are read again with it. Callable from any thread."""
        parts = [lines] if isinstance(lines, str) else [str(line) for line in (lines or ())]
        text = "\n".join(line for line in parts if line.strip())
        with self.lock:
            if text:
                self.store.synthetic(self.root, text, text.splitlines()[0][:160])
            self.translator.publish()

    def typed_command(self, text: str) -> bool:
        """True when ``text`` is a line for one of the consumer's commands (``/name`` and what follows), which is then run and is never a message to the AI."""
        word, _, rest = text.strip().partition(" ")
        return word.startswith("/") and word[1:] in self.commands and self.command(word, rest)

    # --- the client's requests ----------------------------------------------------------------------------------------------------

    def prompt(self, text: str, message_id: str = "") -> Dict[str, Any]:
        """A person's message. With no run it starts one (a follow-up or a resume continues the hub session the last run named); with a run it is a steer."""
        if self.typed_command(text):                  # a line for a command of the consumer's runs now, even while a run works, and is not a message
            return {"id": message_id or self.store.ids.make("inb"), "kind": "command"}
        with self.lock:
            if not self.running:
                iid = self.store.enqueue_user(self.root, text, "steer", message_id)
                self.start(text, iid)
                return {"id": iid, "kind": "start"}
            iid = self.store.enqueue_user(self.root, text, "steer", message_id)
            self.translator.correction_sent(iid, text)
            harness = self.harness
        if getattr(getattr(harness, "capabilities", None), "steer", False):
            message = Steer(text=text, message_id=iid)
            deadline = time.monotonic() + self.steer_wait
            while True:
                accepted = bool(harness.control(message))
                if accepted or time.monotonic() > deadline or not self.running:
                    break
                time.sleep(0.05)
            self.controls.append((message, accepted))
            return {"id": iid, "kind": "steer" if accepted else "queued"}
        with self.lock:
            self.store.emit("session.inbox.delivery.changed", {"sessionID": self.root, "inboxID": iid, "delivery": "queue"}, self.root)
        return {"id": iid, "kind": "queued"}

    def select_tier(self, tier: str) -> bool:
        """The person picked a tier in the client's model picker. It applies to the next run (a run that works keeps the tier it started with); a name that is not one of the hub's tiers is ignored."""
        with self.lock:
            if not self.store.select_model(self.root, tier):
                return False
            self.tier = tier
            return True

    def interrupt(self) -> bool:
        with self.lock:
            if not self.running or self.harness is None:
                return False
            harness = self.harness
        accepted = bool(harness.control(Stop()))
        self.controls.append((Stop(), accepted))
        return accepted

    def reply(self, request_id: str, decision: str, message: str = "") -> bool:
        """The person's answer to a waiting step: once or always approves, reject refuses (with the words they gave)."""
        request = self.store.answer(request_id, decision)
        if request is None or self.harness is None:
            return False
        control = Approve(ask_id=request_id) if decision in ("once", "always") else Refuse(ask_id=request_id, reason=message or "refused in the client")
        accepted = bool(self.harness.control(control))
        self.controls.append((control, accepted))
        return accepted
