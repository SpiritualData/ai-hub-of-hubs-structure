# agent_sessions

Can an agent that is handed a general task in its own session finish it and report what the person needs? This is the metric of Delegated Agent Sessions.
It shares no case set and no score with File Editing: an agent session is open-ended work, and a file edit is one bounded change.

- **Cases** (`cases.json`, 12, written by `build_cases.py` for this evaluation): tasks that are not coding. Each is a small folder of plain files, a goal and
  the facts the final report must hold: read notes and name a city, compare two offers, count and list files, work out a date, route a request by an owner
  table, summarise in one sentence, propose tidy names without renaming, add up a column, find a contradiction, answer yes or no from a list, put steps in order.
- **Pass**: the run says it met the goal, its final report holds every expected fact (case-insensitive), and the files are unchanged (the tasks read and report).
- **Arms**: `subprocess_goal_runner` and `stream_json_goal_runner` (the Claude Code CLI with model alias `haiku`, 15 turns, no user or project settings, no ambient MCP
  servers, `HOME` and `PATH` only) and `acp_deep_runner` (needs the `claude-agent-acp` agent binary, which is not installed on the measuring machine, so it is not
  measured: a circumstance, not a result).
- **Cost**: the runners run on a flat subscription: the recorded dollars are the CLI's own estimate at list price, not money charged, and a "model call" is one
  agent session. Cost and time are folded into the one number by `[balance.agent_sessions]` in `esoi.toml`.
- **Free stage** (no model): `PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run agent_sessions --impl none` (0/12).
- **Paid stages**: the same command with an arm name, `--sample 3`, `--sample 10`, then the full set, one arm at a time, with a call budget and approval.
- Limits: twelve cases are too few to separate close arms, one author wrote them, and the reports are judged by the facts they hold, not by how well they are written.
