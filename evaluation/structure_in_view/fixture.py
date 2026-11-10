"""The invented records and sessions of the Structure In View cases: three solutions in a delegation hierarchy and the events of a session that works on them.
Written by hand; no arm produces them. Standard library only."""

TABLES = {
    "solutions": [
        {"solution_id": "root-sol", "name": "Root Solution", "purpose": "Root purpose text.", "approach": "Root approach text.", "out_of_scope": "",
         "milestones": "1. First goal [met: 2026-11-01] 2. Second goal", "problem_ids": "p-one;p-missing", "ideal_ids": "i-one", "authoritative_metric_id": "m-root",
         "selected": "arm_a", "delegates_to": "child-a;child-b;ghost-kid"},
        {"solution_id": "child-a", "name": "Child A", "purpose": "Child A purpose text.", "approach": "Child A approach text.", "milestones": "1. A goal",
         "problem_ids": "", "ideal_ids": "", "authoritative_metric_id": "", "selected": "", "delegates_to": "none"},
        {"solution_id": "child-b", "name": "Child B", "purpose": "Child B purpose text.", "approach": "Child B approach text.", "milestones": "",
         "problem_ids": "", "ideal_ids": "", "authoritative_metric_id": "", "selected": "", "delegates_to": "none"},
    ],
    "problems": [{"problem_id": "p-one", "name": "Problem One", "problem": "Problem one text.", "who_has_it": "Problem one people.", "why_it_matters": "Problem one matters."}],
    "ideals": [{"ideal_id": "i-one", "name": "Ideal One", "principle": "Ideal one principle.", "state_description": "Ideal one state."}],
    "metrics": [{"metric_id": "m-root", "name": "Root Metric", "command": "esoi run root_sol --impl arm_a"}],
    "implementations": [{"implementation_id": "root-sol:arm_a", "solution_id": "root-sol", "name": "Arm A Name"}],
    "results": [{"date": "2026-11-01", "component": "root_sol", "impl": "arm_a", "cases": "10", "passed": "8", "balanced": "0.8"},
               {"date": "2026-11-05", "component": "root_sol", "impl": "arm_a", "cases": "10", "passed": "9", "balanced": "0.91"},
               {"date": "2026-11-09", "component": "root_sol", "impl": "arm_b", "cases": "10", "passed": "3", "balanced": "0.3"}],
}

FIELD_TEXTS = ["Root purpose text.", "Root approach text.", "Child A purpose text.", "Child A approach text.", "Child B purpose text.", "Problem one text.",
               "Ideal one principle.", "Arm A Name", "Root Metric", "First goal"]

SESSION = [
    {"type": "run-started", "goal": "improve the root", "solution": "root-sol", "harness": "loop"},
    {"type": "agent-started", "agent_id": "root-sol", "parent_id": "main", "task": "Root Solution", "solution": "root-sol"},
    {"type": "agent-started", "agent_id": "root-sol-child-a", "parent_id": "root-sol", "task": "Child A", "solution": "child-a"},
    {"type": "agent-started", "agent_id": "root-sol-child-a-ghost-sol", "parent_id": "root-sol-child-a", "task": "Ghost", "solution": "ghost-sol"},
    {"type": "agent-started", "agent_id": "root-sol-child-b", "parent_id": "root-sol", "task": "Child B", "solution": "child-b"},
    {"type": "agent-started", "agent_id": "helper-x", "parent_id": "root-sol", "task": "tidy notes", "solution": ""},
    {"type": "step", "agent_id": "root-sol-child-a", "step_id": "s1", "kind": "edit", "label": "a.py", "state": "done"},
    {"type": "agent-ended", "agent_id": "root-sol-child-b", "state": "unmet", "calls": 2},
    {"type": "agent-ended", "agent_id": "root-sol-child-a-ghost-sol", "state": "met", "calls": 1},
]
TWO_AGENTS = [
    {"type": "run-started", "goal": "g", "solution": "root-sol"},
    {"type": "agent-started", "agent_id": "r1", "parent_id": "main", "task": "first round", "solution": "child-a"},
    {"type": "agent-started", "agent_id": "r2", "parent_id": "main", "task": "second round", "solution": "child-a"},
    {"type": "agent-ended", "agent_id": "r1", "state": "failed", "calls": 1},
]
EVENTS = {"session": SESSION, "two_agents": TWO_AGENTS, "none": []}
