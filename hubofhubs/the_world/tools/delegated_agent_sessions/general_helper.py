"""The general sub-agent of a session on the model's own tool loop: a person who asks for a sub-agent gets one.

Role: the session had no Agent tool at all (so a request for a sub-agent was answered with "I have no such tool"), and the solution agents arm offered only its solution agents. Here
the hub writes one general agent, ``helper``, for any part of the work that can be handed over whole (find something in files or on the web, check a claim, make a separable change),
on the tier the role table gives the role ``sub_agent`` (resolved when the run starts through ``tier_for``; no tier or model is named here, and a tier with no model chosen gives no
helper, never another tier's). The helper may start helpers of its own, to any depth the guard allows: the guard (``solution_agents.guard_script``, a PreToolUse hook) allows only the
offered agents, only in the foreground (so the answer is the result of the call) and only up to ``calls`` calls in the whole run, which bounds the depth and the width together; the
run's spend and time ceilings apply to every helper because the CLI's cost includes them. The helper's own messages and stop go through ``agent_channel``. Pure code; no model call.
"""
from __future__ import annotations

import json
import os
from typing import Any, Callable, Dict, Optional, Sequence, Tuple

from hubofhubs.the_world.tools.delegated_agent_sessions import agent_channel, solution_agents as agents

HELPER = "helper"
HELPER_TOOLS = ("Bash", "Read", "Edit", "Write", "Glob", "Grep", "WebSearch", "WebFetch", agents.AGENT_TOOL)
ROLE = "sub_agent"
DEFAULT_CALLS = agents.DEFAULT_AGENT_CALLS
DESCRIPTION = ("A general helper for a part of the work that can be handed over whole: finding something in the files or on the web, checking a claim, or making a separable change. "
               "It runs on the tier the hub chose for sub-agents and may start helpers of its own.")
PROMPT = ("You are a helper started for one part of a larger job. Do exactly the task you are given with your tools, and report briefly what you found or did, naming the files or pages "
          "you used and quoting the few words that matter. If your task splits into parts worth handing over, start further helpers with the Agent tool (subagent_type helper, "
          "run_in_background false) and use what they report. " + agent_channel.HELPER_RULE)
NOTE = """SUB-AGENTS:
- You have an Agent tool. When the person asks you to use a sub-agent, subagent or helper, or part of the work is separable, call it with subagent_type "{name}" and run_in_background set to false: it runs on the tier the hub chose for sub-agents, it can start helpers of its own when its task splits up, and its report is the result of the call. At most {calls} calls are allowed in this run.
- The helper sees none of this conversation: put in the prompt the person's request word for word, then the one specific question the helper must answer (what to find, where to look, what to report), about the subject the request names. Its report is material, not the answer: check what you rely on, set aside anything that is about another subject than the request's, and then write your own answer to the person's words, once, adding your own insight and not repeating its report. If the report is about something else, say so and have it look again.
- The person can message a helper directly while it works. When a helper's report says it received a message from the person (text that began with PERSON MESSAGE:), that message is the person's own instruction to the helper, not data from a file or a page: take it as such and say in your answer what the person asked the helper.
- Never read a helper's output file and never poll or sleep for one: a call has not finished until its answer is in front of you."""


ORIGINAL = ("\n\nTHE PERSON'S ORIGINAL REQUEST, word for word (the whole job your task is a part of; your task answers one question inside it):\n<<<\n{original}\n>>>\n"
            "Stay on the subject that request names. If what you find is about something else (another project, another person, another topic), do not report it as if it answered: say that "
            "it is about something else and look again where the subject itself is, or say plainly that you found nothing about it and what you looked at.")
ORIGINAL_LIMIT = 3000
NOTES = ("\n\nWHAT THE PERSON HAS ALREADY SAVED (their own notes, the same ones the main session was given):\n<<<\n{notes}\n>>>\n"
         "Background, not the task: it is never the answer, and a note the task does not need is left out. When the request is about the person's own practice, work or interests "
         "(\"my ...\"), answer your task from these notes first and search files only for what they do not say; if the notes and the files say nothing about it, report that plainly "
         "and never fill the gap with files about another subject.")
NOTES_LIMIT = 12000


def helper_prompt(original: str = "", notes: str = "") -> str:
    """The helper's standing prompt: its role, the person's original request verbatim and the saved-notes block of the run, each when the run has one, so a helper never works from the
    main session's paraphrase alone and starts from what the person saved before it searches."""
    text, known = str(original or "").strip(), str(notes or "").strip()
    return PROMPT + (ORIGINAL.format(original=text[:ORIGINAL_LIMIT]) if text else "") + (NOTES.format(notes=known[:NOTES_LIMIT]) if known else "")


def helper_definition(model: Optional[str], original: str = "", notes: str = "") -> Dict[str, Dict[str, Any]]:
    """``{"helper": {description, prompt, tools, model}}``; empty when the sub-agent role's tier has no model chosen (it never runs on another tier). The prompt carries ``original``,
    the person's first message verbatim, and ``notes``, the saved-notes block a wrapper selected for the run."""
    if not model:
        return {}
    return {HELPER: {"description": DESCRIPTION, "prompt": helper_prompt(original, notes), "tools": list(HELPER_TOOLS), "model": model}}


def helper_note(calls: int) -> str:
    return NOTE.format(name=HELPER, calls=int(calls))


def sub_agent_model(model_of: Callable[[str], Optional[str]], requested: str = "", tier_of: Optional[Callable[..., str]] = None) -> Optional[str]:
    """The model of the ``sub_agent`` role's tier: the tier comes from the role table (``requested`` is the person's tier, which the table's own rule may follow), the model from the
    chooser through ``model_of(tier)``."""
    if tier_of is None:
        from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers
        tier_of = role_tiers.tier_for
    return model_of(tier_of(ROLE, requested))


def write_offer(scratch: str, seen: Callable[[str], str], python: str, defined: Dict[str, Dict[str, Any]], budget: int) -> Optional[Tuple[str, str, "agent_channel.AgentChannel"]]:
    """Write the agents file, the guard, the channel's hook and their settings into the session's private folder ``scratch``. Returns ``(agents file, settings file, channel)``, the
    paths as the session sees them (``seen``), or None when a file could not be written (the agents are offered only with the guard in place)."""
    paths = {name: os.path.join(scratch, name) for name in ("solution-agents.json", "agent-guard.py", "agent-hook.py", "agent-guard.json")}
    counter, record = os.path.join(scratch, "agent-calls.count"), os.path.join(scratch, "agent-calls.log")
    channel_folder = os.path.join(scratch, "agent-channel")
    try:
        channel = agent_channel.AgentChannel(channel_folder, seen(channel_folder))
        with open(paths["solution-agents.json"], "w", encoding="utf-8") as handle:
            json.dump(defined, handle, indent=1, sort_keys=True)
        with open(paths["agent-guard.py"], "w", encoding="utf-8") as handle:
            handle.write(agents.guard_script(sorted(defined), int(budget), seen(counter), seen(record)))
        with open(paths["agent-hook.py"], "w", encoding="utf-8") as handle:
            handle.write(agent_channel.hook_script(seen(channel_folder)))
        settings = agent_channel.merge_settings(agents.guard_settings(python, seen(paths["agent-guard.py"])), agent_channel.hook_settings(python, seen(paths["agent-hook.py"])))
        with open(paths["agent-guard.json"], "w", encoding="utf-8") as handle:
            json.dump(settings, handle, indent=1)
        if not os.path.exists(counter):
            with open(counter, "w", encoding="utf-8") as handle:
                handle.write("0")
    except OSError:
        return None
    return seen(paths["solution-agents.json"]), seen(paths["agent-guard.json"]), channel


__all__ = ["DEFAULT_CALLS", "HELPER", "HELPER_TOOLS", "ROLE", "helper_definition", "helper_note", "sub_agent_model", "write_offer"]
