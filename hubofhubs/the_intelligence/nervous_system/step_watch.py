"""What a running session's own steps show that is worth one steering message: a command run a third time unchanged, and sub-agent calls past the budget.

Pure code over the tool calls a session has made so far, ``[(tool name, tool input)]`` in order: no model call, no file or environment read. A command is the
same when its words are the same; a change to a file between two runs of it makes the next run a different step (the work changed what the command sees), so
the count starts again. ``step_findings`` returns the findings not yet reported (the caller keeps the ``reported`` set), so a finding steers once. Standard library only.
"""
from __future__ import annotations

from typing import Any, Collection, Iterable, List, Sequence, Tuple

REPEAT_LIMIT = 3
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
AGENT_TOOLS = ("Agent", "Task")
COMMAND_CHARS = 120


def repeated_commands(actions: Sequence[Tuple[str, Any]], times: int = REPEAT_LIMIT, write_tools: Collection[str] = WRITE_TOOLS) -> List[str]:
    """The commands (as words, in the order they first reached ``times`` runs) that were run ``times`` times with no file written between the runs."""
    counts: dict = {}
    found: List[str] = []
    for name, data in actions:
        if name in write_tools:
            counts.clear()
        elif name == "Bash" and isinstance(data, dict) and str(data.get("command") or "").strip():
            command = " ".join(str(data["command"]).split())
            counts[command] = counts.get(command, 0) + 1
            if counts[command] == times and command not in found:
                found.append(command)
    return found


def agent_calls(actions: Iterable[Tuple[str, Any]], agent_tools: Collection[str] = AGENT_TOOLS) -> int:
    """How many sub-agent calls the session made."""
    return sum(1 for name, _ in actions if name in agent_tools)


def step_findings(actions: Sequence[Tuple[str, Any]], *, agent_budget: int, reported: Collection[str] = (), times: int = REPEAT_LIMIT) -> List[Tuple[str, str]]:
    """``[(key, message)]`` of what the steps show and has not been reported (``key`` is what the caller adds to ``reported``): ``repeat:<command>`` for a command run
    ``times`` times unchanged, and ``agents`` once the sub-agent calls are past ``agent_budget``."""
    out: List[Tuple[str, str]] = []
    for command in repeated_commands(actions, times):
        key = "repeat:" + command
        if key not in reported:
            shown = command if len(command) <= COMMAND_CHARS else command[:COMMAND_CHARS - 3] + "..."
            out.append((key, f"The command `{shown}` has now run {times} times unchanged. Do not run it again as it is: change what it runs on, or take another way to the fact you need, "
                             "or report what you tried."))
    used = agent_calls(actions)
    if used > agent_budget and "agents" not in reported:
        out.append(("agents", f"{used} sub-agent calls were made and the allowance is {agent_budget}; further calls are refused. Do the rest of the work yourself and report."))
    return out
