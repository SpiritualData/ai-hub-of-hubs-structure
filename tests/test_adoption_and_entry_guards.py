"""Two guards so a solution cannot be crowned among alternatives that leave out the best that exists (principle 8 of the evolvable-structure skill).

(a) Adoption: every registry finding in an area that maps to a solution is either referenced by an arm of that solution (``adoption`` arm, naming an implementation that
exists, or part, naming where the part is used) or carries a recorded ``not_adopted`` reason. An area whose findings carry decisions is guarded in full; an area researched
on or after ``GUARDED_SINCE`` must be, so new research cannot leave a finding with neither an arm nor a reason. The areas still without decisions are the visible debt, pinned
so that the list can only shrink.

(b) Real entry: every solution a person touches directly has a metric stage run through the real entry point (the terminal through ``ahohs work`` on a pseudo-terminal, the
front door through ``hubofhubs.run`` on a plain install)."""
import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from hubofhubs.the_world.learning.research_freshness_reader import registry  # noqa: E402

GUARDED_SINCE = date(2026, 11, 11)
DECISIONS = {"arm", "part", "not_adopted"}


def implementations_of(solution):
    names = set()
    for path in (ROOT / "hubofhubs").rglob("implementations.csv"):
        for row in csv.DictReader(open(path, newline="")):
            if row.get("solution_id") == solution:
                names.add(row["implementation_id"].split(":", 1)[-1])
    return names


def decided(finding):
    return bool(finding.get("adoption", "").strip())


def test_every_finding_of_a_guarded_area_has_an_arm_or_a_reason():
    hubs, findings = registry.read("hubs.csv"), registry.read("hub_findings.csv")
    guarded = 0
    for area in hubs:
        mine = registry.findings_of(area, findings)
        recent = bool(mine) and all(date.fromisoformat(f["date_researched"]) >= GUARDED_SINCE for f in mine)
        if not (any(decided(f) for f in mine) or recent):
            continue
        guarded += 1
        arms = implementations_of(mine[0]["solution_id"])
        for f in mine:
            where = f["finding_id"]
            assert f["adoption"].strip() in DECISIONS, f"{where}: record adoption as arm, part or not_adopted"
            assert f["adoption_reason"].strip(), f"{where}: a decision carries its reason (licence, language, fit with the session contract, or what was used)"
            if f["adoption"] == "arm":
                assert f["adopted_as"].split(":", 1)[-1] in arms, f"{where}: names an arm that does not exist: {f['adopted_as']}"
            if f["adoption"] == "part":
                assert f["adopted_as"].strip(), f"{where}: a part names where it is used"
            if f["adoption"] == "not_adopted":
                assert not f["adopted_as"].strip(), f"{where}: not adopted names no arm"
    assert guarded >= 1


def test_the_terminal_area_is_guarded_and_has_an_arm_on_a_library_and_the_consumers_screen():
    findings = [f for f in registry.read("hub_findings.csv") if f["area"] == "terminal_agent_experience"]
    assert len(findings) >= 14 and all(decided(f) for f in findings)
    arms = {f["adopted_as"] for f in findings if f["adoption"] == "arm"}
    assert "terminal-session:textual_session" in arms
    assert any("consumer" in f["candidate"] for f in findings if f["adoption"] == "arm")


PERSON_FACING = {
    "terminal-session": {"stage": "evaluation/terminal_session/pty_stage.py", "must_name": ("ahohs", "pty.openpty"), "case_kind": "pty"},
    "front door (hub-of-hubs)": {"stage": "evaluation/plain_install/impls/front_door.py", "must_name": ("hubofhubs.run",), "case_kind": None},
}


def test_every_solution_a_person_touches_has_a_stage_through_the_real_entry_point():
    for solution, spec in PERSON_FACING.items():
        stage = ROOT / spec["stage"]
        assert stage.is_file(), f"{solution}: no stage at {spec['stage']}"
        text = stage.read_text()
        for name in spec["must_name"]:
            assert name in text, f"{solution}: its stage does not go through {name}"
    cases = json.loads((ROOT / "evaluation/terminal_session/cases.json").read_text())
    pty = [c for c in cases if c["kind"] == "pty"]
    assert {c["args"]["scenario"] for c in pty} >= {"complete", "escape_resume", "steer", "structure", "follow_up", "harness_switch", "refused", "markdown"}
    arms = implementations_of("terminal-session")
    assert {"live_session", "line_repl", "textual_session"} <= arms
