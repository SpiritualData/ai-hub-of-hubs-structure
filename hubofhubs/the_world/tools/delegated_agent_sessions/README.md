# Delegated Agent Sessions

**Purpose:** Get open-ended work done by an agent in its own session.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Using the tools of the outside world](../README.md) > Delegated Agent Sessions

Part of [Using the tools of the outside world](../README.md)

## Delegated Agent Sessions (`delegated-agent-sessions`)

- Out of scope: Editing a single file (File Editing does that), calling one operation (Connected System Operations does that) and deciding the pieces (the Planner does that).
- Delegates to: file-editing, connected-system-operations, planner
- Entry call: `hubofhubs.run("delegated-agent-sessions", ...)`
- Selected implementation: Claude Code, steerable session (`stream_json_goal_runner`)
- Metric: Harness, context, sub-agents and recursion ranked, Goal met by its own tests (agent sessions)
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 124 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Claude Code, one shot | `delegated-agent-sessions:subprocess_goal_runner` | Runs Claude Code headless with a goal and a turn limit and reports whether the goal was met. | [`hubofhubs/the_world/tools/delegated_agent_sessions/subprocess_runner.py`](subprocess_runner.py) |  |
| Claude Code, steerable session | `delegated-agent-sessions:stream_json_goal_runner` | Holds one live Claude Code session per run so the person can steer it while it works. | [`hubofhubs/the_world/tools/delegated_agent_sessions/stream_runner.py`](stream_runner.py) | selected |
| Agent Client Protocol runner | `delegated-agent-sessions:acp_deep_runner` | Runs each goal as one session against the Claude ACP agent. | [`hubofhubs/the_world/tools/delegated_agent_sessions/acp_runner.py`](acp_runner.py) |  |

## Metrics

- Harness, context, sub-agents and recursion ranked (`metric-harness-context-subagents-recursion-ranked`)
- Goal met by its own tests (agent sessions) (`metric-delegated-agent-sessions`): leader `none`, 0 of 12 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
