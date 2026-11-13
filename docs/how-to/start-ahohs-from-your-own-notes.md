# Start `ahohs work` from your own notes

By default `ahohs work` gives the harness only your goal. If you keep saved notes about a focus of your own (a hobby, a practice, a project), a short file tells `ahohs` where they are, and every run then starts from them: the harness is told what is already known about the focus, helpers get the notes that bear on their task, and you read one line on screen, for example `Using 4 saved notes about garden`. Files are searched only for what the notes do not say.

No file, no change: without the file below, a session runs exactly as before.

## 1. Write the file

`ahohs` reads the first of: `--context FILE`, the `AHOHS_CONTEXT` variable, `~/.config/ahohs/context.toml`. Keep it outside any repository.

```toml
[context]
focus = "garden"            # the named focus: notes at home in it (tag focus:garden) come first
max_notes = 5               # most notes in the brief (default 5)
budget_tokens = 1500        # token budget of the notes (default 1500)
scope = ["team:household"]  # optional hard fence: a note tagged for another scope is never shown

[[context.sources]]
kind = "cards"              # a folder of saved cards, one JSON file each
path = "~/notes/cards"

[[context.sources]]
kind = "folder"             # a folder of .md or .txt files, each file one note
path = "~/notes/garden"
focus = "garden"            # notes with no home of their own are at home in this focus

[[context.sources]]
kind = "command"            # a program that prints a JSON list of notes; told the focus in AHOHS_FOCUS
command = ["python3", "~/bin/garden_notes.py"]
timeout = 60
```

A note is a mapping with `id`, `title` (or `name`), `text` (or `summary`, `description`, `content`), and optionally `affinity_tags` (`["focus:garden"]`), `scope_tags`, `overview` (true for a short statement of what the focus is; always offered) and `timestamp`.

## 2. Run

```bash
ahohs work "what do my notes say about tomatoes?"
ahohs work --focus cooking "..."          # name another focus for this run
ahohs work --context ./other.toml "..."
```

## How the notes are chosen

The Context Retriever's `focus_first` arm ranks notes at home in the focus first (soft affinity, ranking only); a note from another home appears only when it matches the request about as well as the best note; a note outside `scope` is never shown. A request about something else gets nothing added. The metric is `metric-focus-context` (`evaluation/focus_context`).

## A consumer that keeps its context elsewhere

Pass a function from a focus to notes: `work_command(args, hub, context_provider=provider)` in `hubofhubs.the_self.assembler.cli`, or `hubofhubs.api.grounded_builder(build, settings, provider)` around a harness builder. The consumer maps its own data model onto the focus tag; the hub knows nothing about it.
