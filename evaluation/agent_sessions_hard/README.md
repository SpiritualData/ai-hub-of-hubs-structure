# agent_sessions_hard

The hard stage of Delegated Agent Sessions (`metric-delegated-agent-sessions-hard`): real deep work, the kind that takes minutes and
fails on a weak tier. The cases of `agent_sessions` are short enough that every tier passes them, so they cannot tell tiers apart; these can.

- **Cases are private.** Each case is a JSON file in a private folder outside this repository, built from past deep runs. `cases.json` here
  holds only each case's id, kind (`stratum`) and the digest of its body, so a changed private case is a changed case set.
  `AGENT_SESSIONS_HARD_CASES` names the private folders (separated by the path separator); `build_cases.py` rewrites the stubs.
- **Coding cases** (`code`): a small multi-file package modelled on a real deep task, the tests the agent sees, and hidden tests written to
  the rules the goal states. All tests are written back and run after the agent; every one must pass, and the files the goal did not open
  must be unchanged.
- **Deliverable cases** (`deliverable`): the real records a milestone turn read and the request; the agent writes the file. A judge on the
  strongest Anthropic tier rates each rubric item and quotes the words that decide it; a pass whose quote is in neither the deliverable nor
  the records does not count. Every item must pass, within the stated word range.
- **Arms** are those of `agent_sessions` (`<harness>@provider=<p>,tier=<t>`), plus an optional instructions pack
  (`instructions=<name>`): the text of `<name>.md` in the folders `AGENT_INSTRUCTION_PACKS` names, added to every run's instructions.
  A pack whose licence does not allow it here stays in a private folder.
- **Reading by hand:** with `AGENT_SESSIONS_HARD_KEEP=1`, each deliverable and its verdicts are saved in `kept/` of the case's own private
  folder.
- **Cost and time** fold into one number by `[balance.agent_sessions_hard]` in `esoi.toml`. The judge's call is not the arm's cost; its
  time is inside each case's seconds, the same for every arm.

      AGENT_SESSIONS_HARD_CASES=... AGENT_INSTRUCTION_PACKS=... PYTHONPATH=.:../evolvable-structure/implementations/python \
        python3 -m esoi run agent_sessions_hard --impl 'stream_json_goal_runner@provider=anthropic,tier=fast' --max-calls 9 --record

  Then refresh what consumers read: `python3 -m hubofhubs.the_world.tools.delegated_agent_sessions.arm_choice`.
- **Limits:** seven cases; the coding cases are rebuilt packages, not the real repositories; a Claude judge rates Claude arms.
