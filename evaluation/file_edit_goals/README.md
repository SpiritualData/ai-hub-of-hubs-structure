# file_edit_goals

Can an arm make a single-file coding edit that has a written done-standard? This is the metric of File Editing only. Delegated Agent Sessions has its own component, `agent_sessions`, on general tasks that are not coding.

- **Cases** (`cases.json`, 30): small, self-contained coding goals drawn with a fixed seed (`build_cases.py`, seed 20261031) from the 164
  problems of HumanEval (MIT licence, https://github.com/openai/human-eval, data file read 2026-10-31). Each is "make this function pass its
  tests": a fresh temporary folder holds `solution.py` (signature and docstring, body `pass`) and `test_solution.py` (the benchmark's own
  tests, unchanged). The arm's only writable root is that folder.
- **Pass**: after the arm returns, `test_solution.py` is rewritten from the case (an arm cannot pass by editing its check) and pytest runs in
  a new process with a 30 second limit. Pass = exit code 0. The folder is deleted after each case.
- **Arms**: `fast_edit` (one model call, `gemini-2.5-flash-lite`, the cheapest Gemini text model, priced from `tier_prices.csv`). The Claude Code CLI runners were measured on these cases once, before the split; they are agent sessions, not file edits, and are measured on `agent_sessions` now. `mcp_operations` writes through operations, not files, so it cannot attempt these cases.
- **No caller**: no consumer in this ecosystem wires a file writer, so `fast_edit` has no real caller today; the proposal is to retire File Editing, and until Joshua decides the component stays as it was.
- **Cost**: `fast_edit` is tokens times the registry price.
- **Free stage** (no model): `PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run file_edit_goals --impl none`
  (the check must fail on an untouched folder: 0/30). `--impl oracle` writes the reference solutions and must pass 30/30, which checks the
  check; it is not an arm and is not recorded.
- **Paid stages**: the same command with an arm name, `--sample 3`, `--sample 10`, then the full set, one arm at a time.
- Limits: HumanEval is public and old, so a model may have seen the problems; it is easy, so differences between capable arms are small and
  need more cases to show. One author wrote the harness. The check sees whether the tests pass, not whether unrequested files changed.
