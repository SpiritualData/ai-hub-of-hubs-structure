"""The run: what the client's requests do to a hub ``Harness``, and what the harness's events do to the store.

The client sends a prompt, an interrupt and a permission reply; the hub's contract has ``start``, ``Steer``, ``Stop``, ``Approve`` and ``Refuse``. The decisions are made from the server's own state, never from
the words typed: a prompt on a session with no run starts one (a first goal, or a follow-up or a resume that continues the hub session the last run ended with); a prompt while a run works is a ``Steer``
(a harness that cannot take one leaves the message waiting in the inbox, and it starts the next run when this one ends); an interrupt is a ``Stop``; a reply of once or always is ``Approve`` and a
reject is ``Refuse``. Standard library only."""
from __future__ import annotations

import threading
import time
from typing import Any, Callable, Dict, Optional

from hubofhubs.the_consciousness.ai_session_experience.opencode_server.mapping import Translator
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.projection import Store
from hubofhubs.the_consciousness.ai_session_experience.session_events import Approve, Finished, Harness, Refuse, SessionEvent, Steer, Stop

STEER_WAIT_SECONDS = 3.0


class Bridge:
    """One served session over one harness. ``build(folder)`` gives the harness (built once, on the first prompt)."""

    def __init__(self, build: Callable[[str], Harness], folder: str, *, acting_for: str = "", command: str = "ahohs work", clock: Callable[[], float] = time.time,
                 steer_wait: float = STEER_WAIT_SECONDS) -> None:
        self.build, self.folder, self.steer_wait = build, folder, steer_wait
        self.store = Store(folder, clock)
        self.root = self.store.ids.make("ses")
        self.store.create_session(self.root, "")
        self.translator = Translator(self.store, self.root, acting_for, command)
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
            if self.harness is None:
                self.harness = self.build(self.folder)
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

    # --- the client's requests ----------------------------------------------------------------------------------------------------

    def prompt(self, text: str, message_id: str = "") -> Dict[str, Any]:
        """A person's message. With no run it starts one (a follow-up or a resume continues the hub session the last run named); with a run it is a steer."""
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
