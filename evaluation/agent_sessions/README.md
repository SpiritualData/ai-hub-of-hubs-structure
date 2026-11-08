# agent_sessions

Can an agent handed open-ended work in its own session finish it, and at what cost and speed? This is the metric of Delegated Agent Sessions.
It shares no case set and no score with File Editing: an agent session is open-ended work, and a file edit is one bounded change.

- **Arms**: an arm is a harness, the provider it drives and a tier, written `<harness>@provider=<p>,tier=<t>` (an esoi variant). The harness
  gets `provider` and `tier` as constructor arguments and takes the tier's model from the hub's tier chooser, so no model name is written
  here. Harnesses: `subprocess_goal_runner`, `stream_json_goal_runner`, `acp_deep_runner` (Claude Code, Anthropic only), `codex_cli_runner`
  (Codex CLI, OpenAI only) and `opencode_runner` (opencode, any provider). `none` is the zero bound.
- **Cases** (`cases.json`, written by `build_cases.py`), three kinds in the `stratum` field:
  - `report` (12): read a small folder and report a fact; the report must hold every expected fact and the files stay unchanged.
  - `code` (3): make a file pass its own tests; the harness rewrites the tests before checking, so editing them cannot pass.
  - `deliverable` (3), shaped like milestone work: a video script to a written rubric, research from source files that cites each file,
    a dated plan from meeting notes. The written file is checked against the rubric (word range, required words, nothing forbidden, order).
- **Pass**: the run says it met the goal, the files it was not asked to change are unchanged, and the kind's check passes.
- **Credentials**: the worker starts from `HOME` and `PATH`, plus the credential variables of the arm's provider read from the running
  process. A Claude Code arm uses the machine's Claude Code login.
- **Cost**: Claude Code arms run on a flat subscription; their dollars are the CLI's own estimate at list price. opencode reports its
  provider's cost per step; Codex is priced from the hub's price table. Cost and time are folded into one number by
  `[balance.agent_sessions]` in `esoi.toml`.
- **Stages** (the cascade of `metric-delegated-agent-sessions`): idea ratings in `arm_ideas.csv` beside the solution; the offline tests
  (`test_headless_runner.py`, the Claude Code runner tests); public priors (`public_priors.csv`); one real case
  (`--sample 1`), two of each kind (`--sample 6`), then the full set. Each paid run takes `--max-calls` and `--record`:

      PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run agent_sessions \
        --impl 'opencode_runner@provider=gemini,tier=fast' --sample 6 --max-calls 8 --record

  After recording, refresh the snapshot the consumers read: `python3 -m hubofhubs.the_world.tools.delegated_agent_sessions.arm_choice`.
- **Limits**: eighteen cases from one author cannot separate close arms; deliverables are judged by rubric terms, not by how well they read;
  the research case uses local files, not the live web.
