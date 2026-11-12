# file_edit_goals

Can an arm make a single-file coding edit that has a written done-standard? This is the metric of File Editing only. Delegated Agent Sessions has its own component, `agent_sessions`, on general tasks that are not coding.

- **Cases** (`cases.json`, 30): small, self-contained coding goals drawn with a fixed seed (`build_cases.py`, seed 20261031) from the 164
  problems of HumanEval (MIT licence, https://github.com/openai/human-eval, data file read 2026-10-31). Each is "make this function pass its
  tests": a fresh temporary folder holds `solution.py` (signature and docstring, body `pass`) and `test_solution.py` (the benchmark's own
  tests, unchanged). The arm's only writable root is that folder.
- **Pass**: after the arm returns, `test_solution.py` is rewritten from the case (an arm cannot pass by editing its check) and pytest runs in
  a new process with a 30 second limit. Pass = exit code 0. The folder is deleted after each case.
- **Arms**: `fast_edit` (`impls/fast_edit.py`): one model call through the Claude CLI provider on the operator's subscription login (no key;
  `ANTHROPIC_API_KEY` is not passed on). The model is never named in the code: it is the model the tier chooser names for the tier on the day of the run,
  and `meter.model`, hence the `model` cell of `results.csv`, is that model (the role tier table matches a recorded run on it). The tier is `FILE_EDIT_TIER`
  (`fast`, `balanced` or `quality`; default `fast`). A tier other than fast must also be in the arm name, because the arm name is the `impl` cell the role
  tier table reads: `fast_edit` is the fast tier, `fast_edit@tier=balanced` and `fast_edit@tier=quality` the others (`FILE_EDIT_TIER=balanced` with the
  plain arm name is refused). The earlier Gemini arm is removed; rows recorded under it (model `gemini-2.5-flash-lite`) no longer count for any tier.
  Offline cassette record and replay work as for any metered arm (`--cassette`). The Claude Code CLI runners were measured on these cases once, before the
  split; they are agent sessions, not file edits, and are measured on `agent_sessions` now. `mcp_operations` writes through operations, not files, so it cannot attempt these cases.
- **No caller**: no consumer in this ecosystem wires a file writer, so `fast_edit` has no real caller today; the proposal is to retire File Editing, and until Joshua decides the component stays as it was.
- **Cost**: the CLI's own list-price estimate per call (informational on a subscription).
- **Free stage** (no model): `PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run file_edit_goals --impl none`
  (the check must fail on an untouched folder: 0/30). `--impl oracle` writes the reference solutions and must pass 30/30, which checks the
  check; it is not an arm and is not recorded.
- **Paid stages**: the same command with an arm name (`fast_edit`, `fast_edit@tier=balanced`, `fast_edit@tier=quality`), `--sample 3`, `--sample 10`, then the full set, one arm at a time.
- Limits: HumanEval is public and old, so a model may have seen the problems; it is easy, so differences between capable arms are small and
  need more cases to show. One author wrote the harness. The check sees whether the tests pass, not whether unrequested files changed.
