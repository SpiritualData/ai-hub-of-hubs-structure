"""Role Understanding: the recorded arm states a part's role from its row and no more; the checked arm adds the contradictions between the role and the
part's calls. A last test reads the hub's own records."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from hubofhubs.the_self.role_understanding.roles import CheckedRole, RecordedRole, calls_in  # noqa: E402

ROWS = [{"solution_id": "p", "purpose": "Does p.", "out_of_scope": "Other work.", "delegates_to": "q;none"},
        {"solution_id": "q", "purpose": "Does q.", "out_of_scope": "", "delegates_to": ""}]


def test_the_recorded_arm_states_the_row_and_says_when_no_record_knows_the_part():
    arm = RecordedRole(solutions=ROWS, implementations=[], code={})
    assert arm.state_role("p") == {"part": "p", "stated": True, "purpose": "Does p.", "out_of_scope": "Other work.", "delegates_to": ["q"]}
    assert arm.state_role("q")["out_of_scope"] == "" and arm.state_role("q")["delegates_to"] == []
    assert arm.state_role("ghost") == {"part": "ghost", "stated": False}
    assert "contradictions" not in arm.state_role("p")


def test_calls_are_the_literal_ids_of_take_calls():
    assert calls_in('take(a, "x")\ntake(b, "y", method="m")\ntake(c, name)\ntake(d, "x")\nother(e, "z")') == ["x", "y"]


def test_the_checked_arm_reports_a_call_the_role_does_not_cover_and_an_owner_that_is_no_solution():
    implementations = [{"solution_id": "p", "uses_solution_ids": "q", "filepath": "p.py"}]
    arm = CheckedRole(solutions=ROWS, implementations=implementations, code={"p.py": 'take(a, "q")\ntake(a, "r")'})
    assert arm.state_role("p")["contradictions"] == [{"code": "undeclared-call", "detail": "r"}]
    bad = CheckedRole(solutions=[dict(ROWS[0], delegates_to="ghost")], implementations=[], code={})
    assert bad.state_role("p")["contradictions"] == [{"code": "unknown-owner", "detail": "ghost"}]


def test_every_part_the_hub_records_states_a_role_with_no_contradiction():
    arm = CheckedRole()
    assert len(arm.solutions) > 40
    for part in arm.solutions:
        role = arm.state_role(part)
        assert role["stated"] and role["purpose"], part
        assert role["contradictions"] == [], (part, role["contradictions"])
