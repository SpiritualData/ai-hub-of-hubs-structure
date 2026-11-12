# Focus Context

**Purpose:** Start a session from what the person already knows about their own focus, so "my practice" is answered from it first and files are searched only for the rest.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [Finding and preparing information for the Mind](../README.md) > Focus Context

Part of [Finding and preparing information for the Mind](../README.md)

## Focus Context (`focus-context`)

- Out of scope: Ranking pieces of text for an answer within a token budget (Context Retriever does that), building cards from files (Cards From Files), choosing the files of a working folder to show (Folder View), what a consumer's data model calls a focus (the consumer maps it onto the focus tag).
- Delegates to: context-retriever
- Entry call: `hubofhubs.run("focus-context", ...)`
- Selected implementation: The configured focus first (`configured_focus_context`)
- Metric: The person's own notes reach the brief, little else, nothing outside the scope
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../critical_thinking/decision_check/remainder.py) and 253 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Nothing gathered | `focus-context:no_context` | The session starts with the goal alone; a helper searches the files for the request's words on its own (the session as it was). | [`hubofhubs/the_intelligence/subconscious/focus_context/arms.py`](arms.py) |  |
| Notes found by the request's words | `focus-context:filesystem_search` | Ranks every note by how often the request's words occur in it, the focus and the scope ignored: what a helper finds when it searches for the word. | [`hubofhubs/the_intelligence/subconscious/focus_context/arms.py`](arms.py) |  |
| The configured focus first | `focus-context:configured_focus_context` | The notes of the person's configured sources through the Context Retriever's focus_first arm: the named focus ranked first (soft affinity), the scope fence kept, the focus's overview always offered, the newest notes of the focus added when the request touches it; then the brief with the rule to use them before searching, and the one line. | [`hubofhubs/the_intelligence/subconscious/focus_context/arms.py`](arms.py) | selected |

## Metrics

- The person's own notes reach the brief, little else, nothing outside the scope (`metric-focus-context`): leader `configured_focus_context`, 19 of 20 cases

## Problems

- Work starts without the person's own context (`hprob-work-starts-without-the-persons-own-context`): A person asks a session about their own practice, hobby or project ("find something interesting about my practice") and the session searches the files for the request's words, so the answer is built from whatever files share the word (a lookalike folder, another business's material) while the notes the person already saved about that focus are never read.

## Ideals

- The person's own context first (`hideal-the-persons-own-context-first`): A session about the person's own focus starts from what they already saved about it, and files are searched only for what that context does not say.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Finding and preparing information for the Mind](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
