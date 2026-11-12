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
    tier = {kind: role_tiers.tier_for(agents.ROLE_OF_KIND[kind]) for kind in ("gather", "work", "review")}          # the role table is data and changes with its evidence
    assert made["read-things"]["model"] == "model-of-" + tier["gather"] and made["sub-thing"]["model"] == "model-of-" + tier["work"]
    assert made["judge-things"]["model"] == "model-of-" + tier["review"]
    assert made["read-things"]["tools"] == ["Read", "Glob", "Grep"]
    prompt = made["read-things"]["prompt"]
    assert "Read Things (read-things)" in prompt and "Approach: List and read." in prompt and "Next unmet milestone: First." in prompt and "Out of scope: Writing." in prompt
    assert "Sub Thing (sub-thing), agent sub-thing" in prompt and "cannot start another agent" in prompt          # a child is named; the top session calls its agent
    assert "Judge" not in prompt and "Output:" in prompt and "Missing:" in prompt                                 # only its own frame, and the report form
    assert made["read-things"]["description"].startswith("Read the things. Use it when")


def test_a_tier_with_no_model_gives_no_agent_rather_than_another_tiers_model():
    review_tier = "balanced"
    tiers = {agents.ROLE_OF_KIND["review"]: review_tier}       # the table puts every deep-run role on one tier by default: plant two tiers here
    made = agents.agent_definitions(SPECS, NET, lambda tier: None if tier == review_tier else "m", tier_of=lambda role: tiers.get(role, "fast"))
    assert "judge-things" not in made and "read-things" in made


def test_the_fixed_solutions_exist_in_the_hubs_own_records_and_roles_are_in_the_table():
    specs, net = agents.choose_solutions("a goal", "/nonexistent-folder")
    assert [s.solution for s in specs] == ["file-editing", "read-files", "response-quality", "web-search"] and all(net.has(s.solution) for s in specs)
    assert {s.kind for s in specs} == {"gather", "work", "review"}
    assert all(role_tiers.tier_for(agents.ROLE_OF_KIND[k]) in ("fast", "balanced", "quality") for k in ("gather", "work", "review"))
    assert all(r in role_tiers.read_table() for r in agents.ROLE_OF_KIND.values())


def test_solutions_come_from_the_consumer_first_then_the_folders_records_then_the_hub():
    given, net = agents.choose_solutions("g", "/x", ["sub-thing", "read-things", "read-things"], records=NET)
    assert [s.solution for s in given] == ["read-things", "sub-thing"] and net is NET
    by_callable, _ = agents.choose_solutions("g", "/x", lambda goal, root: [agents.SolutionSpec("judge-things", "review")], records=NET)
    assert [s.solution for s in by_callable] == ["judge-things"]
    folder, _ = agents.choose_solutions("Read the things and list them", "/x", records=NET)
    assert folder and all(NET.has(s.solution) for s in folder)


def test_small_work_is_offered_no_agents_by_counts():
    assert not agents.wants_agents({"files": agents.OFFER_FILES - 1, "chars": agents.OFFER_TOTAL_CHARS - 1, "goal_chars": agents.OFFER_CHARS - 1})
    assert agents.wants_agents({"files": agents.OFFER_FILES, "chars": 0, "goal_chars": 0}) and agents.wants_agents({"files": 0, "chars": 0, "goal_chars": agents.OFFER_CHARS})


def test_a_few_long_files_are_a_large_folder_by_their_size_together():
    assert agents.wants_agents({"files": 3, "chars": agents.OFFER_TOTAL_CHARS, "goal_chars": 80})
    assert not agents.wants_agents({"files": 3, "chars": agents.OFFER_TOTAL_CHARS - 1, "goal_chars": 80})


def test_a_solution_is_worked_through_its_children_and_their_own_up_to_the_limit():
    rows = {"solutions": [{"solution_id": s, "name": s, "purpose": "p", "approach": "", "out_of_scope": "", "milestones": "", "delegates_to": d}
                          for s, d in (("top", "mid; leaf-a"), ("mid", "leaf-b; leaf-c"), ("leaf-a", "none"), ("leaf-b", "none"), ("leaf-c", "none"))],
            "intents": [{"intent_id": "i", "name": "Top"}]}
    net = SolutionNetwork.from_rows(rows)
    assert agents.with_delegates(["top"], net) == ["top", "mid", "leaf-a", "leaf-b", "leaf-c"]
    assert agents.with_delegates(["mid", "top"], net, limit=3) == ["mid", "top", "leaf-b"]
    assert agents.with_delegates(["leaf-a"], net) == ["leaf-a"]


def test_the_report_of_a_run_counts_calls_that_ran_by_solution_and_those_refused_by_type():
    solution_of = {"read-things": "read-things", "judge-things": "judge-things"}
    calls = agents.agent_calls_in(record(("a", "read-things", "x", False), ("b", "read-things", "y", False), ("c", "judge-things", "z", True), ("d", "general-purpose", "w", True)))
    assert agents.agent_report(calls, solution_of) == {"offered": ["judge-things", "read-things"], "ran": {"read-things": 2}, "refused": {"judge-things": 1, "general-purpose": 1}}
    assert agents.agent_report([], {}) == {"offered": [], "ran": {}, "refused": {}}


def test_the_review_agent_is_told_to_check_every_claim_against_a_source_and_only_it():
    made = agents.agent_definitions(SPECS, NET, tier_model, goal="Which port was busiest in March?")
    prompt = made["judge-things"]["prompt"]
    assert "every" in prompt and "source" in prompt and agents.REVIEW_BRIEF not in made["read-things"]["prompt"]
    assert "Which port was busiest in March?" in prompt and "THE REQUEST AS THE PERSON STATED IT" in prompt                  # the person's own words reach the reviewer
    assert "milestone" not in prompt.lower() and "Purpose:" not in prompt and "Judge the result" not in prompt             # no milestone or purpose framing for a review
    assert "Verdict:" in prompt and "Milestone:" not in prompt and "Request" not in made["read-things"]["prompt"]
    assert "Next unmet milestone" in made["read-things"]["prompt"] and "Output:" in made["read-things"]["prompt"]           # the other agents keep their own solution's frame
    assert "check" in made["judge-things"]["description"] and "hub asks" in made["judge-things"]["description"]
    assert "milestone as met only when a check" in agents.agents_note(5)


def test_the_review_request_carries_the_goal_the_paths_and_what_to_check():
    text = agents.review_request("judge-things", ["answers.md", "notes/b.md"], "  Report each port's tonnage.  ")
    assert "answers.md, notes/b.md" in text and "THE REQUEST:\nReport each port's tonnage." in text and "foreground" in text
    assert "every figure, name, date and claim of the file against a source file" in text and "quote that source" in text and "milestone" not in text.lower()


def test_a_review_is_asked_for_by_computed_figures_and_size_and_not_for_a_lookup(tmp_path):
    folders = iter(range(100))

    def stakes(files, goal="How many voyages left in March, in total?", **sources):
        folder = tmp_path / f"case{next(folders)}"                         # a folder of its own: an earlier case's deliverable is not a source of the next
        for name, text in {**sources, **files}.items():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_text(text)
        return agents.review_stakes(str(folder), list(files), goal)
    source = {"src.md": "voyage 11: 4400 t\nvoyage 12: 5500 t\n"}
    many = stakes({"answers.md": "Q1: 19950\nQ2: 988600\nQ3: 51610\n"}, **source)                       # three computed figures: reviewed
    assert many["computed"] == 3 and agents.review_wanted(many)
    one_small = stakes({"one.md": "Total: 19950\n"}, **source)                                          # one computed figure in a small file: not reviewed
    assert one_small["computed"] == 1 and not agents.review_wanted(one_small)
    one_big = stakes({"big.md": "Total: 19950\n" + "Plain words about the voyages. " * 200}, **source)    # one in a deliverable of real size: reviewed
    assert one_big["computed"] == 1 and one_big["chars"] >= agents.REVIEW_BIG_CHARS and agents.review_wanted(one_big)
    quoted = stakes({"quote.md": "Voyage 11 carried 4400 t and voyage 12 carried 5500 t.\n" * 3}, **source)   # quoted from the sources: nothing computed
    assert quoted["computed"] == 0 and not agents.review_wanted(quoted)
    assert not agents.review_wanted({"computed": 0, "chars": 10 ** 6}) and not agents.review_wanted({})
    lookup = stakes({"answer.json": '{"note": "note_07.txt", "locker": 41}'}, **source)                 # not prose: the check reads no figure in it
    assert lookup["computed"] == 0 and not agents.review_wanted(lookup)


def test_the_guard_refuses_a_background_call_and_any_read_of_an_agents_output_file(tmp_path):
    background = guard(tmp_path, {"tool_name": "Agent", "tool_input": {"subagent_type": "read-things", "run_in_background": True}}, budget=5)
    assert background["permissionDecision"] == "deny" and "run_in_background set to false" in background["permissionDecisionReason"]
    unset = guard(tmp_path, {"tool_name": "Agent", "tool_input": {"subagent_type": "read-things"}}, budget=5)          # the call that ran in the background in the evaluation: no flag at all
    assert unset["permissionDecision"] == "deny" and "not run and not counted" in unset["permissionDecisionReason"]
    assert guard(tmp_path, {"tool_name": "Agent", "tool_input": {"subagent_type": "read-things", "run_in_background": False}}, budget=5) is None
    assert not (tmp_path / "count").exists() or (tmp_path / "count").read_text() == "1"                        # a refused background call spent none of the budget
    path = "/tmp/x/claude-1000/-tmp-work/abc/tasks/a1b2c3d4e5.output"
    for call in ({"tool_name": "Read", "tool_input": {"file_path": path}}, {"tool_name": "Bash", "tool_input": {"command": f"F={path}; while [ ! -s $F ]; do sleep 5; done"}},
                 {"tool_name": "Grep", "tool_input": {"pattern": "x", "path": path}}):
        refused = guard(tmp_path, call, budget=5)
        assert refused["permissionDecision"] == "deny" and "output file" in refused["permissionDecisionReason"]
    assert guard(tmp_path, {"tool_name": "Bash", "tool_input": {"command": "ls tasks/ && sleep 1"}}, budget=5) is None      # an ordinary command is left alone
    assert guard(tmp_path, {"tool_name": "Read", "tool_input": {"file_path": "/work/answers.md"}}, budget=5) is None


def test_the_note_names_the_rules_and_the_review_rule_only_with_a_review_agent():
    plain, reviewed = agents.agents_note(7), agents.agents_note(7, "judge-things")
    assert "At most 7 calls" in plain and "separable" in plain and "cannot start another agent" in plain and "review agent" not in plain
    assert reviewed.startswith(plain) and "judge-things" in reviewed and "hub decides" in reviewed and agents.agents_note(7) == plain
    assert "foreground" in plain and "run_in_background set to false" in plain and "Never read an agent's output file" in plain and "never poll or sleep" in plain and "you do not report without it" in plain


# --- A: the guard ----------------------------------------------------------------------------------------------------------------

def test_the_guard_allows_a_solution_agent_and_refuses_every_other_agent(tmp_path):
    assert guard(tmp_path, {"tool_name": "Agent", "tool_input": {"subagent_type": "read-things", "run_in_background": False}}, budget=5) is None
    for other in ("general-purpose", "Explore", "Plan", "", "read-things-2"):
        refused = guard(tmp_path, {"tool_name": "Agent", "tool_input": {"subagent_type": other}}, budget=5)
        assert refused["permissionDecision"] == "deny" and "only its solution agents" in refused["permissionDecisionReason"]
    assert guard(tmp_path, {"tool_name": "Agent", "tool_input": {}}, budget=5)["permissionDecision"] == "deny"      # no type at all is not a solution agent


def test_the_guard_refuses_calls_past_the_budget_and_counts_only_allowed_ones(tmp_path):
    call = {"tool_name": "Agent", "tool_input": {"subagent_type": "read-things", "run_in_background": False}}
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
    assert hook["matcher"] == "Agent|Task|Read|Bash|Grep|Glob" and hook["hooks"][0]["command"] == "/usr/bin/python3 '/tmp/a guard.py'"
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


def test_a_small_folder_and_goal_get_only_the_review_agent_by_default(tmp_path):
    runner, work = runner_in(tmp_path, 3)
    runner.prepare("short goal", "short goal", "", work, "small")
    launch = runner.launch_settings()
    assert "Agent" in launch.tools and launch.agents_file is not None and launch.settings_file is not None
    defined = json.load(open(launch.agents_file))
    assert sorted(defined) == ["response-quality"] and runner.local.solution_of == {"response-quality": "response-quality"}      # the one review agent, from the hub's records
    assert f"BUDGET = {agents.REVIEW_ONLY_CALLS}" in open(launch.settings_file.replace("agent-guard.json", "agent-guard.py")).read()
    frame = open(launch.append_system_prompt_file).read()
    assert "offers one agent, the review agent (response-quality)" in frame and "written deliverable" in frame and "needs no agent" in frame


def test_a_small_folder_and_goal_get_no_agents_no_tool_and_no_guard(tmp_path):
    runner, work = runner_in(tmp_path, 3, review_small_work=False)
    runner.prepare("short goal", "short goal", "", work, "small")
    launch = runner.launch_settings()
    assert "Agent" not in launch.tools and launch.agents_file is None and launch.settings_file is None and "SOLUTION AGENTS" not in open(launch.append_system_prompt_file).read()


def test_a_large_folder_gets_the_agents_the_guard_and_the_frame_note_under_a_fixed_budget(tmp_path):
    runner, work = runner_in(tmp_path, agents.OFFER_FILES, agent_calls=3)
    runner.prepare("goal", "goal", "", work, "large")
    launch = runner.launch_settings()
    assert launch.tools[-1] == "Agent" and launch.agents_file.endswith("solution-agents.json") and launch.settings_file.endswith("agent-guard.json")
    defined = json.load(open(launch.agents_file))
    assert sorted(defined) == ["judge-things", "read-things"] and defined["judge-things"]["model"] == "model-of-" + role_tiers.tier_for(agents.ROLE_OF_KIND["review"])
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
    assert result.subagent_report == {"offered": [], "ran": {}, "refused": {}}          # offered nothing: the record says so, which tells a small cut from a run that did not delegate
    runner.local.solution_of = {"read-things": "read-things"}
    shown = DeepResult(met=True)
    runner.report_agents(shown, work, None)       # no session record to read: offered is still known
    assert shown.subagent_report["offered"] == ["read-things"] and shown.subagent_calls == 0


# --- the review the hub asks for after the report ---------------------------------------------------------------------------------

def reviewing_runner(tmp_path, monkeypatch, written, calls=(), goal="Report the total of each port."):
    """A runner that has finished a session which wrote ``written`` (name: text); the resumed session is a stand-in that records the message it was given."""
    from hubofhubs.the_world.tools.deep import DeepResult
    from hubofhubs.the_world.tools.delegated_agent_sessions.solution_loop import snapshot
    from hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner import StreamJsonGoalRunner
    tmp_path.mkdir(parents=True, exist_ok=True)
    runner, work = runner_in(tmp_path, 1)
    (tmp_path / "work" / "src.md").write_text("port a: 4400\nport b: 5500\n")
    before = snapshot(work)
    for name, text in written.items():
        (tmp_path / "work" / name).write_text(text)
    runner.local.review_agent, runner.local.goal_text, runner.local.watch = "judge-things", goal, None
    sent = []

    def resumed(self, **kwargs):
        sent.append(kwargs)
        return DeepResult(met=True, session_id="s1", cost_usd=0.5, tokens=10)
    monkeypatch.setattr(StreamJsonGoalRunner, "run_goal_once", resumed)
    monkeypatch.setattr(runner, "session_calls", lambda result, root: list(calls))
    first = DeepResult(met=True, session_id="s1", cost_usd=0.2, tokens=5)
    return runner, work, before, first, sent


def test_a_deliverable_with_computed_figures_is_sent_to_the_review_agent_with_the_goal_in_the_same_session(tmp_path, monkeypatch):
    runner, work, before, first, sent = reviewing_runner(tmp_path, monkeypatch, {"answers.md": "A: 19950\nB: 988600\nC: 51610\n"})
    got = runner.ask_review(first, work, before, {}, None, None)
    assert len(sent) == 1 and sent[0]["resume_session_id"] == "s1"
    message = sent[0]["goal"]
    assert "judge-things" in message and "answers.md" in message and "Report the total of each port." in message and "foreground" in message
    assert got.cost_usd == 0.5 and got.tokens == 15 and got.review_stakes["computed"] == 3          # the CLI's cost is the session's running total, so it is not added twice


def test_no_review_is_asked_for_a_small_quoted_or_already_reviewed_deliverable(tmp_path, monkeypatch):
    runner, work, before, first, sent = reviewing_runner(tmp_path, monkeypatch, {"answers.md": "Port a carried 4400 and port b 5500.\n"})
    assert runner.ask_review(first, work, before, {}, None, None) is first and sent == [] and first.review_stakes["computed"] == 0       # quoted: no cost
    runner, work, before, first, sent = reviewing_runner(tmp_path / "again", monkeypatch, {"answers.md": "A: 19950\nB: 988600\nC: 51610\n"},
                                                         calls=[{"agent": "judge-things", "failed": False}])
    assert runner.ask_review(first, work, before, {}, None, None) is first and sent == []                                                 # the session reviewed it itself
    runner, work, before, first, sent = reviewing_runner(tmp_path / "third", monkeypatch, {"answers.md": "A: 19950\nB: 988600\nC: 51610\n"},
                                                         calls=[{"agent": "judge-things", "failed": True}])
    assert runner.ask_review(first, work, before, {}, None, None) is not first and len(sent) == 1                                          # a refused call did not review it
    runner, work, before, first, sent = reviewing_runner(tmp_path / "fourth", monkeypatch, {"answers.md": "A: 19950\nB: 988600\nC: 51610\n"})
    runner.local.review_agent = ""
    assert runner.ask_review(first, work, before, {}, None, None) is first and sent == []                                                 # no review agent offered
