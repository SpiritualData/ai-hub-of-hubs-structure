# Holding a request to a measure

A request becomes a metric with a target and a budget, adjustable while the work runs, and the result is held to it: was the goal met, and is the response good for this person.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

This sub-intent arises as the implementation `critical-thinking:composition` of its parent intent [`the_intelligence`](../README.md). Opportunities: Translating a request into a metric, creating and editing the specs and metrics, judging goal completion and judging response quality are four ML tasks, each improvable on its own accuracy.

## How the solutions fit together

Critical Thinking holds a request to a measure. Metric Translation turns the request into a metric with a target value or improvement and a budget, adjustable while the work runs. ESOI Application records that metric as a spec and applies the principles, creating and editing specs and metrics. Goal Completion says whether the goal's condition was met against its done-standard. Response Quality judges the response against the quality profile resolved for the request.

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| ESOI Application | `esoi-application` | `hubofhubs.run("esoi-application", {'change': {}})` | none selected | Specs and metrics improve by the loop |
| Goal Completion | `goal-completion` | `hubofhubs.run("goal-completion", ...)` | Evidence standard (`evidence_standard`) | Goals judged met only when they are |
| Metric Translation | `metric-translation` | `hubofhubs.run("metric-translation", {'request': 'what is the latest Rust release?'})` | Goal record with default budget (`goal_record`) | A goal record with a target and a budget |
| Response Quality | `response-quality` | `hubofhubs.run("response-quality", ...)` | Links held to their evidence (`evidence_check`) | Balanced score of a response against its quality profile |

## Problems and ideals

**Problems**

- Goal not turned into a metric (`hprob-goal-not-turned-into-a-metric`): A request is answered without a target, so no one can say whether its goal was met or how much better a second try was.
- One quality standard for everyone (`hprob-one-quality-standard-for-everyone`): Response quality is judged by one fixed standard, though what counts as high quality depends on the person, the situation and the goals above the request.

**Ideals**

- Every request has a target (`hideal-every-request-has-a-target`): Every request and sub-goal has a metric with a target value or an improvement, which rolls up to the objective it serves.
- Quality is judged per profile (`hideal-quality-is-per-profile`): A response is judged against the quality profile of the person and situation, with a researched default when none is given.

## Metrics and their leaders

- Specs and metrics improve by the loop (`metric-esoi-application`)
- Goals judged met only when they are (`metric-goal-completion`): leader `evidence_standard`, 14 of 14 cases
- A goal record with a target and a budget (`metric-metric-translation`)
- Balanced score of a response against its quality profile (`metric-response-quality`)

## Where to go next

- Parent intent: [Processing information for one request](../README.md)
- Repository: [top README](../../../README.md)
- Records beside the code: [hubofhubs/the_intelligence/critical_thinking/goal_completion](goal_completion/README.md), [hubofhubs/the_intelligence/critical_thinking/metric_translation](metric_translation/README.md), [hubofhubs/the_intelligence/critical_thinking/response_quality](response_quality/README.md)
- Records: [intent.csv](intent.csv), [problems.csv](problems.csv), [ideals.csv](ideals.csv), [solutions.csv](solutions.csv), [metrics.csv](metrics.csv)

---

## The full record

### Problems

- Goal not turned into a metric (`hprob-goal-not-turned-into-a-metric`): A request is answered without a target, so no one can say whether its goal was met or how much better a second try was.
- One quality standard for everyone (`hprob-one-quality-standard-for-everyone`): Response quality is judged by one fixed standard, though what counts as high quality depends on the person, the situation and the goals above the request.

### Ideals

- Every request has a target (`hideal-every-request-has-a-target`): Every request and sub-goal has a metric with a target value or an improvement, which rolls up to the objective it serves.
- Quality is judged per profile (`hideal-quality-is-per-profile`): A response is judged against the quality profile of the person and situation, with a researched default when none is given.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| ESOI Application | `esoi-application` | none selected | Specs and metrics improve by the loop |
| Goal Completion | `goal-completion` | Evidence standard (`evidence_standard`) | Goals judged met only when they are |
| Metric Translation | `metric-translation` | Goal record with default budget (`goal_record`) | A goal record with a target and a budget |
| Response Quality | `response-quality` | Links held to their evidence (`evidence_check`) | Balanced score of a response against its quality profile |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Evidence standard | `goal-completion:evidence_standard` | [hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py](goal_completion/goal_completion.py) |  |
| Outcome is not empty | `goal-completion:nonempty` | [hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py](goal_completion/goal_completion.py) |  |
| Goal record with default budget | `metric-translation:goal_record` | [hubofhubs/the_intelligence/critical_thinking/metric_translation/translation.py](metric_translation/translation.py) |  |
| Links held to their evidence | `response-quality:evidence_check` | [hubofhubs/the_intelligence/critical_thinking/response_quality/evidence_check.py](response_quality/evidence_check.py) |  |

### Metrics

- Specs and metrics improve by the loop (`metric-esoi-application`): `none`
- Goals judged met only when they are (`metric-goal-completion`): `esoi run goal_completion --impl evidence_standard; esoi run goal_completion --impl nonempty`
- A goal record with a target and a budget (`metric-metric-translation`): `python3 -m pytest tests/test_orchestrate_parts.py`
- Balanced score of a response against its quality profile (`metric-response-quality`): `none`
