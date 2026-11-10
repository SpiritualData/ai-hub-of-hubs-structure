"""The sized frame of the adaptive native arm: fixed rules bytes, the plan only by counts, a cap on the view, no outline for an empty folder."""
from hubofhubs.the_world.tools.delegated_agent_sessions import adaptive_native_runner as arm
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import NATIVE_TOOLS


def folder(tmp_path, count, size=50):
    for number in range(count):
        (tmp_path / f"note_{number}.md").write_text("x" * size)
    return str(tmp_path)


def test_the_rules_are_the_same_bytes_for_every_small_task():
    assert arm.rules_for({"files": 2, "chars": 10, "goal_chars": 80}) == arm.rules_for({"files": 5, "chars": 9000, "goal_chars": 300}) == arm.BASE_RULES


def test_the_plan_rule_comes_in_at_one_fixed_place_by_counts_only():
    many = arm.rules_for({"files": arm.PLAN_FILES, "chars": 1, "goal_chars": 10})
    long_goal = arm.rules_for({"files": 1, "chars": 1, "goal_chars": arm.PLAN_CHARS})
    assert many == long_goal and arm.PLAN_RULE in many and arm.PLAN_RULE not in arm.BASE_RULES
    assert many.replace(arm.PLAN_RULE, "") == arm.BASE_RULES


def test_an_empty_folder_gets_the_rules_alone(tmp_path):
    frame = arm.lean_frame("write a note", "", str(tmp_path), arm.folder_facts(str(tmp_path), "write a note"))
    assert frame.text == arm.BASE_RULES and "FOLDER MAP" not in frame.text


def test_a_folder_with_files_gets_the_capped_view_and_the_outline(tmp_path):
    root = folder(tmp_path, 3, size=30_000)
    frame = arm.lean_frame("read note_0.md", "", root, arm.folder_facts(root, "read note_0.md"))
    assert "FOLDER MAP" in frame.text and frame.text.startswith(arm.BASE_RULES) and len(frame.text) < arm.VIEW_CAP + 6_000


def test_the_facts_are_counts(tmp_path):
    root = folder(tmp_path, 4, size=10)
    assert arm.folder_facts(root, "abc") == {"files": 4, "chars": 40, "goal_chars": 3}


def test_the_arm_resumes_only_for_a_named_file_and_leaves_out_the_task_tools_for_a_small_task(tmp_path):
    runner = arm.AdaptiveNativeRunner.__new__(arm.AdaptiveNativeRunner)
    assert runner.resume_gate == "named_files" and arm.PLAN_TOOLS and set(arm.PLAN_TOOLS) <= set(NATIVE_TOOLS)
