"""The hub's answer check after a session: did the final answer do what the person's own words asked, about the subject they named?

Role: the code check (``code_check``) reads files; a run whose result is an answer (a finding, an opinion, an explanation) writes none, so a session could end "met" with an answer
about something else (material a helper picked up that was about another subject). After the session reports, one short call on the fast tier is given ONLY the person's original input,
verbatim (the first message of the session, never a restated goal), and the final answer, and returns a small verdict: the asked parts of the input, each met or unmet with a short
reason, whether the answer is about the subject the input named, whether it invents a different task, and an overall pass that this module computes from those (a model's own "pass"
is never trusted). On a fail the same session is resumed once with a steer built from the original input and the unmet parts (``steer_message``), through the resume path of the
runner that called (its resume limit and ceilings apply; ``run_round`` is given them as ``allowed``). A check that cannot run or cannot be read is no opinion: the answer stands.
The tier comes from the ``answer_check`` role of the role table; no model is named here. Standard library only; the model call is injected (``ask``) or built from the hub's
Claude CLI provider on first use."""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

ROLE = "answer_check"
FALLBACK_TIER = "fast"
INPUT_LIMIT = 4000
ANSWER_LIMIT = 7000

SYSTEM = ("You check whether an answer does what a person asked. You are given the person's request, word for word, and the answer that was given. Judge the answer against the request "
          "only, never against anything else. Reply with JSON only, no other text, no em dashes.")

PROMPT = """REQUEST (the person's own words, the only reference):
<<<
{request}
>>>

ANSWER:
<<<
{answer}
>>>

Do this:
1. Split the request into the parts it asks for, each a short phrase (for example "use a helper", "find something about X", "give your own opinion on what it finds"). Keep them in the order asked. A request that asks one thing has one part.
2. For each part say whether the answer itself does it. A part is met only when the answer contains the doing (the finding, the opinion, the explanation), not a promise, a plan or a list of questions for the person. A part that asks the answer to find something is met when the answer gives it, or says plainly and specifically what was looked at and that nothing relevant was found; a vague or invented finding is unmet. A part about HOW the work was done (use a helper, search the web, read a file) cannot be seen in the answer: count it met unless the answer says it was not done, and judge only the parts that ask for something in the answer itself.
3. Name the subject the request is about, in a few words ("subject"). Say whether the answer is about that subject ("about_subject"): an answer built on material about something else, or that spends its length on another topic, is not.
4. Say whether the answer invents a different task than the one asked, such as decisions, plans or changes for another project that nobody asked about ("invents_task").

Reply with exactly this JSON shape:
{{"parts": [{{"part": "...", "met": true, "reason": "one short sentence"}}], "subject": "...", "about_subject": true, "invents_task": false}}"""

STEER = ("The request was: {request}\n"
         "{misses}"
         "Answer it directly, as your own answer to those words. If the material you found is about something else, say so and look again.")


def clip(text: str, limit: int) -> str:
    """``text`` kept to ``limit`` characters, the middle left out when it is longer (the start and the end of an answer carry what it says)."""
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    half = limit // 2
    return text[:half] + "\n[...]\n" + text[-half:]


def as_flag(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "yes", "1")
    return default


def parse_verdict(raw: Any) -> Optional[Dict[str, Any]]:
    """The verdict in a model's reply: ``{parts: [{part, met, reason}], subject, about_subject, invents_task, passed}``; None when the reply holds no readable parts.
    ``passed`` is computed here: every part met, the answer about the subject, no invented task."""
    text = str(raw or "")
    try:
        data = json.loads(text[text.index("{"):text.rindex("}") + 1])
    except (ValueError, TypeError):
        return None
    if not isinstance(data, Mapping):
        return None
    parts: List[Dict[str, Any]] = []
    for item in data.get("parts") or []:
        if isinstance(item, Mapping) and str(item.get("part") or "").strip():
            parts.append({"part": str(item["part"]).strip(), "met": as_flag(item.get("met"), True), "reason": str(item.get("reason") or "").strip()})
    if not parts:
        return None
    about = as_flag(data.get("about_subject"), True)
    invents = as_flag(data.get("invents_task"), False)
    return {"parts": parts, "subject": str(data.get("subject") or "").strip(), "about_subject": about, "invents_task": invents,
            "passed": all(p["met"] for p in parts) and about and not invents}


def judge(original_input: str, answer: str, ask: Callable[[str, str], str]) -> Optional[Dict[str, Any]]:
    """One call: the verdict on ``answer`` against ``original_input`` (see ``parse_verdict``), or None when there is nothing to judge or the call or its reply failed.
    ``ask(system, prompt)`` returns the reply text."""
    if not str(original_input or "").strip() or not str(answer or "").strip():
        return None
    try:
        reply = ask(SYSTEM, PROMPT.format(request=clip(original_input, INPUT_LIMIT), answer=clip(answer, ANSWER_LIMIT)))
    except Exception:  # noqa: BLE001 -- a failed call is no opinion
        return None
    return parse_verdict(reply)


def unmet_parts(verdict: Mapping[str, Any]) -> List[str]:
    return [str(p["part"]) for p in verdict.get("parts") or [] if not p.get("met")]


def steer_message(original_input: str, verdict: Mapping[str, Any]) -> str:
    """The resumed turn's message: the request in the person's own words, and what the answer did not do."""
    lines = []
    for part in verdict.get("parts") or []:
        if not part.get("met"):
            lines.append(f"Your answer did not {part['part']}" + (f" ({part['reason'].rstrip('.')})" if part.get("reason") else "") + ".")
    subject = str(verdict.get("subject") or "").strip()
    if not verdict.get("about_subject", True):
        lines.append("Your answer was not about " + (subject if subject else "the subject the request named") + ".")
    if verdict.get("invents_task"):
        lines.append("Your answer took on a task the request did not ask for.")
    return STEER.format(request=str(original_input).strip(), misses=("\n".join(lines) + "\n") if lines else "")


def resume_reason(verdict: Mapping[str, Any]) -> str:
    """The plain reason a person reads on the line that says the session is resumed."""
    unmet = unmet_parts(verdict)
    if unmet:
        return "the answer did not " + "; did not ".join(unmet[:2])
    if not verdict.get("about_subject", True):
        return "the answer was about something other than what you asked"
    return "the answer took on a task you did not ask for"


def answer_ask(model_of: Callable[[str], Optional[str]], requested: str = "", tier_of: Optional[Callable[..., str]] = None,
               claude_path: str = "claude") -> Optional[Callable[[str, str], str]]:
    """The model call of the check on the ``answer_check`` role's tier (the fast tier when the table has no row for it), through the hub's Claude CLI provider; None when no model is
    chosen for the tier. ``model_of(tier)`` gives the model of a tier."""
    if tier_of is None:
        from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers
        tier_of = role_tiers.tier_for
    try:
        tier = tier_of(ROLE, requested)
    except (KeyError, ValueError):
        tier = FALLBACK_TIER
    model = model_of(tier)
    if not model:
        return None
    from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
    engine = ClaudeCliProvider(claude_path=claude_path)      # the program the run itself uses
    return lambda system, prompt: engine.answer([{"role": "user", "content": prompt}], model=model, system=system)


def run_round(original_input: str, answer: str, ask: Optional[Callable[[str, str], str]], resume: Callable[[str], Any], *, allowed: Callable[[], str] = lambda: "",
          emit: Optional[Callable[[str, str, Mapping[str, Any]], None]] = None) -> Dict[str, Any]:
    """One answer-check round. Judges ``answer`` against ``original_input``; on a fail asks ``allowed()`` (an empty string: the runner's resume limit and ceilings allow another
    resume, else the reason it does not) and, when allowed, calls ``resume(steer)``, which resumes the session and returns the new answer text (None when it failed), and judges
    that once more. ``emit(phase, text, data)`` tells a watcher. Returns the record: ``verdict``, ``resumed``, ``skipped`` (why no resume), ``after`` (the second verdict), ``answer``
    (the answer to keep: the resumed one when it came back, else the first)."""
    record: Dict[str, Any] = {"input": original_input, "verdict": None, "resumed": False, "skipped": "", "after": None, "answer": answer}
    if ask is None:
        record["skipped"] = "no model for the check"
        return record
    verdict = judge(original_input, answer, ask)
    record["verdict"] = verdict
    if verdict is None:
        record["skipped"] = "the check gave no readable verdict"
        return record
    if emit is not None:
        emit("answer_check", "answer check: " + ("passed" if verdict["passed"] else resume_reason(verdict)), {"verdict": verdict})
    if verdict["passed"]:
        return record
    reason = allowed()
    if reason:
        record["skipped"] = reason
        return record
    if emit is not None:
        emit("hub_resume", "The answer did not do what was asked; the session is resumed once more.", {"reason": resume_reason(verdict)})
    record["resumed"] = True
    new = resume(steer_message(original_input, verdict))
    if new and str(new).strip():
        record["answer"] = str(new)
        record["after"] = judge(original_input, str(new), ask)
        if emit is not None and record["after"] is not None:
            emit("answer_check", "answer check after the resume: " + ("passed" if record["after"]["passed"] else resume_reason(record["after"])), {"verdict": record["after"]})
    return record


__all__ = ["ROLE", "answer_ask", "judge", "parse_verdict", "resume_reason", "run_round", "steer_message", "unmet_parts"]
