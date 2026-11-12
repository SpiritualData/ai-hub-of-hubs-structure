"""Layer 2 of the presentation metric: a model judges fixed frames against a frozen checklist. ADVISORY ONLY: it never gates and never enters the balanced score, because
published studies find model-judged usability evaluation unreliable (Guerino et al. 2025, arXiv 2506.16345: 21.2% of the issues experts found were found, with false positives
from speculation; Zhong et al. 2025, arXiv 2507.02306 found more issues than experts on app screenshots but weak on conventions and cross-screen problems and says so). So the
judge is measured before it is believed: ``calibrate`` runs it on frames with injected defects and reports its miss rate and its false-alarm rate.

How a judgement is made: each frame is judged with only the checklist items that apply to it; a ``yes`` counts only when its quote is found in the frame (a pass whose quote is
not in the frame is a no); three runs, the majority decides; arms are blinded (labelled A, B, ...) and the frames of all arms are asked in a shuffled order; the tier comes
from the hub's role table for the role ``deliverable_judge`` (no model is named here). ``call(prompt, tier) -> reply text`` is passed in; nothing here runs a model by itself, and
the harness has NOT been run on any arm (a live arm is never run just to fill a row)."""
from __future__ import annotations

import hashlib
import json
import random
import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence

HERE = Path(__file__).resolve().parent
ROLE = "deliverable_judge"
RUNS = 3

PROMPT = """You review one screen of a terminal program that shows an AI working. The screen is a text grid: a box of the terminal's size, each row followed by its number.
Answer each question below with "yes" or "no". Answer "yes" only when you can quote, word for word, the text on the screen that shows it; put that quote in "quote". Do not
guess what a screen might do; judge only what is drawn. Reply with JSON only: {{"items": [{{"id": "...", "verdict": "yes" or "no", "quote": "..."}}]}}

Screen ({frame}):
{grid}

Questions:
{items}
"""


def load_checklist(path: Path = HERE / "checklist.json") -> Dict[str, Any]:
    return json.loads(path.read_text())


def checklist_digest(path: Path = HERE / "checklist.json") -> str:
    """The digest of the frozen checklist: a result names it, so no result is read against another version."""
    return hashlib.sha256(json.dumps(load_checklist(path)["items"], sort_keys=True).encode()).hexdigest()[:12]


def squash(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def frame_text(grid: str) -> str:
    """The words on the screen: the grid without its rules, borders and row numbers."""
    rows = [re.sub(r"^\|(.*)\|\s*\d+$", r"\1", line) for line in grid.splitlines() if line.startswith("|")]
    return "\n".join(rows)


def items_for(frame: str, checklist: Optional[Mapping[str, Any]] = None) -> List[Dict[str, Any]]:
    return [item for item in (checklist or load_checklist())["items"] if frame in item["frames"]]


def parse(reply: str) -> List[Dict[str, Any]]:
    try:
        return json.loads(re.search(r"\{.*\}", reply, re.S).group(0))["items"]
    except (AttributeError, ValueError, KeyError, TypeError):
        return []


def verdicts(reply: str, grid: str, items: Sequence[Mapping[str, Any]]) -> Dict[str, bool]:
    """``{item id: bool}`` from one reply: a yes whose quote is not in the frame, or an item left unanswered, is a no."""
    words = squash(frame_text(grid))
    said = {str(v.get("id")): v for v in parse(reply) if isinstance(v, dict)}
    out = {}
    for item in items:
        v = said.get(item["id"], {})
        quote = squash(str(v.get("quote") or ""))
        out[item["id"]] = v.get("verdict") == "yes" and bool(quote) and quote in words
    return out


def judge_frame(call: Callable[[str, str], str], tier: str, frame: str, grid: str, runs: int = RUNS, checklist: Optional[Mapping[str, Any]] = None) -> Dict[str, bool]:
    items = items_for(frame, checklist)
    text = "\n".join(f"- {i['id']}: {i['question']}" for i in items)
    votes: Dict[str, Counter] = {i["id"]: Counter() for i in items}
    for _ in range(runs):
        for item_id, ok in verdicts(call(PROMPT.format(frame=frame, grid=grid, items=text), tier), grid, items).items():
            votes[item_id][ok] += 1
    return {item_id: count[True] > count[False] for item_id, count in votes.items()}


def judge_arms(call: Callable[[str, str], str], frames_by_arm: Mapping[str, Mapping[str, str]], tier: str, seed: int = 0, runs: int = RUNS) -> Dict[str, Any]:
    """Judge every frame of every arm, arms blinded and the order shuffled. Returns ``{"share": {arm: yes share}, "items": {arm: {frame: {item: bool}}}, "order": [...]}``."""
    rng = random.Random(seed)
    arms = sorted(frames_by_arm)
    labels = dict(zip(rng.sample(arms, len(arms)), "ABCDEFGHIJKLMNOP"))
    jobs = [(arm, frame) for arm in arms for frame in frames_by_arm[arm]]
    rng.shuffle(jobs)
    result: Dict[str, Dict[str, Dict[str, bool]]] = {arm: {} for arm in arms}
    for arm, frame in jobs:       # the judge sees the label, never the arm's name
        result[arm][frame] = judge_frame(call, tier, frame, frames_by_arm[arm][frame].replace(arm, labels[arm]), runs)
    share = {arm: round(sum(v for f in rows.values() for v in f.values()) / max(sum(len(f) for f in rows.values()), 1), 4) for arm, rows in result.items()}
    return {"share": share, "items": result, "order": [f"{labels[a]}:{f}" for a, f in jobs], "checklist": checklist_digest(), "advisory": True}


def calibrate(call: Callable[[str, str], str], tier: str, runs: int = RUNS) -> Dict[str, Any]:
    """The judge's own error on the calibration set: ``miss_rate`` is the share of injected defects it called fine, ``false_alarm_rate`` the share of clean frames' items
    (the ones a defect was cut from) it called a failure. Read every arm's layer 2 number with these."""
    from judged.calibration import load_calibration
    missed = alarms = defects = clean = 0
    detail = []
    for case in load_calibration():
        for kind, grid in (("clean", case["clean"]), ("defect", case["defective"])):
            got = judge_frame(call, tier, case["frame"], grid, runs)[case["item"]]
            if kind == "defect":
                defects += 1
                missed += bool(got)
            else:
                clean += 1
                alarms += not got
            detail.append((case["id"], kind, got))
    return {"miss_rate": round(missed / max(defects, 1), 4), "false_alarm_rate": round(alarms / max(clean, 1), 4), "defects": defects, "clean": clean, "detail": detail,
            "checklist": checklist_digest()}


def default_caller() -> Callable[[str, str], str]:
    """A caller through the Claude CLI at the tier the role table gives (never run by the metric; for a person who asks for layer 2)."""
    import os
    import subprocess
    from hubofhubs.api import model_for

    def call(prompt: str, tier: str) -> str:
        env = {n: os.environ[n] for n in ("HOME", "PATH") if n in os.environ}
        done = subprocess.run(["claude", "-p", "--output-format", "json", "--model", model_for("anthropic", tier), "--setting-sources", "", "--strict-mcp-config", "--max-turns", "1"],
                              input=prompt, capture_output=True, text=True, timeout=300, env=env)
        return json.loads(done.stdout).get("result", "")
    return call


def role_tier() -> str:
    from hubofhubs.the_world.model_plumbing.model_tier_chooser.role_tiers import tier_for
    return tier_for(ROLE)
