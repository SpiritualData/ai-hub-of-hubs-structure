"""Freeze the calibration set: the six frames of the reference terminal, then one defect each (``calibration.DEFECTS``). Run once, review the pairs, commit the json.

    python3 evaluation/terminal_presentation/judged/build_calibration.py"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))
sys.path.insert(0, str(HERE.parent.parent.parent))

from judged import calibration, frames  # noqa: E402
from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.live import LiveSession  # noqa: E402

if __name__ == "__main__":
    clean = frames.frames_of(LiveSession())
    cases = calibration.build(clean)
    skipped = sorted({d[0] for d in calibration.DEFECTS} - {c["id"] for c in cases})
    calibration.FROZEN.write_text(json.dumps({"source": "the reference terminal (live_session), scripted sessions, no model", "left_out": skipped, "cases": cases}, indent=1) + "\n")
    print(len(cases), "pairs; left out:", skipped)
