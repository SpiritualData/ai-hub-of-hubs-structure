# Delegated Agent Sessions

*ESOI records kept beside the code in `hubofhubs/the_world/tools/delegated_agent_sessions`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The AI uses the tool of each category the person's authority allows, and a category gains a better integration without any product rewriting its code.

These are the solutions of [Using the tools of the outside world](../README.md).

## How the solutions fit together

Tools lets the AI use the tool of a category and refuses a category the authority does not allow. Web Search brings in the live web. File Reading reads the files of a folder. File Editing changes one file by instruction. Connected System Operations calls a write operation of a connected system. Delegated Agent Sessions gives open-ended work to an agent that runs in its own session.

## Delegated Agent Sessions (`delegated-agent-sessions`)

Get open-ended work done by an agent in its own session.

- Entry call: `hubofhubs.run("delegated-agent-sessions", ...)`
- Selected implementation: Claude Code, steerable session (`stream_json_goal_runner`)
- Metric: Harness, context, sub-agents and recursion ranked, Goal met by its own tests (agent sessions)
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 122 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Claude Code, one shot | `delegated-agent-sessions:subprocess_goal_runner` | [`hubofhubs/the_world/tools/delegated_agent_sessions/subprocess_runner.py`](subprocess_runner.py) |  |
| Claude Code, steerable session | `delegated-agent-sessions:stream_json_goal_runner` | [`hubofhubs/the_world/tools/delegated_agent_sessions/stream_runner.py`](stream_runner.py) | selected |
| Agent Client Protocol runner | `delegated-agent-sessions:acp_deep_runner` | [`hubofhubs/the_world/tools/delegated_agent_sessions/acp_runner.py`](acp_runner.py) |  |

## Metrics

- Harness, context, sub-agents and recursion ranked (`metric-harness-context-subagents-recursion-ranked`)
- Goal met by its own tests (agent sessions) (`metric-delegated-agent-sessions`): leader `none`, 0 of 12 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)
