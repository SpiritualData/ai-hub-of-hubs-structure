"""Scores a Delegated Agent Sessions arm on hard work: real deep tasks that take minutes and fail on a weak tier.

The case bodies are private (see ``build_cases.py``); ``cases.json`` holds only their ids and digests, and a body whose digest differs from
its stub is refused, so a result always names the case set it ran on. Two kinds:

* ``code``: a small multi-file package with a bug or a missing feature, the tests the agent is shown, and hidden tests written to the same
  rules the goal states. After the run every test file is written back from the case and all of them run in a new process. Pass = every
  test passes and the files the goal did not open to change are unchanged.
* ``deliverable``: a milestone turn's real records and the request; the agent writes the deliverable file. A judge on the strongest
  Anthropic tier rates each rubric item pass or fail and must quote the words that decide it; a pass whose quote is in neither the
  deliverable nor the records does not count (the per-item rule of the chat-quality judge). Pass = every item passes, plus the word range.

Arms, credentials and cost are as in ``agent_sessions`` (whose ``adapt`` this reuses with a longer time limit). The judge's own cost is
not the arm's and is not metered. An arm may carry an instructions pack (``instructions=<name>``); the text of ``<name>.md`` is read from
the folders ``AGENT_INSTRUCTION_PACKS`` names, which stay outside this repository when the text's licence does not allow it here.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent_sessions import score as base   # noqa: E402
from agent_sessions_hard.build_cases import digest, private_cases   # noqa: E402

AGENT_SECONDS = 900
JUDGE_SECONDS = 300
JUDGE_TIER = "best"
EVIDENCE_CHARS = 400000   # every case's records whole: a judge shown only the first records fails a true citation of a later one
PACKS_ENV = "AGENT_INSTRUCTION_PACKS"
KEEP_ENV = "AGENT_SESSIONS_HARD_KEEP"


def pack_text(name):
    for folder in filter(None, os.environ.get(PACKS_ENV, "").split(os.pathsep)):
        path = Path(folder, f"{name}.md")
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return ""


def adapt(implementation, meter):
    """As ``agent_sessions.score.adapt``, with this stage's time limit and the instructions packs readable."""
    base.AGENT_SECONDS = AGENT_SECONDS
    settings = base.agent_settings(implementation)
    import dataclasses
    settings = dataclasses.replace(settings, instruction_pack=pack_text)

    def run(kind, args):
        runner = implementation(base.agent_config(args["root"]), settings=settings)
        meter.model = getattr(runner, "model", None) or getattr(runner, "tier_model", None) or "default"
        result = runner.run_goal(goal=args["goal"], brief=args["goal"], max_turns=60)
        meter.record()
        meter.cost_usd += float(getattr(result, "cost_usd", 0.0) or 0.0)
        return result
    return run


def body(stub):
    found = private_cases().get(stub["id"])
    if found is None:
        raise RuntimeError(f"case {stub['id']} is not in the private folders named by AGENT_SESSIONS_HARD_CASES")
    if digest(found[1]) != stub["digest"]:
        raise RuntimeError(f"case {stub['id']} changed since cases.json was written: run build_cases.py")
    case = json.loads(found[1])
    case["private_folder"] = str(found[0].parent.parent)
    return case


def squash(text):
    """Lowercase words with markdown marks and quotation marks dropped, so a quote matches the text it quotes however it was laid out."""
    text = re.sub(r"['\u2018\u2019]", "", str(text or "").lower())
    text = re.sub(r"[#*_`>\"\u201c\u201d]", " ", text)
    return " ".join(text.split())


def quoted(quote, evidence):
    """Whether every piece of ``quote`` (pieces joined by an ellipsis or a line break in the judge's quote) is in ``evidence``."""
    pieces = [squash(p) for p in re.split(r"\.\.\.|\u2026|\n|\s/\s", str(quote or ""))]
    pieces = [p.strip(" -:;,.") for p in pieces if len(p.strip(" -:;,.")) >= 3]
    return bool(pieces) and all(p in evidence for p in pieces)


JUDGE_PROMPT = """You judge one deliverable against its rubric. For each rubric item decide pass or fail from the evidence only, and quote
the exact words (from the deliverable, or from the records for an item about what the records hold) that decide it. Pass only when the
evidence shows the item is met. Reply with JSON only: {{"items": [{{"item": "<the item>", "verdict": "pass" or "fail", "quote": "<exact words>"}}]}}

REQUEST: {goal}

RUBRIC ITEMS:
{items}

THE DELIVERABLE ({file}):
{deliverable}

THE RECORDS THE AGENT HAD:
{records}
"""


def judge(case, deliverable):
    """[(item, ok, why)] from one judge call on the strongest Anthropic tier; a pass whose quote is not in the evidence fails."""
    from hubofhubs.api import model_for
    records = "\n\n".join(f"--- {n}\n{t}" for n, t in case["files"].items())[:EVIDENCE_CHARS]
    prompt = JUDGE_PROMPT.format(goal=case["goal"], items="\n".join(f"- {i}" for i in case["rubric"]["items"]),
                                 file=case["rubric"]["file"], deliverable=deliverable, records=records)
    env = {n: os.environ[n] for n in ("HOME", "PATH") if n in os.environ}
    for attempt in range(2):
        try:
            done = subprocess.run(["claude", "-p", "--output-format", "json", "--model", model_for("anthropic", JUDGE_TIER),
                                   "--setting-sources", "", "--strict-mcp-config", "--max-turns", "1"],
                                  input=prompt, capture_output=True, text=True, timeout=JUDGE_SECONDS, env=env)
            reply = json.loads(done.stdout).get("result", "")
            verdicts = json.loads(re.search(r"\{.*\}", reply, re.S).group(0))["items"]
            break
        except (subprocess.TimeoutExpired, ValueError, AttributeError, KeyError, TypeError):
            verdicts = None
    if verdicts is None:
        return [(i, False, "the judge gave no readable verdict", "") for i in case["rubric"]["items"]]
    evidence = squash(deliverable) + " " + squash(records)
    out = []
    for item, verdict in zip(case["rubric"]["items"], verdicts + [{}] * len(case["rubric"]["items"])):
        ok = verdict.get("verdict") == "pass" and quoted(verdict.get("quote"), evidence)
        why = "" if ok else ("judged fail" if verdict.get("verdict") != "pass" else "the quote is not in the evidence")
        out.append((item, ok, why, str(verdict.get("quote") or "")[:400]))
    return out


def keep(case, text, verdicts):
    """Save a deliverable and its verdicts for reading by hand, in ``kept/`` of the private folder the case came from, when
    ``AGENT_SESSIONS_HARD_KEEP`` is set (a case never leaves its own private folder)."""
    if os.environ.get(KEEP_ENV, ""):
        out = Path(case["private_folder"], "kept", f"{case['id']}-{os.getpid()}.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"deliverable": text, "verdicts": verdicts}, indent=1), encoding="utf-8")


def score_case(fn, stub):
    case = body(stub)
    root = Path(tempfile.mkdtemp(prefix="agent_session_hard_"))
    try:
        base.write_files(root, case["files"])
        base.write_files(root, case.get("tests", {}))
        result = fn(case["stratum"], dict(root=str(root), goal=case["goal"]))
        report = str(getattr(result, "output", "") or "")
        fixed = {n: t for n, t in case["files"].items() if n not in case.get("editable", [])}
        changed = [n for n, t in fixed.items() if not (root / n).is_file() or (root / n).read_text(encoding="utf-8") != t]
        problems = [f"files changed: {changed}"] if changed else []
        if case["stratum"] == "code":
            base.write_files(root, case["tests"])
            base.write_files(root, case["hidden_tests"])
            ok, last = base.run_tests(root, sorted(list(case["tests"]) + list(case["hidden_tests"])))
            problems += [] if ok else [f"tests fail: {last}"]
        else:
            rubric = case["rubric"]
            problems += base.rubric_problems(root, {"file": rubric["file"], "min_words": rubric.get("min_words", 0),
                                                    "max_words": rubric.get("max_words", 10 ** 9)})
            target = root / rubric["file"]
            if target.is_file():
                text = target.read_text(encoding="utf-8", errors="replace")
                verdicts = judge(case, text)
                keep(case, text, verdicts)
                failed = [f"{item} ({why})" for item, ok, why, _ in verdicts if not ok]
                problems += [f"rubric fails: {failed}"] if failed else []
        met = bool(getattr(result, "met", False))
        ok = met and not problems
        note = "" if ok else (getattr(result, "error", None) or "; ".join(problems) or "the run did not meet the goal")
        return dict(ok=ok, got=report[:60], note=str(note)[:300])
    finally:
        shutil.rmtree(root, ignore_errors=True)
