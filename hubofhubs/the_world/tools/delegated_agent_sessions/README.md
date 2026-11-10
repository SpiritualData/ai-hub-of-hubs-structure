# Delegated Agent Sessions

**Purpose:** Get open-ended work done by an agent in its own session.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Using the tools of the outside world](../README.md) > Delegated Agent Sessions

Part of [Using the tools of the outside world](../README.md)

## Delegated Agent Sessions (`delegated-agent-sessions`)

- Out of scope: Editing a single file (File Editing does that), calling one operation (Connected System Operations does that) and deciding the pieces (the Planner does that).
- Delegates to: file-editing, connected-system-operations, planner
- Entry call: `hubofhubs.run("delegated-agent-sessions", ...)`
- Selected implementation: `stream_json_goal_runner@provider=anthropic,tier=fast`
- Metric: Harness, context, sub-agents and recursion ranked, Open-ended work finished per cost and time (agent sessions), Hard deep work finished per cost and time (agent sessions)
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 134 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Claude Code, one shot | `delegated-agent-sessions:subprocess_goal_runner` | Runs Claude Code headless with a goal and a turn limit and reports whether the goal was met. Drives Anthropic models only (a Claude subscription login or a key); an arm is this harness with a tier, written subprocess_goal_runner@provider=anthropic,tier=fast. | [`hubofhubs/the_world/tools/delegated_agent_sessions/subprocess_runner.py`](subprocess_runner.py) |  |
| Claude Code, steerable session | `delegated-agent-sessions:stream_json_goal_runner` | Holds one live Claude Code session per run so the person can steer it while it works. Drives Anthropic models only. | [`hubofhubs/the_world/tools/delegated_agent_sessions/stream_runner.py`](stream_runner.py) |  |
| Agent Client Protocol runner | `delegated-agent-sessions:acp_deep_runner` | Runs each goal as one session against the Claude ACP agent. Drives Anthropic models only. | [`hubofhubs/the_world/tools/delegated_agent_sessions/acp_runner.py`](acp_runner.py) |  |
| Codex CLI, one shot | `delegated-agent-sessions:codex_cli_runner` | Runs Codex CLI headless (codex exec --json) once per goal with the prompt on stdin and reads its event stream for the report, tokens and cost. Drives OpenAI models only. | [`hubofhubs/the_world/tools/delegated_agent_sessions/headless_runner.py`](headless_runner.py) |  |
| opencode, one shot | `delegated-agent-sessions:opencode_runner` | Runs opencode headless (opencode run --format json) once per goal and reads its event stream for the report, tokens and cost. Drives any provider it holds a key for, so one harness serves Gemini, OpenAI, Anthropic or DeepSeek keys. | [`hubofhubs/the_world/tools/delegated_agent_sessions/headless_runner.py`](headless_runner.py) |  |

## Metrics

- Harness, context, sub-agents and recursion ranked (`metric-harness-context-subagents-recursion-ranked`)
- Open-ended work finished per cost and time (agent sessions) (`metric-delegated-agent-sessions`): leader `stream_json_goal_runner@provider=anthropic,tier=fast`, 18 of 18 cases
- Hard deep work finished per cost and time (agent sessions) (`metric-delegated-agent-sessions-hard`): leader `subprocess_goal_runner@provider=anthropic,tier=best`, 7 of 7 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
