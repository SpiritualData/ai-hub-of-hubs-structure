"""Scores a Terminal Experience arm on how its screen is drawn (layer 1 of the presentation metric): deterministic, free, no model.

Each case runs one scripted session on a fake harness at 80x24 and 120x40 and judges the screen as drawn (``screen.py``: the terminal emulator pyte for an arm that writes
to a stream, Textual's ``run_test`` for a Textual arm) with named checks (``checks.py``), each tied to requirements X1 to X33. A case scores the weighted share of the checks that
applied to it and passed (weights: ``[balance.terminal_presentation.check_weights]`` in esoi.toml, fixed before any arm was scored) and is ``ok`` when none failed; the
balanced score is ``[balance.terminal_presentation]``. A check that does not apply (None) or was not run is left out and listed. The protocol ceiling column (what a surface
cannot show at all) is reported in the details and is not part of the score. This does not replace ``terminal_session``, the correctness gate."""
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import checks as C  # noqa: E402
import scenarios as S  # noqa: E402

CONFIG = HERE.parent.parent / "esoi.toml"


def weights():
    return {k: int(v) for k, v in tomllib.loads(CONFIG.read_text())["balance"]["terminal_presentation"]["check_weights"].items()}


def adapt(implementation, meter):
    arm = implementation()

    def run(kind, args):
        return S.run_scenario(arm, args["scenario"])
    return run


def score_case(fn, case):
    got = fn(case["kind"], case["args"])
    table = weights()
    not_run = set(got.get("not_run", ()))
    applied = {k: v for k, v in got.get("checks", {}).items() if v is not None and k not in not_run}
    failed = sorted(k for k, v in applied.items() if not v)
    total = sum(table[k] for k in applied)
    share = sum(table[k] for k, v in applied.items() if v) / total if total else 0.0
    ceiling = got.get("ceiling", {})
    ok = bool(applied) and not failed
    return dict(ok=ok, score=round(share, 4), got=",".join(failed)[:60] or "none failed", note="" if ok else "failed: " + (", ".join(failed) or "nothing could be checked") + (" | " + got["note"] if got.get("note") else ""),
                kind=case["kind"], requirements=case.get("requirements", []), checks={k: v for k, v in got.get("checks", {}).items()}, ceiling=ceiling,
                not_run=sorted(not_run), not_applicable=sorted(k for k, v in got.get("checks", {}).items() if v is None))


def aggregate(rows):
    per = {}
    for r in rows:
        for name, value in r.get("checks", {}).items():
            if value is None:
                continue
            ok, total = per.get(name, (0, 0))
            per[name] = (ok + bool(value), total + 1)
    ceiling = {}
    for r in rows:
        for name, value in r.get("ceiling", {}).items():
            ok, total = ceiling.get(name, (0, 0))
            ceiling[name] = (ok + bool(value), total + 1)
    out = {name: f"{ok}/{total}" for name, (ok, total) in sorted(per.items())}
    out["ceiling_shown"] = f"{sum(o for o, _ in ceiling.values())}/{sum(t for _, t in ceiling.values())}"
    out.update({"ceiling:" + name: f"{ok}/{total}" for name, (ok, total) in sorted(ceiling.items())})
    skipped = sorted({n for r in rows for n in r.get("not_run", [])} | {n for r in rows for n in r.get("not_applicable", [])})
    if skipped:
        out["left_out"] = "+".join(skipped)
    return out
