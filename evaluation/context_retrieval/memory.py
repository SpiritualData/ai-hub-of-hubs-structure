"""Long-term conversational memory cases for the ``memory`` kind of ``context_retrieval``, from LongMemEval (Wu et al., ICLR 2025).

LongMemEval is MIT licensed (code and the cleaned dataset on Hugging Face, ``license: mit``), so a small sample is committed with the licence
notice (``datasets/memory/LICENSE-LongMemEval.txt``, ``NOTICE.md``). ``datasets/memory/pin.json`` names the upstream file (repository revision and the
sha256 of ``longmemeval_s_cleaned.json``) and the sha256 of the committed sample, checked on every use. ``build`` re-derives the sample from a
local copy of the upstream file, whose sha256 it checks against the pin (the file is 277 MB and is not needed to run the metric).

Each question of the benchmark has a history of timestamped chat sessions (user and assistant turns) of which some hold the evidence. The sample
keeps ``PER_TYPE`` questions of each type (knowledge update, temporal reasoning, multi-session, three single-session types) and ``ABSTENTION`` questions
whose answer was never said, and for each question its evidence sessions and ``DISTRACTORS`` other sessions of its history, chosen by a fixed hash.

A case's world is one user's history: every turn is an item (a file of the corpus) with metadata taken from the benchmark: kind ``message``, author
role (``requester`` for the user, ``assistant``), the session's timestamp, and the owner's scope tag. The request is the question, asked at the
question's date. Labels: a turn that holds the evidence (``has_answer``) is *needed*; for a knowledge-update question, the evidence turns of an
older session are *superseded* (the newer fact replaced them) and count as irrelevant; the other turns of a needed session are *helpful*;
an abstention question needs nothing, and the right answer is to return nothing.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cards_from_files import corpus as base  # noqa: E402

HERE = Path(__file__).resolve().parent / "datasets" / "memory"
PIN_FILE, SAMPLE_FILE = HERE / "pin.json", HERE / "sample.json"
UPSTREAM = "https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/resolve/{revision}/longmemeval_s_cleaned.json"
REVISION = "98d7416c24c778c2fee6e6f3006e7a073259d48f"
PER_TYPE = {"knowledge-update": 10, "temporal-reasoning": 10, "multi-session": 9, "single-session-user": 5, "single-session-assistant": 3,
            "single-session-preference": 3}
ABSTENTION = 7
DISTRACTORS = 10
DATE = re.compile(r"(\d{4})/(\d{2})/(\d{2}) \(\w+\) (\d{2}):(\d{2})")


class SampleMismatch(RuntimeError):
    """The committed sample is not the one its pin names."""


def iso(stamp: str) -> str:
    found = DATE.match(stamp)
    return "{}-{}-{}T{}:{}:00".format(*found.groups()) if found else stamp


def rank(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def build(source: Path, replace: bool = False) -> dict:
    """Derive ``sample.json`` and the pin from a local copy of the upstream file; refuses to replace a pin."""
    if PIN_FILE.exists() and not replace:
        raise SampleMismatch(f"{PIN_FILE.name} exists: the sample is pinned (pass replace=True to replace it on purpose)")
    raw = source.read_bytes()
    upstream_sha = hashlib.sha256(raw).hexdigest()
    data = json.loads(raw)
    chosen: List[dict] = []
    for qtype, quota in PER_TYPE.items():
        pool = sorted((q for q in data if q["question_type"] == qtype and not q["question_id"].endswith("_abs")), key=lambda q: rank(q["question_id"]))
        chosen += pool[:quota]
    chosen += sorted((q for q in data if q["question_id"].endswith("_abs")), key=lambda q: rank(q["question_id"]))[:ABSTENTION]
    sessions: Dict[str, list] = {}
    cases = []
    for q in chosen:
        evidence = set(q["answer_session_ids"])
        by_id = dict(zip(q["haystack_session_ids"], zip(q["haystack_dates"], q["haystack_sessions"])))
        others = sorted((s for s in by_id if s not in evidence), key=lambda s: rank(q["question_id"], s))[:DISTRACTORS]
        keep = [s for s in q["haystack_session_ids"] if s in evidence or s in others]     # the benchmark's own order
        for s in keep:
            sessions.setdefault(s, [[dict(role=t["role"], content=t["content"], has_answer=bool(t.get("has_answer"))) for t in by_id[s][1]]][0])
        cases.append(dict(id="MEM-" + q["question_id"], question_type=q["question_type"], abstention=q["question_id"].endswith("_abs"),
                          question=q["question"], question_date=iso(q["question_date"]), answer=str(q["answer"]),
                          evidence_sessions=sorted(evidence), haystack=[[s, iso(by_id[s][0])] for s in keep]))
    text = json.dumps({"source": "LongMemEval (longmemeval_s_cleaned), MIT licence, see LICENSE-LongMemEval.txt", "cases": cases, "sessions": sessions},
                      ensure_ascii=False, separators=(",", ":")) + "\n"
    SAMPLE_FILE.write_text(text, encoding="utf-8")
    pin = dict(upstream=UPSTREAM.format(revision=REVISION), revision=REVISION, licence="MIT", upstream_sha256=upstream_sha,
               sample_sha256=base.sha256_text(text), cases=len(cases), sessions=len(sessions),
               citation="Wu et al., LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory, ICLR 2025 (arXiv:2410.10813)")
    PIN_FILE.write_text(json.dumps(pin, indent=1) + "\n", encoding="utf-8")
    return pin


_SAMPLE: dict = {}


def sample() -> dict:
    if not _SAMPLE:
        text = SAMPLE_FILE.read_text(encoding="utf-8")
        pin = json.loads(PIN_FILE.read_text(encoding="utf-8"))
        if base.sha256_text(text) != pin["sample_sha256"]:
            raise SampleMismatch(f"{SAMPLE_FILE.name} has sha256 {base.sha256_text(text)}, the pin names {pin['sample_sha256']}")
        _SAMPLE.update(json.loads(text))
    return _SAMPLE


def turn_path(case_id: str, session: str, n: int, role: str) -> str:
    return f"{case_id}/{session}/t{n:02d}_{role}.txt"


def world_of(case: dict) -> Tuple[Dict[str, str], Dict[str, dict]]:
    """``(files, meta)`` of one user's history: one file per turn, with the benchmark's timestamp and role as metadata."""
    sessions = sample()["sessions"]
    files, meta = {}, {}
    for sid, stamp in case["haystack"]:
        for n, turn in enumerate(sessions[sid]):
            path = turn_path(case["id"], sid, n, turn["role"])
            files[path] = f"{turn['role']}: {turn['content']}"
            meta[path] = dict(kind="message", author_role="requester" if turn["role"] == "user" else turn["role"], timestamp=stamp,
                              scope_tags=[f"owner:{case['id']}"])
    return files, meta


def labels_of(case: dict) -> Tuple[List[str], List[str]]:
    """``(needed, helpful)`` turn paths of a case; a superseded fact (an older evidence session of a knowledge-update question) is neither."""
    if case["abstention"]:
        return [], []
    sessions, dates = sample()["sessions"], dict(case["haystack"])
    evidence = [s for s in case["evidence_sessions"] if s in dates]
    newest = max(dates[s] for s in evidence)
    needed, helpful = [], []
    anything = any(t["has_answer"] for sid in evidence for t in sessions[sid])      # a case with no marked turn at all needs its evidence sessions whole
    for sid in evidence:
        stale = case["question_type"] == "knowledge-update" and dates[sid] < newest
        marked = [n for n, t in enumerate(sessions[sid]) if t["has_answer"]]
        for n, turn in enumerate(sessions[sid]):
            path = turn_path(case["id"], sid, n, turn["role"])
            if stale:
                continue
            (needed if (n in marked or not anything) else helpful).append(path)
    return needed, helpful


def cases() -> List[dict]:
    out = []
    for c in sample()["cases"]:
        needed, helpful = labels_of(c)
        out.append(dict(c, kind="memory", task=c["question"], timestamp=c["question_date"], scope_tags=[f"owner:{c['id']}"],
                        needed=needed, helpful=helpful))
    return out


if __name__ == "__main__":
    print(build(Path(sys.argv[1]), replace="--replace" in sys.argv))
