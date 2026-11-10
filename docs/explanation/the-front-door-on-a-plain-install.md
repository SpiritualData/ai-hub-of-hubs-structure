# The front door on a plain install

A person who installs the hub with `pip install hubofhubs` and has only a logged-in Claude CLI (no vendor key) must get a working
answer, not a setup task. Four rules make that true, and one measure keeps it true.

## 1. The install carries what the selected arms import

Every arm declares its Python needs with `REQUIRES`, each naming the extra of `pyproject.toml` that provides the module. The base
`dependencies` are those libraries for the currently selected arm of every solution, written between two marker comments by
`python3 scripts/sync_dependencies.py` (`hubofhubs/the_self/integrity/base_dependencies.py` derives them; a need declared optional is left out
because the arm degrades without it). A test fails when a selected arm needs a library the base install lacks, or when the marked lines are not
current. The extras stay for the alternatives that are not selected. Selecting a different arm by metric changes the base list on the next sync.

## 2. An arm that cannot run here is replaced by the best-measured arm that can

A selected arm may need a library that is not installed, a key that is not in the environment mapping, a program that is not on the path, or an
object only a consumer can pass. `hubofhubs.the_self.assembler.availability` checks each solution's selected arm against the mapping through the
arm's own declarations (esoi's requirement checks), and where one is unmet it takes the first arm in `hubofhubs/arm_order.json` whose needs are met.
That file is the leaderboard order of every solution, written by `scripts/sync_arm_order.py` from `esoi/results.csv` (an installed copy has no
results, so the order ships with the package; a test fails when it is not current). Availability chooses among measured arms and never by
preference; an arm the caller names is kept; a solution no arm can serve keeps its selected arm and is reported as a pending step. With only the
Claude CLI, web search runs as `claude_login` and the model caller as `claude_cli`. What stood in is `Result.stood_in`, a detail for anyone who
asks (`--json`), never a message.

## 3. A step that only enriches never fails the answer

Each flow step is declared by how it is called: `take` for a step the answer depends on, `support` (`hubofhubs/the_self/steps.py`) for a step that
only enriches it (the person's context, retrieval, a check, a record, a worker such as web search). A supporting step that cannot run is an
`unavailable` step, and the flow goes on with what it has. A worker of a supporting category (`SUPPORTING` in the Delegation arm) that fails is a
result that says it was unavailable and how to enable it, never an error. Nothing is shown when the answer did not need it.

## 4. What the person sees

- Nothing when a stand-in did the job.
- One plain line in `Result.note` only when the answer is materially weaker and the person can act on it, with how.
- When nothing else answered, the answer is that plain fact and how to enable the missing step.
- The stop reason is the real one (`Result.stopped`): `unavailable`, `asked` (a decision is the person's), `final` (a worker's own message),
  `authority`, `cancelled`, or `budget` only when the attempts were spent without the goal met.
- A needed step that breaks ends as a message, never a traceback.

The test of any message: if it would appear for most people on a plain install, it is a defect to fix (make the default work) or it is not worth
saying.

## 5. A question about the hub is not searched

"What can you do?" is answered from the hub's own records (Role Understanding, through the Delegation arm), with no web search and no model call.
A file named in the request is read in the folder the work runs in; a change to it asks for a go-ahead and says how to give one (`ahohs work`).

## The measure

`esoi run plain_install --impl front_door --max-calls 60` scores ten scripted ordinary inputs on a machine with only a program named `claude` (a replay
of the CLI's JSON reply envelope; nothing else is replaced): each must end with a real answer or an honest, actionable message, no raw error text and
zero warnings. `--impl real_login` runs the same cases on the real login (it spends the allowance, so a person authorizes it). `tests/test_out_of_the_box.py`
runs the same cases in the test suite.
