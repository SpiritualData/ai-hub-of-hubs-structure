"""Going in and out of the agents of a run: the tree of agents as a person walks it, shared by every terminal arm so none of them reimplements it.

A run is a tree: the main session and the helpers it started, which started helpers of their own, as deep as the work goes. A person looks at ONE agent at a time (the focus): the main
session at first. From there the keys are the same at every depth and the screen has the same shape at every depth:

* the focus is a path of agent ids from the main session down; ``Focus.current`` is the agent in view and ``listing`` its direct children, one flat row each (no indentation, so a
  helper five levels down gets the same width as one level down);
* ``Up`` and ``Down`` move the cursor over those rows, ``Right`` goes into the agent under the cursor (a running one shows its live activity, a finished one what it did and its result),
  ``Left`` goes up one level (``leave``); a breadcrumb row (``breadcrumb``) always says where the person is, in a fixed width whatever the depth;
* what the person types is a message to the agent in view (``steer_for``: the control names that agent's id, so the harness delivers it to that agent and not to its parent) and ``Esc``
  stops the agent in view only (``stop_for``); at the main level both are the whole run's, as before;
* a finished agent stays in its parent's list and stays enterable; its result shows in the parent's row once and in full inside the agent.

This module holds the model (the focus, the rows, the routing, the words) and no drawing surface: ``session_view.frame`` and the full-screen arms draw the lines it gives. Standard library
and the hub's session events only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from hubofhubs.the_consciousness.ai_session_experience.session_events import MAIN, Steer, Stop, short
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import present

#: the keys an arm's screen uses for each action, as it says them on screen (an arm that uses others declares them in its own ``screen_labels``)
KEY_LABELS: Dict[str, str] = {"enter": "Right", "leave": "Left", "pick": "Up/Down", "message": "type + Enter", "stop": "Esc"}
NAME_CHARS = 18                  # the most characters of an agent's name in a breadcrumb or a prompt, so the line is as wide at any depth
RESULT_LINES = 3


@dataclass
class Focus:
    """Where the person is: the agent ids from the main session down to the agent in view (empty: the main session), and the row of its children the cursor is on."""
    path: List[str] = field(default_factory=list)
    cursor: int = 0

    @property
    def current(self) -> str:
        return self.path[-1] if self.path else MAIN

    @property
    def depth(self) -> int:
        return len(self.path)


def parent_of(view: Any, agent: Any) -> str:
    """The agent's parent as the tree has it (an unknown parent is the main session)."""
    return agent.parent_id if agent.parent_id in view.agents else MAIN


def children(view: Any, who: str) -> List[Any]:
    """The direct children of ``who`` in the order they started, finished ones included."""
    return [a for a in list(view.agents.values()) if parent_of(view, a) == who]


def below(view: Any, who: str) -> List[Any]:
    """Every agent under ``who``, at any depth."""
    out: List[Any] = []
    for child in children(view, who):
        out.append(child)
        out.extend(below(view, child.agent_id))
    return out


def running_below(view: Any, who: str) -> int:
    return sum(1 for a in below(view, who) if a.state == "running")


def name_of(view: Any, who: str) -> str:
    agent = view.agents.get(who)
    return "main" if who == MAIN or agent is None else short(present.one_line(agent.task), NAME_CHARS)


def prune(view: Any, focus: Focus) -> None:
    """Keep the focus on agents that exist (a reset or a replay may drop one) and the cursor on a row."""
    for index, who in enumerate(focus.path):
        if who not in view.agents:
            del focus.path[index:]
            break
    focus.cursor = max(0, min(focus.cursor, max(len(children(view, focus.current)) - 1, 0)))


def listing(view: Any, focus: Focus) -> List[Any]:
    prune(view, focus)
    return children(view, focus.current)


def move(view: Any, focus: Focus, delta: int) -> None:
    rows = listing(view, focus)
    focus.cursor = max(0, min(focus.cursor + delta, max(len(rows) - 1, 0)))


def enter(view: Any, focus: Focus, token: str = "") -> str:
    """Go into the agent under the cursor (or the one ``token`` names: a row number, or a word of its name). Returns the reason when there is none to enter, else an empty string."""
    rows = listing(view, focus)
    if not rows:
        return "No helper here to enter."
    pick: Optional[Any] = None
    word = token.strip().lower()
    if word.isdigit() and 1 <= int(word) <= len(rows):
        pick = rows[int(word) - 1]
    elif word:
        hits = [a for a in rows if word in a.task.lower() or word == a.agent_id.lower()]
        pick = hits[0] if len(hits) == 1 else None
        if pick is None:
            return f"No single helper here matches {token.strip()!r}."
    else:
        pick = rows[focus.cursor]
    focus.path.append(pick.agent_id)
    focus.cursor = 0
    return ""


def focus_on(view: Any, focus: Focus, agent_id: str) -> bool:
    """Put the focus on ``agent_id`` (the path of its ancestors from the main session down); an empty id is the main session. False when no such agent is known."""
    if not agent_id or agent_id == MAIN:
        focus.path.clear()
        focus.cursor = 0
        return True
    if agent_id not in view.agents:
        return False
    path: List[str] = []
    who = agent_id
    while who in view.agents and who not in path:
        path.append(who)
        who = parent_of(view, view.agents[who])
    focus.path[:] = list(reversed(path))
    focus.cursor = 0
    return True


def leave(focus: Focus) -> bool:
    """Go up one level; False at the main session."""
    if not focus.path:
        return False
    focus.path.pop()
    focus.cursor = 0
    return True


def breadcrumb(view: Any, focus: Focus, width: int, glyphs: bool = False) -> str:
    """One row that says where the person is, ``main > helper > helper``, never wider than ``width``: when the path is long the middle is cut to an ellipsis and the first and the last
    names stay, so the row is the same shape at depth 1 and at depth 4."""
    sep = " › " if glyphs else " > "
    names = ["main"] + [name_of(view, who) for who in focus.path]
    shapes = [names] + ([[names[0], "...", *names[-2:]]] if len(names) > 3 else []) + ([[names[0], "...", names[-1]]] if len(names) > 2 else []) + [["...", names[-1]]]
    for shape in shapes:
        text = sep.join(shape)
        if len(text) <= width:
            return text
    return text[:max(width - 3, 1)] + "..."


def prompt(view: Any, focus: Focus) -> str:
    """The input line's lead: who a typed line goes to."""
    return "> " if not focus.path else f"{name_of(view, focus.current)} > "


def targets(focus: Focus) -> str:
    """The agent id a control names (empty: the whole run)."""
    return focus.path[-1] if focus.path else ""


def steer_for(focus: Focus, text: str, message_id: str) -> Steer:
    """The control for a line the person typed: to the agent in view, so the harness delivers it to that agent and not to its parent."""
    return Steer(text=text.strip(), agent_id=targets(focus), message_id=message_id)


def stop_for(focus: Focus) -> Stop:
    """The control for Escape: the agent in view only (the whole run at the main level)."""
    return Stop(agent_id=targets(focus))


def state_word(agent: Any) -> str:
    return {"running": "running", "met": "done", "unmet": "unmet", "stopped": "stopped", "failed": "failed", "not_started": "waiting"}.get(agent.state, agent.state)


def glyph_of(agent: Any, color: bool) -> str:
    state = {"met": "done", "unmet": "unmet"}.get(agent.state, agent.state)
    return present.paint(present.GLYPHS.get(state, present.GLYPHS["running"]), present.STATE_COLOR.get(state, ""), color)


def figures(agent: Any) -> str:
    calls = f"{agent.calls} call{'' if agent.calls == 1 else 's'}" if agent.calls else ""
    return present.join([calls, present.count_text(agent.tokens, "token"), present.cost_text(agent.cost_usd) if agent.cost_usd else ""], ", ")


def child_rows(view: Any, focus: Focus, width: int, color: bool = False, shown: int = 6) -> List[str]:
    """One flat row per direct child of the agent in view: a cursor mark, its number, a state glyph, its task, its state, what it is doing now or its result in short, and how many
    run below it. The same shape at every depth. More than ``shown`` rows scroll with the cursor."""
    rows = listing(view, focus)
    if not rows:
        return []
    start = max(0, min(focus.cursor - shown + 1, len(rows) - shown)) if len(rows) > shown else 0
    out: List[str] = []
    for index in range(start, min(start + shown, len(rows))):
        agent = rows[index]
        mark = (">" if not color else "›") if index == focus.cursor else " "
        deeper = running_below(view, agent.agent_id)
        tail = agent.activity if agent.state == "running" else short(present.one_line(agent.summary), 40)
        more = f" (+{deeper} below)" if deeper else ""
        text = f"{mark}{index + 1}. {glyph_of(agent, color)} {short(present.one_line(agent.task), 28)} [{state_word(agent)}]{more}"
        out.append(text + (f" {short(tail, 40)}" if tail else ""))
    if len(rows) > shown:
        out.append(f"  ({len(rows)} here; Up and Down move)")
    return out


def message_rows(view: Any, focus: Focus, limit: int = 2) -> List[str]:
    """The messages the person sent to the agent in view (or to the whole run at the main level), each as queued until the harness says it was taken up."""
    mine = [m for m in view.messages if (m.agent_id or MAIN) == focus.current]
    who = "" if not focus.path else f" to {name_of(view, focus.current)}"
    return [f"you{who}: {short(m.text, 50)}  ({'taken up' if m.taken_up else 'queued: it reads it at its next step'})" for m in mine[-limit:]]


def agent_lines(view: Any, focus: Focus, width: int, color: bool = False, rows: int = 8) -> List[str]:
    """What the screen shows of the agent in view when it is not the main session: its state row, what it did and is doing (its own steps, finished ones too), its result when it ended,
    its children, and the messages sent to it. The same rows, in the same order, at every depth."""
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.session_view import step_row
    who = focus.current
    agent = view.agents.get(who)
    if agent is None:
        return []
    out = [f"{glyph_of(agent, color)} {short(present.one_line(agent.task), max(width - 30, 20))}  {state_word(agent)}" + (f" · {figures(agent)}" if figures(agent) else "")]
    own = [s for s in view.steps.values() if s.agent_id == who and not present.is_lifecycle(s) and s.kind != "delegate" and s.label]
    out.extend(step_row(s, color) for s in own[-rows:])
    if agent.state != "running" and agent.summary:
        wrapped = present.wrap(present.one_line(agent.summary), max(width - 12, 20), "Result: ", "  ")
        out.extend(wrapped[:RESULT_LINES])
    out.extend(child_rows(view, focus, width, color))
    out.extend(message_rows(view, focus))
    return out


def keys_hint(view: Any, focus: Focus, labels: Optional[Dict[str, str]] = None) -> str:
    """The key hints of the focus, as whole hints (the last ones are dropped first on a narrow screen). The same words at every depth."""
    word = {**KEY_LABELS, **(labels or {})}
    if focus.path:
        return f"{word['leave']} back | {word['stop']} stop this one | {word['message']} message it | {word['pick']} pick | {word['enter']} enter"
    if children(view, MAIN):
        return f"{word['stop']} stop | {word['message']} to steer | {word['pick']} pick | {word['enter']} enter | Tab structure | ? keys"
    return ""


def key_rows(labels: Optional[Dict[str, str]] = None) -> Sequence[str]:
    word = {**KEY_LABELS, **(labels or {})}
    return (f"{word['pick']}, {word['enter']}   pick a helper and go into it to watch it and talk to it; {word['leave']} goes back up one level",
            f"{word['message']}   send a message to the agent in view; {word['stop']} stops that one only (at the top, the whole run)")


__all__ = ["Focus", "focus_on", "KEY_LABELS", "agent_lines", "below", "breadcrumb", "child_rows", "children", "enter", "keys_hint", "leave", "listing", "message_rows", "move", "name_of", "prompt",
           "prune", "running_below", "steer_for", "stop_for", "targets"]
