"""``ahohs acp``: the hub's session ``Harness`` served as an Agent Client Protocol agent over stdio, so an existing open-source agent terminal (an ACP client) can draw the hub.

The protocol library is the official Python SDK (``agent-client-protocol``, Apache-2.0), an OPTIONAL extra (``pip install hubofhubs[acp]``); it is imported only inside ``serve``
and ``sdk``, and a missing library gives ``AcpUnavailable`` with the install line. Everything that decides what the agent says is in ``mapping`` (pure); this module only moves it.

The mapping of the protocol to the hub's contract (``session_events``):

* ``initialize``: the agent's capabilities (``loadSession``), and ``_meta.steering.supported`` as the hub's own ACP client reads it.
* ``session/new``: a hub session in the folder the client gives (a harness is built for it by ``build(folder)``, no run yet).
* ``session/prompt``: ``Harness.start``, in a thread; each event becomes updates (``mapping.Translator``); a ``Waiting`` becomes ``session/request_permission`` and the outcome is sent back as
  ``Approve`` or ``Refuse`` (a cancelled ask is a refusal); the ``Finished`` becomes the stop reason and a closing message with the outcome, report, changed files and metric after.
  A prompt on a session whose last run ended continues that hub session (a follow-up).
* ``session/cancel``: ``Stop``; the turn ends with the stop reason ``cancelled`` and the work kept.
* ``session/load``: ``Resume``: the next prompt on that session starts with the hub session id the client names (or the one the session last ended with).
* ``_session/steering``: ``Steer``, answered ``injected`` when the harness took it, ``promptRequired`` when no turn is running, ``unsupported`` when the harness cannot take a message.
"""
from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional

from hubofhubs.the_consciousness.ai_session_experience.acp_agent import mapping
from hubofhubs.the_consciousness.ai_session_experience.session_events import Approve, Finished, Harness, Refuse, Steer, Stop, Waiting

PROTOCOL_VERSION = 1
INSTALL_LINE = "pip install 'hubofhubs[acp]'   (the official Agent Client Protocol SDK, agent-client-protocol)"
STEER_WAIT_SECONDS = 3.0
DONE = object()


class AcpUnavailable(RuntimeError):
    """The optional protocol library is not installed; the message says how to install it."""


def sdk() -> Any:
    """The ``acp`` module of the SDK, or ``AcpUnavailable`` saying what to install."""
    try:
        import acp
        if not hasattr(acp, "run_agent"):
            raise ImportError("this version of the SDK has no run_agent")
        return acp
    except ImportError as error:
        raise AcpUnavailable(f"ahohs acp needs the Agent Client Protocol SDK ({error}). Install it with: {INSTALL_LINE}") from error


@dataclass
class Session:
    session_id: str
    folder: str
    harness: Optional[Harness] = None
    resume_id: str = ""
    running: bool = False
    stopping: bool = False
    history: List[Dict[str, Any]] = field(default_factory=list)


class HubAgent:
    """An ACP agent over a hub ``Harness``. ``build(folder)`` gives the harness for a session in that folder; ``steering`` says whether the harness can take a message while it works
    (advertised at ``initialize``, before any harness exists); ``acting_for`` names who the AI acts for, said once in the first message."""

    def __init__(self, build: Callable[[str], Harness], *, folder: str = ".", steering: bool = True, acting_for: str = "", name: str = "ahohs", version: str = "") -> None:
        self.build, self.folder, self.steering, self.acting_for, self.name, self.version = build, folder, steering, acting_for, name, version
        self.sessions: Dict[str, Session] = {}
        self.conn: Any = None

    # --- the connection ---------------------------------------------------------------------------------------------------------

    def on_connect(self, conn: Any) -> None:
        self.conn = conn

    async def initialize(self, protocol_version: int, client_capabilities: Any = None, client_info: Any = None, **kwargs: Any) -> Any:
        schema = sdk().schema
        return schema.InitializeResponse(protocol_version=min(int(protocol_version), PROTOCOL_VERSION), agent_capabilities=schema.AgentCapabilities(load_session=True),
                                         agent_info=schema.Implementation(name=self.name, title="AI Hub of Hubs", version=self.version or "0"),
                                         field_meta={"steering": {"supported": bool(self.steering)}})

    async def authenticate(self, method_id: str, **kwargs: Any) -> None:
        return None

    async def new_session(self, cwd: str, mcp_servers: Any = None, **kwargs: Any) -> Any:
        session = Session(uuid.uuid4().hex[:12], cwd or self.folder)
        self.sessions[session.session_id] = session
        return sdk().schema.NewSessionResponse(session_id=session.session_id)

    async def load_session(self, cwd: str, session_id: str, mcp_servers: Any = None, **kwargs: Any) -> Any:
        """Resume: a session this process knows continues from the hub session it last ended with (its history is replayed to the client); any other id is taken as a hub session id."""
        known = self.sessions.get(session_id)
        if known is None:
            self.sessions[session_id] = Session(session_id, cwd or self.folder, resume_id=session_id)
            await self.send(session_id, mapping.message(f"Loaded hub session {session_id}. The next prompt continues it."), keep=False)
        else:
            for update in list(known.history):
                await self.send(session_id, update, keep=False)
        return sdk().schema.LoadSessionResponse()

    async def cancel(self, session_id: str, **kwargs: Any) -> None:
        session = self.sessions.get(session_id)
        if session is not None and session.running and session.harness is not None:
            session.stopping = True
            session.harness.control(Stop())

    async def ext_method(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if method in mapping.STEERING_METHODS:
            return await self.steer(params)
        raise sdk().RequestError.method_not_found(method)

    async def ext_notification(self, method: str, params: Dict[str, Any]) -> None:
        return None

    # --- steering ---------------------------------------------------------------------------------------------------------------

    async def steer(self, params: Mapping[str, Any]) -> Dict[str, Any]:
        session = self.sessions.get(str(params.get("sessionId") or ""))
        text = mapping.prompt_text(params.get("prompt") or ())
        if session is None or not session.running or session.harness is None or not text:
            return {"outcome": "promptRequired"}
        if not getattr(session.harness.capabilities, "steer", False):
            return {"outcome": "unsupported"}
        message = Steer(text=text, message_id=uuid.uuid4().hex[:8])
        deadline = asyncio.get_running_loop().time() + STEER_WAIT_SECONDS
        while not session.harness.control(message):
            if asyncio.get_running_loop().time() > deadline or not session.running:
                return {"outcome": "promptRequired"}
            await asyncio.sleep(0.05)
        await self.send(session.session_id, mapping.message(f"You (steering): {text}"))
        return {"outcome": "injected", "messageId": message.message_id}

    # --- the turn ---------------------------------------------------------------------------------------------------------------

    async def send(self, session_id: str, update: Mapping[str, Any], keep: bool = True) -> None:
        session = self.sessions.get(session_id)
        if keep and session is not None:
            session.history.append(dict(update))
        await self.conn.session_update(session_id=session_id, update=dict(update))

    async def prompt(self, prompt: Any, session_id: str, **kwargs: Any) -> Any:
        acp = sdk()
        session = self.sessions.get(session_id)
        if session is None:
            raise acp.RequestError.invalid_params({"sessionId": "unknown session"})
        if session.running:
            raise acp.RequestError.invalid_request({"reason": "a turn is already running on this session"})
        goal = mapping.prompt_text(prompt)
        if not goal:
            raise acp.RequestError.invalid_params({"prompt": "the prompt has no text"})
        loop = asyncio.get_running_loop()
        events: "asyncio.Queue[Any]" = asyncio.Queue()
        translator = mapping.Translator(self.acting_for)
        try:
            session.harness = session.harness or self.build(session.folder)
        except Exception as error:  # noqa: BLE001 -- a harness that cannot be built is the turn's failure, said plainly
            await self.send(session_id, mapping.message(f"Cannot start: {type(error).__name__}: {error}"))
            return acp.schema.PromptResponse(stop_reason="end_turn", field_meta={"hub": {"outcome": "failed"}})
        harness, resume = session.harness, session.resume_id
        session.running, session.stopping = True, False
        outcome: Dict[str, Any] = {}

        def work() -> Finished:
            return harness.start(goal, lambda event: loop.call_soon_threadsafe(events.put_nowait, event), resume)
        future = loop.run_in_executor(None, work)
        future.add_done_callback(lambda done: loop.call_soon_threadsafe(events.put_nowait, DONE))
        try:
            while True:
                event = await events.get()
                if event is DONE:
                    break
                for update in translator.updates(event):
                    await self.send(session_id, update)
                if isinstance(event, Waiting):
                    await self.ask(session, harness, event, translator)
            try:
                done = future.result()
            except Exception as error:  # noqa: BLE001 -- a harness that raises ends the run as failed
                done = Finished(outcome="failed", error=f"{type(error).__name__}: {error}", session_id=resume)
            stop, updates, meta = translator.closing(done)
            for update in updates:
                await self.send(session_id, update)
            if done.session_id:
                session.resume_id = done.session_id
            outcome.update(stop=stop, meta=meta)
        finally:
            session.running = False
        return acp.schema.PromptResponse(stop_reason=outcome["stop"], field_meta=outcome["meta"])

    async def ask(self, session: Session, harness: Harness, event: Waiting, translator: mapping.Translator) -> None:
        """A risky step waits: ask the client, and send the answer to the harness (a cancelled or failed ask is a refusal, so the step never runs by accident)."""
        helper = translator.helpers.get(event.agent_id)
        request = mapping.permission_request(event, helper.task if helper is not None else "")
        try:
            answer = mapping.choice_of(await self.conn.request_permission(session_id=session.session_id, tool_call=request["toolCall"], options=request["options"]))
        except Exception:  # noqa: BLE001 -- a client that cannot be asked refuses
            answer = mapping.OPTION_REFUSE
        harness.control(Approve(ask_id=event.ask_id) if answer == mapping.OPTION_APPROVE else Refuse(ask_id=event.ask_id, reason="refused in the client"))


def serve(agent: HubAgent) -> None:
    """Run the agent on this process's stdin and stdout until the client closes them."""
    acp = sdk()
    asyncio.run(acp.run_agent(agent))
