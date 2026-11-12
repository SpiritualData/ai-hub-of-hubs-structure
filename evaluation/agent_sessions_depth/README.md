# agent_sessions_depth

Does depth help, or only cost more? The hard set (`agent_sessions_hard`) can be done in one session with no depth, so an arm that uses
sub-agents scoped to solutions, recalled context or a consumer's skills cannot win there, and an arm without them cannot lose. These nine
cases each need something that set does not, or show that depth is waste. The set is part of the metric
`metric-harness-context-subagents-recursion-ranked` and is the depth stage of `metric-delegated-agent-sessions-hard` (floor eight tenths,
pooled over at least three runs, after the hard floor).

- **Cases are public and synthetic**, built in code by `build_cases.py` into `cases.json` (neutral subjects: a nursery's sensors, a small report
  library, a shop's shipping rules, a warehouse's depots, a website's visit counts). Each is a folder, a goal and a code scorer; there is no
  model judge.

| Case | Stratum | What it needs, and why one session may do worse or pay more |
|---|---|---|
| `depth-parts-sites` | parts | five separable sites of many files each, most irrelevant to a given part; the report must hold each part's facts |
| `depth-solution-records` | records | solution records in the folder (a parent delegating to three children, each with a milestone, and a retired one); hidden tests per child, the retired code unchanged |
| `depth-skills-folder` | skills | the rule is only in a skills folder outside the work folder, handed as `skills_dir` to an arm that takes it |
| `depth-recall-known` | recall | an earlier finding handed as `recall` saves searching; a planted wrong claim in the folder must be rejected |
| `depth-small-simple` | small | a one-line fix: sub-agents are waste, and the cost, time and sub-agent calls show it |
| `depth-context-load` | context | five depots, seven long documents each (about a hundred thousand characters in all); each depot's answer is the latest adopted amendment of two rules, so most of its own documents must be read, in date order, ignoring proposed and withdrawn ones. One session carries all of it in one context for every later turn; separate workers each carry one depot and hand back a line |
| `depth-two-level-records` | records-two-level | records as an ESOI folder (`esoi.toml`, `esoi/solutions.csv`): a top solution delegating to three, one of which delegates to two, each with a milestone and its own hidden test; one leaf cannot be met (the carrier's rate table it names was never delivered), so its parent and the top cannot either. The report must say `<id>: met` or `<id>: unmet` for every solution and agree with the tests; a milestone reported met that its test does not show fails. A single session tends to report the whole as done |
| `depth-verify-claims` | verify | a recap states a total and a best month that do not follow from the monthly files once a correction note is applied, and repeats a cause with no source. The first plausible answer copies the recap; a separate reader that recomputes from the sources and looks for a source for each claim catches it. The scorer fails a wrong figure stated as fact, a total with no source file, and an unsourced claim stated as fact |
| `depth-small-lookup` | small-lookup | sixteen tiny notes (enough files to be offered sub-agents, almost no text) and a one-line question: delegation can only cost |

- **Ability first.** A run passes when it says it met the goal, the facts or the JSON answer are right (per part where the case has parts), the
  folder's tests pass, nothing that should stay the same changed (the skills folder included). For the two-level case the tests decide the truth
  of each milestone and the report is checked against them.
- **Cost and time** fold into one number by `[balance.agent_sessions_depth]` in `esoi.toml`, the same weights as the other sets, so one failed
  case is never bought back by a cheap run. A sub-agent used on a small case is noted, not failed.
- **What a run did with sub-agents is recorded.** `esoi/per_case.csv` has a fixed set of columns (the esoi library's), so the row the scorer
  returns carries the rest and `esoi/runs.csv` keeps the whole row of every case: `turns`, `subagent_calls` (calls that ran),
  `subagent_refused` (refused by the hook or failed), `agents_offered` (how many solution agents the run was offered; 0 means the work was sized
  too small) and `subagents` (`solution=count` pairs). The hard stage's rows carry the same keys (`agent_sessions_hard/score.py`, `run_fields`),
  from the result's `subagent_report`. An arm with no sub-agents adds nothing.
- **Arms** are those of `agent_sessions_hard`. `score.adapt` passes `skills_dir` and `recall` only to an arm whose constructor names them as
  parameters (read from the signature, never by arm name); other arms get the goal and the folder alone.
- **Offline proof** (free): `tests/test_agent_sessions_depth_baseline.py`. `broken/parrot.py` fails every case, `reference.py` (a hand-written
  correct result per case) passes every case, wrong reports fail the new cases, and `cases.json` must equal the builder's output.

      PYTHONPATH=.:../evolvable-structure/implementations/python python3 -m esoi run agent_sessions_depth \
        --impl 'native_tool_loop_runner@provider=anthropic,tier=fast' --max-calls 9 --record

  Repeat each arm at least three times, then refresh what consumers read.
- **Limits:** nine cases cannot separate close arms; synthetic and small; the skills case could be solved by an arm that searches the machine for
  the skills folder; on the fast tier a single session read the large folder in seconds at a cent, so the context case measures pass rate first
  and shows cost only as a small difference; the two-level and verification cases measure honesty about milestones and sources, which a good
  single session may also have.
