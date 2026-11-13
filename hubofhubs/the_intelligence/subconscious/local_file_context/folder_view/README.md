# Folder View

**Purpose:** Choose the files of a working folder a piece of work should be shown first, and never read what is risky or unlikely to help, for any programming language and tool.

Breadcrumb: [Top](../../../../../esoi/README.md) > [How the AI processes information](../../../README.md) > [Finding and preparing information for the Mind](../../README.md) > [Local File Context](../README.md) > Folder View

Part of [Local File Context](../README.md)

## Folder View (`folder-view`)

- Out of scope: Ranking pieces of text for an answer within a token budget from a corpus already read (Context Retriever does that), building cards from the files (Cards From Files does that), offering what was not asked for (Intuition does that), naming the consumer's ESOI solutions a request concerns (Relevant Solutions does that), and reading or editing the files (Read Files and File Editing do that).
- Delegates to: context-retriever, cards-from-files, the-intuition, relevant-solutions, read-files
- Entry call: `hubofhubs.run("folder-view", ...)`
- Selected implementation: Folders judged by evidence, files ranked by what the work points at (`evidence_ranked`)
- Metric: Needed files shown within the budget, nothing risky or useless read, what was left out said
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](../../../__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](../../../critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/__init__.py`](../../../critical_thinking/decision_check/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/agreement.py`](../../../critical_thinking/decision_check/agreement.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/checks.py`](../../../critical_thinking/decision_check/checks.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/interface.py`](../../../critical_thinking/decision_check/interface.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/mistakes.py`](../../../critical_thinking/decision_check/mistakes.py), [`hubofhubs/the_intelligence/critical_thinking/decision_check/remainder.py`](../../../critical_thinking/decision_check/remainder.py) and 255 more

### Top implementations of Folder View

| # | Implementation | Result | Cost per pass | In use |
|---|---|---|---|---|
| 1 | Folders judged by evidence, files ranked by what the work points at (`evidence_ranked`) | score 0.98 (39 of 41 cases) | free | selected |
| 2 | Evidence candidates, then one cheap model call (`model_pick`) | 97% (32 of 33 cases) | 0.5 calls |  |
| 3 | Names, whole folder, shared words (the harness as it was) (`ported_baseline`) | score 0.70 (7 of 41 cases) | free |  |

**How it is scored:** Needed files shown within the budget, nothing risky or useless read, what was left out said. The files a piece of work needs are among the first shown within a fixed budget, with little else; no file of a credentials, backup or private folder, and no dependency, build or cache file, is shown unasked; a file the goal names inside a risky folder comes back flagged and not shown; and the folders left out are listed.
Result is the share of the metric's cases an implementation passes (its balanced score when it has one); cost per pass is dollars per passing case.

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Names, whole folder, shared words (the harness as it was) | `folder-view:ported_baseline` | The selection the hub's work harness used before this solution: skip a fixed list of folder names, hidden folders and virtual environments; show the files the goal names, then the whole folder when it fits, then for a small folder a few files sharing words with the goal, and nothing unasked for a corpus of more than 200 files. | [`hubofhubs/the_intelligence/subconscious/local_file_context/folder_view/ported_baseline.py`](ported_baseline.py) |  |
| Folders judged by evidence, files ranked by what the work points at | `folder-view:evidence_ranked` | Judges each folder by a table of markers and rules (a project file beside it, a marker inside it, what its files are, the project's own .gitignore) and leaves out dependency, build, cache, generated and risky places with the reason; ranks the rest by rare goal words in the path, headings and opening, the work's own ids and quoted strings, links from a named file, the trail of earlier runs and the newest of a numbered series. | [`hubofhubs/the_intelligence/subconscious/local_file_context/folder_view/evidence_ranked.py`](evidence_ranked.py) | selected |
| Evidence candidates, then one cheap model call | `folder-view:model_pick` | Takes the evidence arm's wider candidate list (up to 30 files with size and first heading) and asks one fast-tier model call to name the files the work needs; the files the goal names and the flagged ones stay as they were. | [`hubofhubs/the_intelligence/subconscious/local_file_context/folder_view/model_pick.py`](model_pick.py) |  |

## Metrics

- Needed files shown within the budget, nothing risky or useless read, what was left out said (`metric-folder-view`): leader `evidence_ranked`, 39 of 41 cases

## Problems

- Work starts on noise or risky files (`hprob-work-starts-on-noise-or-risky-files`): A piece of work in a folder of thousands of files is shown files from dependency, build and cache folders or notes that share a word with the goal, and can be shown files that hold credentials, backups or other people's private data, while the file it needs is missed.

## Ideals

- The right files in view, nothing risky read (`hideal-the-right-files-in-view-nothing-risky-read`): A piece of work starts with the files it needs in view and nothing that is dependency, build output, cache or a secret.

## Where to go next

- Up: [hubofhubs/the_intelligence/subconscious/local_file_context](../README.md)
- Intent: [Finding and preparing information for the Mind](../../README.md)
- Repository: [top README](../../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
