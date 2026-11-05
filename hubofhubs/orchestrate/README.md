# Arms in orchestrate

*ESOI arms kept in `hubofhubs/orchestrate`, generated from the records of the intents that own them by `esoi readmes`. Edit those records, not this page.*

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Merge into one labelled view | `context-intake:one_view` | [`hubofhubs/orchestrate/intake.py`](intake.py) | selected |
| Goal record with default budget | `metric-translation:goal_record` | [`hubofhubs/orchestrate/translation.py`](translation.py) | selected |
| Split and route by cues | `request-planner:cue_router` | [`hubofhubs/orchestrate/planning.py`](planning.py) | selected |
| One piece, no worker | `request-planner:one_piece` | [`hubofhubs/orchestrate/planning.py`](planning.py) |  |
| Cited results | `response-writer:cited_results` | [`hubofhubs/orchestrate/writer.py`](writer.py) | selected |
| Model synthesis | `response-writer:model_synthesis` | [`hubofhubs/orchestrate/writer.py`](writer.py) |  |
| Route to Tools and Science | `work-delegation:to_tools` | [`hubofhubs/orchestrate/delegation.py`](delegation.py) | selected |

## Where to go next

- Owning intent: [Processing information for one request](../the_intelligence/README.md)
- Repository: [top README](../../README.md)
