# Resolve a Reference

**Purpose:** Tie a phrase to the thing it names only when it is that thing.

Breadcrumb: [Top](../../../../esoi/README.md) > [How the AI processes information](../../README.md) > [What the Mind sees and does for one request](../README.md) > Resolve a Reference

Part of [What the Mind sees and does for one request](../README.md)

## Resolve a Reference (`resolve-a-reference`)

- Out of scope: Deciding whether the matched thing may be changed (the caller's own safety rule decides that) and finding the candidates (the caller supplies them).
- Delegates to: model-plumbing
- Entry call: `hubofhubs.run("resolve-a-reference", ...)`
- Selected implementation: Id and exact match (`exact_match`)
- Metric: References settled without a wrong match
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../critical_thinking/decision_check/remainder.py) and 237 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Id and exact match | `resolve-a-reference:exact_match` | Matches by id, by the whole name or an alias, or by every word of the phrase being a whole word of one candidate's name (a caller can ask for the whole name only); two candidates that fit, or none, is an abstain. | [`hubofhubs/the_intelligence/mind/reference_resolver/resolving.py`](resolving.py) | selected |
| A model judges sameness | `resolve-a-reference:model_judged` | One model call is shown the phrase and the candidates and says which is the very same thing, or none; an answer outside the candidates offered raises. | [`hubofhubs/the_intelligence/mind/reference_resolver/resolving.py`](resolving.py) |  |
| Most shared words | `resolve-a-reference:shared_words` | The candidate sharing the most words with the phrase wins; it abstains only when no word is shared. | [`hubofhubs/the_intelligence/mind/reference_resolver/resolving.py`](resolving.py) |  |

## Metrics

- References settled without a wrong match (`metric-resolve-a-reference`): leader `exact_match`, 28 of 32 cases

## Problems

- A reference is settled by shared words (`hprob-reference-settled-by-shared-words`): A phrase that refers to a person, a goal or a post is matched to a candidate by the words they share, in several parts that each do it their own way, and none of them can say that no candidate is meant.

## Ideals

- No match without the thing itself (`hideal-no-reference-without-the-thing-itself`): A phrase is tied to a candidate only when it is that candidate; otherwise the system says it does not know and goes on without guessing.

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [What the Mind sees and does for one request](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
