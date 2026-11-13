# answer_fidelity

Measured evidence for the answer check of Delegated Agent Sessions (`hubofhubs/the_world/tools/delegated_agent_sessions/answer_check.py`): after a run whose result is an
answer, one fast-tier call holds the answer to the person's own first message and says, part by part, whether it did what was asked, about the subject named. It is a part-level
metric of the solution (`metric-answer-fidelity`, parent `metric-delegated-agent-sessions`), run on the model call of the check only, not on a whole session.

- **Cases** (18, invented, `build_cases.py`): 5 `drift` (the answer is about another subject or invents another task), 5 `partial` (one of two asked parts done), 5 `correct`, 3
  `honest_none` (the answer says plainly, with what was looked at, that nothing was found about the named subject, and gives its own view). Each case also holds the agent's own
  restatement of the goal (`paraphrase`).
- **Arms**: `no_check` (the run as it was before, no calls), `answer_check@input=original` (the check the hub runs, reading the person's words) and
  `answer_check@input=paraphrase` (the reference: the same check reading the restated goal).
- **Score, fixed before scoring** (`score.py`): the mean of detection (drift and partial cases flagged) and one minus the false-alarm rate (correct and honest cases flagged); an arm
  that never flags scores 0.5.
- **Run**: `env -u ANTHROPIC_API_KEY esoi run answer_fidelity --impl answer_check@input=original --max-calls 18 --keep-going --record --force "<reason>"` (paid on the Claude CLI
  login, the fast tier through the `answer_check` role; no key, never Gemini). Free baseline: `--impl no_check`. The whole stage is about 40 calls (a 3-case stage run, then 18
  per model arm).
- **Reading it**: the cases are short and invented, and the paraphrases are written to model the drift, so the paraphrase arm shows what reading a restatement costs and is not a
  claim about every restatement.
