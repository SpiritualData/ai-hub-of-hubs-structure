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
#: the calibration thresholds the judge must meet before layer 2 may break a layer 1 tie (written in the metric record on 2026-11-11, before the judge was run): of 12 pairs
MAX_MISSES = 2
MAX_FALSE_ALARMS = 1

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


WORKERS = 4      # the CLI calls that run at once (a lane that starts many claude processes at once times out)


def run_votes(call: Callable[[str, str], str], tier: str, frame: str, grid: str, run: int, checklist: Optional[Mapping[str, Any]] = None) -> Dict[str, bool]:
    """One run's verdicts for one frame (``run`` only tells the runs apart in a log)."""
    items = items_for(frame, checklist)
    text = "\n".join(f"- {i['id']}: {i['question']}" for i in items)
    return verdicts(call(PROMPT.format(frame=frame, grid=grid, items=text), tier), grid, items)


def majority(per_run: Sequence[Mapping[str, bool]]) -> Dict[str, bool]:
    ids = list(per_run[0]) if per_run else []
    return {i: sum(bool(r[i]) for r in per_run) * 2 > len(per_run) for i in ids}


def judge_frame(call: Callable[[str, str], str], tier: str, frame: str, grid: str, runs: int = RUNS, checklist: Optional[Mapping[str, Any]] = None) -> Dict[str, bool]:
    return majority([run_votes(call, tier, frame, grid, n, checklist) for n in range(runs)])


def ask_all(call: Callable[[str, str], str], tier: str, tasks: Sequence[Any], runs: int = RUNS, workers: int = WORKERS) -> Dict[Any, List[Dict[str, bool]]]:
    """``{key: [one verdict dict per run]}`` for tasks ``(key, frame, grid)``, the runs of all tasks spread over a few threads."""
    from concurrent.futures import ThreadPoolExecutor
    work = [(key, frame, grid, n) for key, frame, grid in tasks for n in range(runs)]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        done = list(pool.map(lambda w: (w[0], w[3], run_votes(call, tier, w[1], w[2], w[3])), work))
    out: Dict[Any, List[Dict[str, bool]]] = {key: [{}] * runs for key, _, _ in tasks}
    for key, n, got in done:
        out[key] = list(out[key])
        out[key][n] = got
    return out


def spread(shares: Sequence[float]) -> float:
    """The run-to-run spread of a share: the range over the runs."""
    return round(max(shares) - min(shares), 4) if shares else 0.0


def judge_arms(call: Callable[[str, str], str], frames_by_arm: Mapping[str, Mapping[str, str]], tier: str, seed: int = 0, runs: int = RUNS) -> Dict[str, Any]:
    """Judge every frame of every arm, arms blinded and the order shuffled. Returns the yes share by majority, the share of each run and its spread, and the per-item results:
    ``{"share": {arm: share}, "run_shares": {arm: [per run]}, "spread": {arm: range}, "items": {arm: {frame: {item: bool}}}, "order": [...]}``."""
    rng = random.Random(seed)
    arms = sorted(frames_by_arm)
    labels = dict(zip(rng.sample(arms, len(arms)), "ABCDEFGHIJKLMNOP"))
    jobs = [(arm, frame) for arm in arms for frame in frames_by_arm[arm]]
    rng.shuffle(jobs)
    # the judge sees the label, never the arm's name
    got = ask_all(call, tier, [((arm, frame), frame, frames_by_arm[arm][frame].replace(arm, labels[arm])) for arm, frame in jobs], runs)
    result: Dict[str, Dict[str, Dict[str, bool]]] = {arm: {} for arm in arms}
    run_shares: Dict[str, List[float]] = {}
    for arm in arms:
        for frame in frames_by_arm[arm]:
            result[arm][frame] = majority(got[(arm, frame)])
        counts = [(sum(v for frame in frames_by_arm[arm] for v in got[(arm, frame)][n].values()), sum(len(got[(arm, frame)][n]) for frame in frames_by_arm[arm])) for n in range(runs)]
        run_shares[arm] = [round(yes / max(total, 1), 4) for yes, total in counts]
    share = {arm: round(sum(v for f in rows.values() for v in f.values()) / max(sum(len(f) for f in rows.values()), 1), 4) for arm, rows in result.items()}
    return {"share": share, "run_shares": run_shares, "spread": {arm: spread(s) for arm, s in run_shares.items()}, "items": result, "order": [f"{labels[a]}:{f}" for a, f in jobs],
            "checklist": checklist_digest(), "advisory": True}


def breaks_a_tie(result: Mapping[str, Any], incumbent: str, rival: str) -> str:
    """The arm layer 2 prefers between two arms that tied on layer 1: the rival only when its share beats the incumbent's by more than the larger of the two arms' run-to-run spreads;
    otherwise the incumbent stays."""
    gap = result["share"][rival] - result["share"][incumbent]
    return rival if gap > max(result["spread"][incumbent], result["spread"][rival]) else incumbent


def calibrate(call: Callable[[str, str], str], tier: str, runs: int = RUNS) -> Dict[str, Any]:
    """The judge's own error on the calibration set: ``miss_rate`` is the share of injected defects it called fine, ``false_alarm_rate`` the share of clean frames' items
    (the ones a defect was cut from) it called a failure. Read every arm's layer 2 number with these."""
    from judged.calibration import load_calibration
    missed = alarms = defects = clean = 0
    detail = []
    cases = load_calibration()
    got_all = ask_all(call, tier, [((case["id"], kind), case["frame"], case[column]) for case in cases for kind, column in (("clean", "clean"), ("defect", "defective"))], runs)
    for case in cases:
        for kind in ("clean", "defect"):
            got = majority(got_all[(case["id"], kind)])[case["item"]]
            if kind == "defect":
                defects += 1
                missed += bool(got)
            else:
                clean += 1
                alarms += not got
            detail.append((case["id"], kind, got))
    return {"miss_rate": round(missed / max(defects, 1), 4), "false_alarm_rate": round(alarms / max(clean, 1), 4), "defects": defects, "clean": clean, "detail": detail,
            "checklist": checklist_digest()}


def default_caller(spend: Optional[List[float]] = None) -> Callable[[str, str], str]:
    """A caller through the Claude CLI at the tier the role table gives (never run by the metric; for a person who asks for layer 2). It runs on the CLI's own login (the process
    gets HOME and PATH only, so no API key reaches it); each call's cost as the CLI reports it (a list-price estimate on a subscription) is appended to ``spend``."""
    import os
    import subprocess
    from hubofhubs.api import model_for

    def call(prompt: str, tier: str) -> str:
        env = {n: os.environ[n] for n in ("HOME", "PATH") if n in os.environ}
        for attempt in range(2):
            try:
                done = subprocess.run(["claude", "-p", "--output-format", "json", "--model", model_for("anthropic", tier), "--setting-sources", "", "--strict-mcp-config", "--max-turns", "1"],
                                      input=prompt, capture_output=True, text=True, timeout=300, env=env)
                data = json.loads(done.stdout)
            except (subprocess.TimeoutExpired, ValueError):
                continue
            if spend is not None:
                spend.append(float(data.get("total_cost_usd") or 0.0))
            return data.get("result", "")
        return ""
    return call


def role_tier() -> str:
    from hubofhubs.the_world.model_plumbing.model_tier_chooser.role_tiers import tier_for
    return tier_for(ROLE)
