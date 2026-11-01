# Emit a work trace

Show the person the work a solution did, as it happens, without leaking what it read.

1. Build a `WorkTrace` once per run with the run's emitter: `WorkTrace(emit, trace_id=run_id, viewer_may_see_titles=owner_is_viewing)`. `emit` receives a `ProgressEvent` of type `EVENT_WORK_TRACE` (`hubofhubs.ports.events`).
2. From the structural result of a call (counts, domains, titles; never the model's wording), call `trace.update(step_id, solution_id=..., kind=..., label_key=..., state=..., counts=..., items=...)`. Use the same `step_id` for every update of one unit of work: the latest replaces the earlier ones.
3. Send `state="done"` or `"failed"` when the work ends. Running updates are coalesced to about four a second; the final one always goes out.
4. At the end of the run, `trace.summary()` returns the finished steps to store with the reply.

The projector keeps only allowlisted fields. It never lets through a query, content, a snippet, reasoning, tool arguments, a path or a full URL (a domain only). With `viewer_may_see_titles=False`, `records` are counts only. The wire shape is `docs/reference/work-trace-event.schema.json`; `hubofhubs.ports.trace.validate` checks a dict against it.

A `label_key` is an i18n key such as `workTrace.web.reading`. The consumer translates it; an unknown key falls back to a generic label for the `kind`.
