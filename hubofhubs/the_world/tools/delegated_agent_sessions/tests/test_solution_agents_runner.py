"""The solution agents arm: every piece is pure code, so no test here calls a model. The guard is run as the CLI runs it, a program fed the hook's JSON."""
import json
import subprocess
import sys

import pytest

from hubofhubs.the_intelligence.nervous_system.step_watch import repeated_commands, step_findings
from hubofhubs.the_intelligence.subconscious.relevant_solutions.network import SolutionNetwork
from hubofhubs.the_world.model_plumbing.model_tier_chooser import role_tiers
from hubofhubs.the_world.tools.delegated_agent_sessions import frame_sections, solution_agents as agents
from hubofhubs.the_world.tools.delegated_agent_sessions import solution_agents_runner as arm
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
from hubofhubs.the_world.tools.delegated_agent_sessions.control import RunControl
from hubofhubs.the_world.tools.delegated_agent_sessions.hub_frame import RULES, STABLE_RULES, build_frame
from hubofhubs.the_world.tools.delegated_agent_sessions.launch import DeepLaunchSettings, build_deep_argv, lean_flags
from hubofhubs.the_world.tools.delegated_agent_sessions.settings import GoalSettings

TABLES = {"intents": [{"intent_id": "i1", "name": "Top"}], "solutions": [
    {"solution_id": "read-things", "name": "Read Things", "purpose": "Read the things.", "approach": "List and read.", "out_of_scope": "Writing.",
     "milestones": "1. First. (authoritative metric m)", "delegates_to": "sub-thing"},
    {"solution_id": "sub-thing", "name": "Sub Thing", "purpose": "A part.", "approach": "", "out_of_scope": "", "milestones": "", "delegates_to": "none"},
    {"solution_id": "judge-things", "name": "Judge Things", "purpose": "Judge the result.", "approach": "Check it.", "out_of_scope": "", "milestones": "", "delegates_to": "none"}]}
NET = SolutionNetwork.from_rows(TABLES)
SPECS = [agents.SolutionSpec("read-things", "gather", agents.READ_TOOLS), agents.SolutionSpec("judge-things", "review", agents.READ_TOOLS),
         agents.SolutionSpec("sub-thing", "work"), agents.SolutionSpec("not-in-records")]


def tier_model(tier):
    return "model-of-" + tier


def guard(tmp_path, data, allowed=("read-things",), budget=1):
    path = tmp_path / "guard.py"
    path.write_text(agents.guard_script(allowed, budget, str(tmp_path / "count"), str(tmp_path / "log")))
    done = subprocess.run([sys.executable, str(path)], input=data if isinstance(data, str) else json.dumps(data), capture_output=True, text=True)
    return json.loads(done.stdout)["hookSpecificOutput"] if done.stdout.strip() else None


# --- A: the agents ---------------------------------------------------------------------------------------------------------------

def test_one_agent_per_solution_the_records_hold_with_its_own_frame_and_its_roles_tier():
    made = agents.agent_definitions(SPECS, NET, tier_model)
    assert sorted(made) == ["judge-things", "read-things", "sub-thing"]       # a solution with no record gets no agent; names are sorted ids
    assert made["read-things"]["model"] == "model-of-fast" and made["sub-thing"]["model"] == "model-of-balanced" and made["judge-things"]["model"] == "model-of-quality"
    assert made["read-things"]["tools"] == ["Read", "Glob", "Grep"]
    prompt = made["read-things"]["prompt"]
    assert "Read Things (read-things)" in prompt and "Approach: List and read." in prompt and "Next unmet milestone: First." in prompt and "Out of scope: Writing." in prompt
    assert "Sub Thing (sub-thing), agent sub-thing" in prompt and "cannot start another agent" in prompt          # a child is named; the top session calls its agent
    assert "Judge" not in prompt and "Output:" in prompt and "Missing:" in prompt                                 # only its own frame, and the report form
    assert made["read-things"]["description"].startswith("Read the things. Use it when")


def test_a_tier_with_no_model_gives_no_agent_rather_than_another_tiers_model():
    made = agents.agent_definitions(SPECS, NET, lambda tier: None if tier == "quality" else "m")
    assert "judge-things" not in made and "read-things" in made


def test_the_fixed_solutions_exist_in_the_hubs_own_records_and_roles_are_in_the_table():
    specs, net = agents.choose_solutions("a goal", "/nonexistent-folder")
    assert [s.solution for s in specs] == ["file-editing", "read-files", "response-quality", "web-search"] and all(net.has(s.solution) for s in specs)
    assert {s.kind for s in specs} == {"gather", "work", "review"}
    assert {role_tiers.tier_for(agents.ROLE_OF_KIND[k]) for k in ("gather", "work", "review")} == {"fast", "balanced", "quality"}
    assert all(role_tiers.read_table()[r]["evidence"].startswith("owner's policy, unmeasured") for r in agents.ROLE_OF_KIND.values())


def test_solutions_come_from_the_consumer_first_then_the_folders_records_then_the_hub():
    given, net = agents.choose_solutions("g", "/x", ["sub-thing", "read-things", "read-things"], records=NET)
    assert [s.solution for s in given] == ["read-things", "sub-thing"] and net is NET
    by_callable, _ = agents.choose_solutions("g", "/x", lambda goal, root: [agents.SolutionSpec("judge-things", "review")], records=NET)
    assert [s.solution for s in by_callable] == ["judge-things"]
    folder, _ = agents.choose_solutions("Read the things and list them", "/x", records=NET)
    assert folder and all(NET.has(s.solution) for s in folder)


def test_small_work_is_offered_no_agents_by_counts():
    assert not agents.wants_agents({"files": agents.OFFER_FILES - 1, "chars": 10**6, "goal_chars": agents.OFFER_CHARS - 1})
    assert agents.wants_agents({"files": agents.OFFER_FILES, "chars": 0, "goal_chars": 0}) and agents.wants_agents({"files": 0, "chars": 0, "goal_chars": agents.OFFER_CHARS})


def test_the_note_names_the_rules_and_the_review_rule_only_with_a_review_agent():
    plain, reviewed = agents.agents_note(7), agents.agents_note(7, "judge-things")
    assert "At most 7 calls" in plain and "separable" in plain and "cannot start another agent" in plain and "review agent" not in plain
    assert reviewed.startswith(plain) and "judge-things" in reviewed and str(agents.REVIEW_FILES) in reviewed and agents.agents_note(7) == plain


# --- A: the guard ----------------------------------------------------------------------------------------------------------------

def test_the_guard_allows_a_solution_agent_and_refuses_every_other_agent(tmp_path):
    assert guard(tmp_path, {"tool_name": "Agent", "tool_input": {"subagent_type": "read-things"}}, budget=5) is None
    for other in ("general-purpose", "Explore", "Plan", "", "read-things-2"):
        refused = guard(tmp_path, {"tool_name": "Agent", "tool_input": {"subagent_type": other}}, budget=5)
        assert refused["permissionDecision"] == "deny" and "only its solution agents" in refused["permissionDecisionReason"]
    assert guard(tmp_path, {"tool_name": "Agent", "tool_input": {}}, budget=5)["permissionDecision"] == "deny"      # no type at all is not a solution agent


def test_the_guard_refuses_calls_past_the_budget_and_counts_only_allowed_ones(tmp_path):
    call = {"tool_name": "Agent", "tool_input": {"subagent_type": "read-things"}}
    guard(tmp_path, {"tool_name": "Agent", "tool_input": {"subagent_type": "general-purpose"}}, budget=2)
    assert guard(tmp_path, call, budget=2) is None and guard(tmp_path, call, budget=2) is None
    spent = guard(tmp_path, call, budget=2)
    assert spent["permissionDecision"] == "deny" and "budget of 2" in spent["permissionDecisionReason"]
    assert (tmp_path / "count").read_text() == "2" and len((tmp_path / "log").read_text().splitlines()) == 4


def test_a_guard_that_cannot_decide_refuses(tmp_path):
    assert guard(tmp_path, "not json at all")["permissionDecision"] == "deny"


def test_the_settings_hook_both_names_of_the_tool_and_a_deny_for_the_built_in_agents():
    settings = agents.guard_settings("/usr/bin/python3", "/tmp/a guard.py")
    hook = settings["hooks"]["PreToolUse"][0]
    assert hook["matcher"] == "Agent|Task" and hook["hooks"][0]["command"] == "/usr/bin/python3 '/tmp/a guard.py'"
    assert settings["permissions"]["deny"] == ["Agent(general-purpose)", "Agent(Explore)", "Agent(Plan)"]


def test_launch_flags_for_the_agents_and_settings_files_and_the_default_stays_default():
    assert DeepLaunchSettings().is_default() and lean_flags(DeepLaunchSettings()) == []
    flags = lean_flags(DeepLaunchSettings(agents_file="/a.json", settings_file="/s.json"))
    assert flags == ["--agents", "/a.json", "--settings", "/s.json"] and "agents_file=1" in DeepLaunchSettings(agents_file="/a.json").describe()


# --- A: after the session --------------------------------------------------------------------------------------------------------

def record(*calls):
    lines = []
    for ident, agent, description, failed in calls:
        lines.append(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": ident, "name": "Agent",
                                                                               "input": {"subagent_type": agent, "description": description}}]}}))
        lines.append(json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": ident, "is_error": failed, "content": "x"}]}}))
    return lines


def test_a_call_outside_the_list_is_a_finding_and_each_solution_call_is_announced():
    calls = agents.agent_calls_in(record(("t1", "general-purpose", "look", True), ("t2", "read-things", "[read-things] list the files", False), ("t3", "read-things", "again", True)))
    assert [c["agent"] for c in calls] == ["general-purpose", "read-things", "read-things"]
    assert agents.outside_the_list(calls, ["read-things"]) == ["an agent call outside the list: general-purpose (refused)"]
    assert "NOT refused" in agents.outside_the_list(agents.agent_calls_in(record(("t9", "Explore", "x", False))), ["read-things"])[0]
    events = agents.session_events(calls, {"read-things": "read-things"})
    assert [e["type"] for e in events] == ["agent-started", "agent-ended"] * 2
    assert events[0] == {"type": "agent-started", "agent_id": "t2", "parent_id": "main", "task": "list the files", "solution": "read-things"}
    assert events[1]["state"] == "met" and events[1]["calls"] == 1 and events[3]["state"] == "unmet" and events[3]["calls"] == 0


# --- the arm: a session prepared offline -------------------------------------------------------------------------------------------

def runner_in(tmp_path, files, **kwargs):
    work = tmp_path / "work"
    work.mkdir(exist_ok=True)
    for number in range(files):
        (work / f"note_{number}.txt").write_text(f"note {number}\n")
    made = arm.SolutionAgentsNativeRunner(SubprocessConfig(working_dir=str(work)), settings=GoalSettings(environment=lambda: {}), provider="anthropic",
                                          session_dir=str(tmp_path / "sessions"), records=NET, solutions=SPECS[:2], **kwargs)
    made.model_of = tier_model
    return made, str(work)


def test_a_small_folder_and_goal_get_no_agents_no_tool_and_no_guard(tmp_path):
    runner, work = runner_in(tmp_path, 3)
    runner.prepare("short goal", "short goal", "", work, "small")
    launch = runner.launch_settings()
    assert "Agent" not in launch.tools and launch.agents_file is None and launch.settings_file is None and "SOLUTION AGENTS" not in open(launch.append_system_prompt_file).read()


def test_a_large_folder_gets_the_agents_the_guard_and_the_frame_note_under_a_fixed_budget(tmp_path):
    runner, work = runner_in(tmp_path, agents.OFFER_FILES, agent_calls=3)
    runner.prepare("goal", "goal", "", work, "large")
    launch = runner.launch_settings()
    assert launch.tools[-1] == "Agent" and launch.agents_file.endswith("solution-agents.json") and launch.settings_file.endswith("agent-guard.json")
    defined = json.load(open(launch.agents_file))
    assert sorted(defined) == ["judge-things", "read-things"] and defined["judge-things"]["model"] == "model-of-quality"
    assert "BUDGET = 3" in open(launch.settings_file.replace("agent-guard.json", "agent-guard.py")).read()
    frame = open(launch.append_system_prompt_file).read()
    assert "At most 3 calls" in frame and "review agent (judge-things)" in frame
    argv = build_deep_argv("claude", streaming=True, skip_permissions=True, allowed_tools=None, disallowed_tools=None, mcp_config_path=None, model="m", turns=5,
                           goal_given=True, session_flag="--session-id", session_id="s", launch=launch)
    assert argv[argv.index("--agents") + 1] == launch.agents_file and argv[argv.index("--settings") + 1] == launch.settings_file and "--strict-mcp-config" in argv
    assert runner.local.solution_of == {"judge-things": "judge-things", "read-things": "read-things"}


def test_zero_agent_calls_offers_none_even_for_a_large_folder(tmp_path):
    runner, work = runner_in(tmp_path, agents.OFFER_FILES, agent_calls=0)
    runner.prepare("goal", "goal", "", work, "none")
    assert runner.launch_settings().agents_file is None


def test_an_mcp_config_is_passed_through_with_strict_mcp_kept_on(tmp_path):
    runner, work = runner_in(tmp_path, 1, mcp_config="/somewhere/mcp.json")
    runner.prepare("goal", "goal", "", work, "mcp")
    assert runner.cfg.mcp_config_path == "/somewhere/mcp.json" and runner.launch_settings().strict_mcp


# --- B and C: skills and known context ----------------------------------------------------------------------------------------------

def test_skills_are_one_line_each_sorted_and_clipped_with_the_rule(tmp_path):
    for name, body in (("zeta", "---\nname: zeta\ndescription: Does zeta things.\n---\nbody"), ("alpha", "---\nname: alpha\ndescription: >\n  Folded\n  description.\n---\n"),
                       ("long", "---\nname: long\ndescription: " + "w " * 400 + "\n---\n")):
        (tmp_path / "s" / name).mkdir(parents=True)
        (tmp_path / "s" / name / "SKILL.md").write_text(body)
    (tmp_path / "s" / "no-skill-file").mkdir()
    (tmp_path / "t" / "beta").mkdir(parents=True)
    (tmp_path / "t" / "beta" / "SKILL.md").write_text("---\nname: beta\ndescription: Second folder.\n---\n")
    text = frame_sections.skills_section([str(tmp_path / "s"), str(tmp_path / "t")])
    lines = text.splitlines()
    assert "Read a skill's file before you do work it covers." in lines[0]
    assert [x.split(":")[0] for x in lines[1:]] == ["- alpha", "- beta", "- long", "- zeta"] and "Folded description." in lines[1]
    assert str(tmp_path / "s" / "alpha" / "SKILL.md") in lines[1] and len(lines[3]) < frame_sections.SKILL_LINE_CHARS + len(str(tmp_path)) + 40
    assert frame_sections.skills_section(None) == "" and frame_sections.skills_section(str(tmp_path / "missing")) == ""


def test_known_context_holds_recall_and_earlier_investigations_bounded_and_ordered():
    rows = {"s1": [{"investigation_id": "a", "question": "Q old?", "synthesis_known": "old finding", "done_on": "2026-01-01", "fresh": "no"},
                   {"investigation_id": "b", "question": "Q new?", "synthesis_known": "new finding", "done_on": "2026-06-01", "fresh": "yes"}],
            "s2": [{"investigation_id": "b", "question": "Q new?", "synthesis_known": "new finding", "done_on": "2026-06-01", "fresh": "yes"}]}
    text = frame_sections.known_section("goal", recall=lambda goal: "card text for " + goal, solutions=["s2", "s1"], investigations=lambda sid: rows[sid])
    assert text.startswith("KNOWN CONTEXT") and "card text for goal" in text and "not redone unless its date is stale" in text
    lines = [x for x in text.splitlines() if x.startswith("- ")]
    assert len(lines) == 2 and "Q new?" in lines[0] and "2026-06-01" in lines[0] and "stale" not in lines[0] and "2026-01-01, stale" in lines[1]
    small = frame_sections.known_section("goal", recall=lambda goal: "x" * 5000, solutions=["s1"], investigations=lambda sid: rows[sid], chars=1000)
    assert len(small) < 1400
    assert frame_sections.known_section("g", recall=lambda goal: 1 / 0, solutions=[], investigations=lambda sid: []) == ""
    assert frame_sections.known_section("g", recall=lambda goal: "ok", solutions=["s1"], investigations=lambda sid: 1 / 0).endswith("ok")


# --- F: the frame is ordered for the prompt cache -------------------------------------------------------------------------------------

def test_frames_for_different_goals_in_one_folder_share_a_prefix_up_to_the_first_goal_dependent_section(tmp_path):
    for number in range(6):
        (tmp_path / f"doc_{number}.md").write_text(f"document {number} about topic{number}\n" * 20)
    extras = [agents.agents_note(4), "SKILLS (x):\n- a: b"]
    one = build_frame("summarise topic1", "", str(tmp_path), stable=True, extras=extras, known="KNOWN CONTEXT: one")
    two = build_frame("compare topic4 and topic5 in depth", "", str(tmp_path), stable=True, extras=extras, known="KNOWN CONTEXT: two")
    cut = one.text.index("KNOWN CONTEXT")
    assert one.text[:cut] == two.text[:cut] and STABLE_RULES in one.text[:cut] and "FOLDER MAP" in one.text[:cut] and "[not in view" not in one.text
    assert one.text.index("KNOWN CONTEXT") < one.text.index("FILES IN VIEW (current)") and one.shown != two.shown      # the goal-dependent parts come after it


def test_the_order_is_rules_notes_agents_skills_map_known_view(tmp_path):
    (tmp_path / "a.txt").write_text("alpha\n")
    text = build_frame("a", "", str(tmp_path), notes="NOTES", stable=True, extras=["AGENTS", "SKILLS"], known="KNOWN").text
    positions = [text.index(x) for x in ("How to work", "\n\nNOTES\n\n", "\n\nAGENTS\n\n", "\n\nSKILLS\n\n", "FOLDER MAP", "\n\nKNOWN\n\n", "FILES IN VIEW (current)")]
    assert positions == sorted(positions)


def test_the_existing_frame_is_unchanged_by_the_new_arguments(tmp_path):
    (tmp_path / "a.txt").write_text("alpha\n")
    (tmp_path / "b.txt").write_text("beta " * 30000)
    frame = build_frame("report on a.txt", "", str(tmp_path), notes="NOTES")
    assert frame.text.startswith(RULES + "\n\nNOTES\n\nFOLDER MAP") and STABLE_RULES not in frame.text and "[not in view: READ it before relying on it]" in frame.text
    assert "SOLUTION AGENTS" not in frame.text and "KNOWN CONTEXT" not in frame.text
    def broken(*a, **k):
        raise RuntimeError("no selection")
    assert build_frame("g", "", str(tmp_path), select=broken, notes="N").text == RULES + "\n\nN"


# --- E: the step watch -------------------------------------------------------------------------------------------------------------

def test_a_command_run_a_third_time_unchanged_is_found_and_a_write_between_runs_starts_the_count_again():
    run = ("Bash", {"command": "pytest  -q"})
    assert repeated_commands([run, ("Bash", {"command": "pytest -q"}), run]) == ["pytest -q"]
    assert repeated_commands([run, run, ("Edit", {"file_path": "a"}), run]) == [] and repeated_commands([run, run]) == []


def test_findings_are_reported_once_and_agent_calls_past_the_budget_are_a_finding():
    actions = [("Bash", {"command": "ls"})] * 3 + [("Agent", {"subagent_type": "x"})] * 3
    found = step_findings(actions, agent_budget=2)
    assert [k for k, _ in found] == ["repeat:ls", "agents"] and "3 times unchanged" in found[0][1] and "allowance is 2" in found[1][1]
    assert step_findings(actions, agent_budget=2, reported={"repeat:ls", "agents"}) == [] and step_findings(actions, agent_budget=3, reported={"repeat:ls"}) == []


def test_the_watch_steers_once_per_finding_through_the_control(monkeypatch):
    monkeypatch.setattr(arm, "STEP_POLL_SECONDS", 0.0)
    seen = []
    watch = arm.StepWatch(None, None, 0.8, budget=1, actions_of=lambda: [("Bash", {"command": "ls"})] * 3)
    control = watch.wrap(RunControl(claim_inputs=lambda: seen))
    first, second = control.claim_inputs(), control.claim_inputs()
    assert len(first) == 1 and "3 times unchanged" in first[0].text and second == []
    assert control.cancel_requested() is False


def test_the_watch_sends_at_most_a_few_messages(monkeypatch):
    monkeypatch.setattr(arm, "STEP_POLL_SECONDS", 0.0)
    actions = lambda: [("Bash", {"command": f"c{n}"}) for n in range(arm.MAX_STEERS + 3) for _ in range(3)]
    watch = arm.StepWatch(None, None, 0.8, budget=9, actions_of=actions)
    total = sum(len(watch.steering()) for _ in range(5))
    assert total == arm.MAX_STEERS


def test_the_frame_prefix_is_the_same_for_different_goals_on_a_real_folder_and_left_out_does_not_follow_the_goal():
    from pathlib import Path
    folder = str(Path(arm.__file__).parent)
    goals = ["add a step watch to the native runner", "write a summary of how metrics.csv is scored", "explain public_priors.csv"]
    frames = [build_frame(g, "", folder, stable=True, extras=["X"], known="KNOWN CONTEXT: " + g) for g in goals]
    cut = frames[0].text.index("KNOWN CONTEXT")
    assert all(f.text[:cut] == frames[0].text[:cut] for f in frames) and len({tuple(f.left_out) for f in frames}) == 1
    assert len({tuple(f.shown) for f in frames}) > 1       # the files in view do follow the goal, and come after the stable part


def test_the_result_carries_turns_and_the_calls_that_ran_and_other_results_carry_none(tmp_path):
    from hubofhubs.the_world.tools.deep import DeepResult
    assert DeepResult(met=True).subagent_calls is None and DeepResult(met=True).turns is None
    runner, work = runner_in(tmp_path, 1)
    runner.local.used_turns, runner.local.solution_of = 7, {}
    result = DeepResult(met=True)
    runner.report_agents(result, work, None)
    assert result.turns == 7 and result.subagent_calls == 0
