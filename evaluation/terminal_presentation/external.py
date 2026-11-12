"""The protocol layer of an arm that is an external program (the ACP client arm, ``presentation = "external"``).

The hub's own side of the protocol is scored here: ``ahohs acp`` (``acp_agent``) is started as a subprocess with the scripted demo harness (no model), and a bare ACP client drives it
over stdio: a cancel, a load and a prompt, a steering message, a permission request answered approve and refuse. That shows each control reaching the harness and an acknowledgement coming
back as a protocol message, a risky step waiting with its preview, and a complete closing report. What the client DRAWS (rows, contrast, repaints, key hints, first output, plain output,
the current step on screen, each update once) is the client's own screen and is marked not run: reading it needs the real client in a pseudo-terminal (one such launch of Toad was
recorded by hand; see the arm's record). The protocol ceiling column is answered from what the protocol can carry. Needs the optional SDK; without it every check is not run."""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import checks as C

AGENT = [sys.executable, "-m", "hubofhubs.the_consciousness.ai_session_experience.acp_agent", "--demo", "--pause", "0.12"]
CLIENT_RENDERED = ("each-update-once", "current-step-visible", "no-row-wider-than-the-terminal", "repaints-under-bound", "contrast-4.5", "plain-when-not-a-terminal",
                   "key-hints-present-and-whole", "first-output-within-a-second", "unavailable-control-shown")
CEILING = {"structure-on-request": False, "spend-against-ceilings": False, "who-the-ai-acts-for": True, "correction-taken-up": True, "stop-one-helper": False}


class Client:
    """A bare ACP client: records every update and every permission request, and answers as told."""

    def __init__(self, folder: str, answer: str = "approve") -> None:
        self.folder, self.answer, self.updates, self.asked = folder, answer, [], []

    def on_connect(self, conn: Any) -> None:
        self.conn = conn

    async def session_update(self, session_id: str, update: Any, **kwargs: Any) -> None:
        self.updates.append(update.model_dump(mode="json", by_alias=True, exclude_none=True) if hasattr(update, "model_dump") else update)

    async def request_permission(self, session_id: str, tool_call: Any, options: Any, **kwargs: Any) -> Dict[str, Any]:
        body = str(tool_call.model_dump(mode="json", exclude_none=True) if hasattr(tool_call, "model_dump") else tool_call)
        self.asked.append((body, Path(self.folder, "deployed.txt").exists()))
        return {"outcome": {"outcome": "selected", "optionId": self.answer}}

    async def ext_method(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    async def ext_notification(self, method: str, params: Dict[str, Any]) -> None:
        return None

    def messages(self) -> str:
        return "\n".join(u["content"]["text"] for u in self.updates if u.get("sessionUpdate") == "agent_message_chunk")


async def session(client: Client, script: Any) -> Any:
    from hubofhubs.the_world.tools.delegated_agent_sessions.acp_session import open_agent_connection
    async with open_agent_connection(client, AGENT, env={**os.environ, "PYTHONPATH": os.pathsep.join(p for p in sys.path if p)}, cwd=client.folder) as (conn, _):
        client.on_connect(conn)
        await conn.initialize(protocol_version=1, client_capabilities={"fs": {"readTextFile": False, "writeTextFile": False}})
        new = await conn.new_session(cwd=client.folder, mcp_servers=[])
        return await script(conn, new.session_id)


def prompt(conn: Any, sid: str, text: str = "ship it") -> Any:
    return conn.prompt(session_id=sid, prompt=[{"type": "text", "text": text}])


def closing_ok(client: Client) -> bool:
    text = client.messages()
    return "Done: the goal was met" in text and "Changed (2)" in text and "Wrote the release notes" in text and "Cost and time" in text


def run_watch() -> Dict[str, Any]:
    folder = tempfile.mkdtemp(prefix="acp-")
    client = Client(folder)

    async def script(conn: Any, sid: str) -> Any:
        return await prompt(conn, sid)
    asyncio.run(session(client, script))
    # the protocol has no way to ask the agent for a structure tree, no live spend gauge (a line at the start and in the report) and no way to stop one helper
    return {"checks": {"closing-report-complete": closing_ok(client)}, "ceiling": {**{k: v for k, v in CEILING.items() if k != "correction-taken-up"}, "who-the-ai-acts-for": "Acting for" in client.messages()}}


def run_steer() -> Dict[str, Any]:
    folder = tempfile.mkdtemp(prefix="acp-")
    client = Client(folder)

    async def script(conn: Any, sid: str) -> Any:
        running = asyncio.create_task(prompt(conn, sid))
        await asyncio.sleep(0.3)
        answer = await conn.ext_method("session/steering", {"sessionId": sid, "prompt": [{"type": "text", "text": "use the short name"}], "_meta": {"steering": {"idleBehavior": "promptRequired"}}})
        await running
        return answer
    answer = asyncio.run(session(client, script))
    text = client.messages()
    sent_then_taken = "You (steering): use the short name" in text and "Taken up: use the short name" in text and text.index("You (steering)") < text.index("Taken up")
    return {"checks": {"round-trip-steer": answer.get("outcome") == "injected" and "Taken up: use the short name" in text, "correction-sent-then-taken-up": sent_then_taken},
            "ceiling": {"correction-taken-up": sent_then_taken}}


def run_stop_resume() -> Dict[str, Any]:
    folder = tempfile.mkdtemp(prefix="acp-")
    client = Client(folder)

    async def script(conn: Any, sid: str) -> Any:
        running = asyncio.create_task(prompt(conn, sid))
        await asyncio.sleep(0.5)
        await conn.cancel(session_id=sid)
        first = await running
        await conn.load_session(cwd=folder, session_id=sid, mcp_servers=[])
        return first, await prompt(conn, sid, "go on")
    first, second = asyncio.run(session(client, script))
    text = client.messages()
    kept = all(Path(folder, name).exists() for name in ("release-notes.md",))
    return {"checks": {"round-trip-stop": first.stop_reason == "cancelled" and "Stopped: finished work is kept" in text,
                       "round-trip-resume": second.stop_reason == "end_turn" and "Resuming session" in text,
                       "stop-then-resume-keeps-work": kept and "Resuming session" in text, "closing-report-complete": closing_ok(client)}}


def run_approval(answer: str) -> Dict[str, Any]:
    folder = tempfile.mkdtemp(prefix="acp-")
    client = Client(folder, answer)

    async def script(conn: Any, sid: str) -> Any:
        return await prompt(conn, sid)
    asyncio.run(session(client, script))
    asked = bool(client.asked)
    waits = asked and "creates deployed.txt" in client.asked[0][0] and client.asked[0][1] is False
    ran = Path(folder, "deployed.txt").exists()
    word = "approve" if answer == "approve" else "refuse"
    return {"checks": {"risky-step-waits-with-preview": waits, f"round-trip-{word}": asked and ran == (answer == "approve")}}


SCENARIOS = {"watch": run_watch, "steer": run_steer, "stop_resume": run_stop_resume, "approve": lambda: run_approval("approve"), "refuse": lambda: run_approval("refuse")}


def run_scenario(name: str) -> Dict[str, Any]:
    """The scenario's protocol-layer result; every check that reads the client's own screen is listed as not run."""
    import agents_scenarios as hierarchy
    if name in hierarchy.SCENARIO_CHECKS:
        return {"checks": {}, "ceiling": {}, "not_run": list(hierarchy.SCENARIO_CHECKS[name]), "note": hierarchy.NOT_DRIVEN}
    try:
        import acp  # noqa: F401
    except ImportError:
        return {"checks": {}, "ceiling": {}, "not_run": list(C.REQUIREMENTS), "note": "the Agent Client Protocol SDK is not installed (pip install 'hubofhubs[acp]')"}
    done = SCENARIOS[name]() if name in SCENARIOS else {"checks": {}, "ceiling": {}}
    done = dict(done)
    left = {c: None for c in CLIENT_RENDERED}
    done["not_run"] = sorted(set(CLIENT_RENDERED))
    done["checks"] = {**left, **done["checks"]}
    done["note"] = "the checks that read the client's own screen are not run; the protocol layer is scored"
    return done
