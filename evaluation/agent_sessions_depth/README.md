# agent_sessions_depth

Does depth help, or only cost more? The hard set (`agent_sessions_hard`) can be done in one session with no depth, so an arm that uses
sub-agents scoped to solutions, recalled context or a consumer's skills cannot win there, and an arm without them cannot lose. These five
cases each need something that set does not. The set is part of the metric `metric-harness-context-subagents-recursion-ranked` and is the
depth stage of `metric-delegated-agent-sessions-hard` (floor four of five, pooled over at least three runs, after the hard floor).

- **Cases are public and synthetic**, built in code by `build_cases.py` into `cases.json` (neutral subjects: a nursery's sensors, a small report
  library, a shop's shipping rules). Each is a folder, a goal and a code scorer; there is no model judge.

| Case | Stratum | What it needs |
|---|---|---|
| `depth-parts-sites` | parts | five separable sites of many files each, most irrelevant to a given part; the report must hold each part's facts |
| `depth-solution-records` | records | solution records in the folder (a parent delegating to three children, each with a milestone, and a retired one); hidden tests per child, the retired code unchanged |
| `depth-skills-folder` | skills | the rule is only in a skills folder outside the work folder, handed as `skills_dir` to an arm that takes it |
| `depth-recall-known` | recall | an earlier finding handed as `recall` saves searching; a planted wrong claim in the folder must be rejected |
| `depth-small-simple` | small | a one-line fix: sub-agents are waste, and the cost, time and sub-agent calls show it |

- **Ability first.** A run passes when it says it met the goal, the facts or the JSON answer are right (per part where the case has parts), the
  folder's tests pass, nothing that should stay the same changed (the skills folder included).
- **Cost and time** fold into one number by `[balance.agent_sessions_depth]` in `esoi.toml`, the same weights as the other sets, so one failed
  case is never bought back by a cheap run. The row also records calls, seconds, tokens and, when the run's result has attributes named
  `subagent_calls` and `turns`, those. A sub-agent used on the small case is noted, not failed.
- **Arms** are those of `agent_sessions_hard`. `score.adapt` passes `skills_dir` and `recall` only to an arm whose constructor names them as
  parameters (read from the signature, never by arm name); other arms get the goal and the folder alone.
- **Offline proof** (free): `tests/test_agent_sessions_depth_baseline.py`. `broken/parrot.py` fails every case, `reference.py` (a hand-written
  correct result per case) passes every case, and `cases.json` must equal the builder's output.

      PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run agent_sessions_depth \
        --impl 'native_tool_loop_runner@provider=anthropic,tier=fast' --max-calls 5 --record

  Repeat each arm at least three times, then refresh what consumers read.
- **Limits:** five cases cannot separate close arms; synthetic and small; the skills case could be solved by an arm that searches the machine for
  the skills folder; the arm's own result must expose `subagent_calls` and `turns` for those columns to fill.
