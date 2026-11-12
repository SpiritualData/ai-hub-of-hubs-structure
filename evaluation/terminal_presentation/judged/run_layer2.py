"""Run layer 2 on request: the judge's calibration first, then (only if it meets the thresholds written in the metric record) the arms' six frames, blinded and shuffled, three runs
each, majority per item. Writes ``layer2_results.json`` beside this file and prints the spend as the CLI reports it. Not run by the metric or by any test.

    python3 evaluation/terminal_presentation/judged/run_layer2.py live_session textual_session polished_session

The judge runs through the Claude CLI on its own login at the tier the role table gives the role ``deliverable_judge``."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent.parent.parent))

from judged import frames, judge  # noqa: E402


def arm_named(name):
    from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.work import terminal_arm
    return terminal_arm(name, {})[0]


def main(names):
    spend = []
    call = judge.default_caller(spend)
    tier = judge.role_tier()
    out = {"tier": tier, "role": judge.ROLE, "checklist": judge.checklist_digest(), "thresholds": {"max_misses": judge.MAX_MISSES, "max_false_alarms": judge.MAX_FALSE_ALARMS}}
    cal = judge.calibrate(call, tier)
    misses, alarms = round(cal["miss_rate"] * cal["defects"]), round(cal["false_alarm_rate"] * cal["clean"])
    out["calibration"] = {"misses": misses, "false_alarms": alarms, "defects": cal["defects"], "clean": cal["clean"], "detail": cal["detail"]}
    out["calibration_met"] = misses <= judge.MAX_MISSES and alarms <= judge.MAX_FALSE_ALARMS
    print(f"calibration: {misses} of {cal['defects']} defects missed, {alarms} of {cal['clean']} clean frames called a failure; met={out['calibration_met']}")
    if out["calibration_met"]:
        grids = {name: frames.frames_of(arm_named(name)) for name in names}
        out["layer2"] = judge.judge_arms(call, grids, tier)
        print(json.dumps({k: out["layer2"][k] for k in ("share", "run_shares", "spread")}, indent=1))
    out["spend_usd"] = round(sum(spend), 4)
    out["calls"] = len(spend)
    (HERE / "layer2_results.json").write_text(json.dumps(out, indent=1, default=str) + "\n")
    print(f"calls: {len(spend)}, spend as the CLI reports it: ${out['spend_usd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
