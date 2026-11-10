# The format a model is trained on

A harness is the loop around a model: the model writes an action, code runs it, the result goes back. The words of the action are a format, and a model
does better in the format it was trained on. Researched 2026-11-10; the sources are rows of `hubofhubs/registry/hub_findings.csv` and
`hub_evidence.csv` (area `agent_action_format`, under Delegated Agent Sessions).

## What the providers say and do

- **Anthropic** documents its bash tool (`bash_20250124`) and text editor tool (`text_editor_20250728`, commands `view`, `str_replace`, `create`, `insert`) as
  client tools: the model replies with a tool call and the application runs it. The bash page says the tool is schema-less because the schema is built into
  the model and cannot be modified. Anthropic's guide on writing tools for agents (2025-09-11) says models tend to perform better with formats that match
  their training data, and that the best of the formats it names (XML, JSON, Markdown) varies by task and is to be chosen by evaluation.
- **Claude Code** is the harness built on those tools. Its tools today are Bash, Read, Edit, Write, Glob, Grep, WebSearch, WebFetch, NotebookEdit, an agent
  tool for sub-agents and task tools (TaskCreate, TaskUpdate and others; the older TodoWrite is off by default in the installed version). Flags choose a lean
  launch: `--tools`, `--append-system-prompt-file`, `--setting-sources`, `--strict-mcp-config`, `--max-budget-usd`.
- **OpenAI** documents an `apply_patch` tool whose diffs are in a V4A format, and Codex CLI sandbox modes. **Gemini CLI** has its own file tools
  (`read_file`, `write_file`, `replace`, `glob`, `grep_search`) and `run_shell_command`. Neither page was found to say the models were trained on the format.
- **Aider** measured edit formats: on its 89-task refactoring benchmark GPT-4 Turbo went from 20 percent with search and replace blocks to 61 percent with
  unified diffs, and Aider picks a format per model. The format changed the result on the same model.

## What it implies

For a Claude model, the native loop with its own tool names and schemas is the trained format. A private text protocol (the hub loop's `RUN:`, `READ:`,
`STATE:` lines and search and replace blocks) is off distribution: the model can learn it from a prompt, but it spends calls on the protocol, it sometimes
writes its actions in the trained markup instead (a real run did: `<invoke name="RUN">`, which the parser did not read), and its habits of looking things up
in its own loop (history, a database file, the web) do not carry over. The hub's parser now reads that markup, and the metric below counts it.

The text protocol is still the cheaper loop where a task ends in one or two calls, because it carries no agent system prompt and no tool schemas. So the hub
keeps both, as arms of Delegated Agent Sessions, and lets the metric choose.

## The two arms side by side

`solution_loop_runner` is the hub as its own harness over pure text completions. `native_tool_loop_runner` keeps the native loop and adds what the hub is
best at: the Folder View's picks and the folder outline, the folders left out and why, a short plan, a rule to discover before asking, and the code check of
written text after the session reports. It launches one lean Claude Code session (no settings sources, strict MCP, a chosen tool list, a private temporary
folder) and reuses the stream runner for stop, steer and resume. Both are on trial; neither is chosen for a consumer until the owner promotes it.

Same model (fast tier), subscription login, recorded 2026-11-10:

| Arm | Open-ended, 18 cases | Hard set, 9 cases |
|---|---|---|
| Hub text loop (`solution_loop_runner`) | 18 of 18, $0.011, 116 s | 7 of 9, $0.052, 411 s |
| Hub frame on the native loop (`native_tool_loop_runner`) | 17 of 18, $0.023, 93 s | 8 of 9, $0.099, 307 s |
| Claude Code, steerable session (`stream_json_goal_runner`, the selected arm) | 18 of 18, $0.043, 104 s | 9 of 9, $0.082, 285 s |

The open-ended cases end in one or two calls and cannot tell the loops apart; the hard set holds two long cases (ten steps, scripts to write, a database file
standing in for a spreadsheet, one fact only found by looking, a hidden test that passes only when the rows were written) that were added because the short
cases did not predict real work. All three arms passed both long cases in the recorded runs, so on this evidence the long cases do not separate the loops on pass rate; what separates them is cost (the text loop is cheapest on tasks that end in one or two calls, the plain Claude Code session was cheapest of the two Claude Code arms on the hard set) and the single misses, which move from run to run (the native arm failed one open-ended case and one judged deliverable in the final runs and two deliverables in an earlier one). One run per arm cannot rank them; repeat before claiming a difference.

## Limits

One run per arm and case; the long cases are two, synthetic, written by one author; a Claude judge rates the deliverable cases of the hard set; the dollars of
the Claude Code arms are the CLI's list-price estimate on a flat subscription; other providers' formats are recorded and not built.
