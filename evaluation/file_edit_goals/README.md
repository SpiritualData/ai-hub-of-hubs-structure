# file_edit_goals

Can an arm that changes files meet a goal that has a written done-standard? The act-in-the-world seat (the Body), file-changing arms only.

- **Cases** (`cases.json`, 30): small, self-contained coding goals drawn with a fixed seed (`build_cases.py`, seed 20261031) from the 164
  problems of HumanEval (MIT licence, https://github.com/openai/human-eval, data file read 2026-10-31). Each is "make this function pass its
  tests": a fresh temporary folder holds `solution.py` (signature and docstring, body `pass`) and `test_solution.py` (the benchmark's own
  tests, unchanged). The arm's only writable root is that folder.
- **Pass**: after the arm returns, `test_solution.py` is rewritten from the case (an arm cannot pass by editing its check) and pytest runs in
  a new process with a 30 second limit. Pass = exit code 0. The folder is deleted after each case.
- **Arms**: `fast_edit` (one model call, `gemini-2.5-flash-lite`, the cheapest Gemini text model, priced from `tier_prices.csv`),
  `subprocess_goal_runner` and `stream_json_goal_runner` (the Claude Code CLI with model alias `haiku`, 15 turns and 240 seconds per goal,
  no user or project settings, no ambient MCP servers, `HOME` and `PATH` only). `acp_deep_runner` needs the `claude-agent-acp` agent binary,
  which is not installed on the measuring machine, so it is not measured (a circumstance, not a result). `mcp_operations` writes through
  operations, not files, so it cannot attempt these cases and is not compared here.
- **Circumstance**: the two groups use different models (Gemini flash-lite for `fast_edit`, Claude haiku for the CLI runners), because
  `fast_edit` needs a model provider and the hub has none backed by the CLI. A difference between the groups mixes harness and model; the two
  CLI runners share a model and differ only in harness.
- **Cost**: `fast_edit` is tokens times the registry price. The CLI runners run on a flat subscription: the recorded dollars are the CLI's own
  estimate at list price, not money charged, and a "model call" is one agent session (the CLI does not report its turn count to the runner).
- **Free stage** (no model): `PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run file_edit_goals --impl none`
  (the check must fail on an untouched folder: 0/30). `--impl oracle` writes the reference solutions and must pass 30/30, which checks the
  check; it is not an arm and is not recorded.
- **Paid stages**: the same command with an arm name, `--sample 3`, `--sample 10`, then the full set, one arm at a time.
- Limits: HumanEval is public and old, so a model may have seen the problems; it is easy, so differences between capable arms are small and
  need more cases to show. One author wrote the harness. The check sees whether the tests pass, not whether unrequested files changed.
