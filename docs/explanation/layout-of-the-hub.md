# Where each part of the hub lives

The top of `hubofhubs/` shows five folders and the registry. Everything else sits beneath the solution it implements, next to the
records that describe it.

```
hubofhubs/
  the_self/            The Self: the parts working as one whole
  the_body/            Body: the system's form and internal context
  the_intelligence/    Intelligence: processing information
  the_world/           World: the outside and interaction with it
  the_consciousness/   Consciousness: adapting to the humans
  registry/            the registry data (CSV with dated sources), read by the Learning code
  __init__.py          the package entry (run, assemble, Binding)
```

## The rule

A container folder holds one folder for each of its second-level solutions. A solution's folder holds its records
(`solutions.csv`, `implementations.csv`, `metrics.csv`, and `problems.csv` and `ideals.csv` where it has its own), the generated
`README.md`, its `interface.py` (the Protocol the solution declares), and the code of its arms, beside the records that name them in
`filepath`. A solution with parts of its own has a folder for each part, and when those parts need their own paragraph and diagram
the solution's folder is a sub-intent with an `intent.csv`.

- Four of Intelligence's solutions are sub-intents: `mind/`, `higher_mind/`, `subconscious/`, `critical_thinking/`. Two of World's
  are: `tools/` and `model_plumbing/`.
- Each container has a `flow.py` that holds the composition arm of the container (the order in which it calls its parts). A
  sub-intent has its own `flow.py` (`mind/flow.py`, `higher_mind/flow.py`, `critical_thinking/flow.py`, `tools/flow.py`).
- The cross-container flow lives in `the_self/respond.py`; the step plumbing every flow uses (`take`, `Step`) is
  `the_self/steps.py`; the assembly (resolution, needs, the one-line `run`) is `the_self/assembler/`.
- Helper code that belongs to no arm of its own sits in the lowest folder that all its users share, with a plain name:
  `the_world/tools/deep.py` (what a goal run returns, used by file editing, operations and agent sessions),
  `the_body/internal_context/run_store/` (run records), `the_intelligence/subconscious/context_retriever/assemblers/` and
  `context_cards/`, `the_intelligence/mind/delegation/overseer/`.

## Where things went

| Was | Is |
|---|---|
| `seats.py` | one `interface.py` per solution, beside its code |
| `flows.py`, `whole.py`, `areas.py` | `flow.py` of each container or sub-intent, `the_self/respond.py`, `the_self/assembler/zero_config.py`, `the_world/learning/registry_research.py`, `the_self/integrity/audit.py` |
| `act/` (retired word) | `the_world/tools/file_editing`, `connected_system_operations`, `file_reading` |
| `deep/` | `the_world/tools/delegated_agent_sessions` |
| `websearch/`, `science/` | `the_world/tools/web_search`, `the_world/science` |
| `models/`, `tiers.py` | `the_world/model_plumbing/vendor_model_caller`, `model_tier_chooser`, `via_vendor.py` |
| `recall/` | `the_body/internal_context/card_store` (the store and its upkeep), `the_intelligence/subconscious/local_file_context/cards_from_files`, `context_retriever/context_cards`, `context_retriever/assemblers` |
| `retrieval/` | `the_intelligence/subconscious/context_retriever` |
| `orchestrate/` | `the_intelligence/mind/{context_intake,planner,delegation,response_writer}`, `critical_thinking/metric_translation` |
| `critique/` | `the_intelligence/critical_thinking/{goal_completion,response_quality}` |
| `consciousness/`, `terminal/`, `quality.py` | `the_consciousness/{representatives,judgment_calls,request_intake,ai_session_experience}` (the terminal is `ai_session_experience/terminal_experience`) |
| `intake/` | `the_body/intake_sources` |
| `proactivity/`, `risk.py`, `consent_gate.py`, `signals.py` | `the_intelligence/proactivity`, `the_intelligence/nervous_system` (the overseer is a helper of Delegation) |
| `ports/` | beside the solution each Protocol serves (`the_world/tools/deep.py`, `the_world/model_plumbing/model.py`, `the_body/internal_context/context.py`, `the_consciousness/ai_session_experience/terminal_experience/trace.py`, ...) |
| `evidence_summary.py`, `measure.py`, `doctrine.py` and the generators | `the_self/integrity` |

## Why it is shaped this way

Records beside code (`esoi records place --apply`) put each record in the folder of the code its row names, so moving code moves its
specification with it. The sub-intent mechanism of `esoi.toml` (`[records] beside_code`, `arm_folders`) lists the nested folders.
A reader who opens a solution's folder finds what it is for, how it is measured and what runs it, in one place.
