# hubofhubs

*ESOI records kept beside the code in `hubofhubs`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

Anyone building AI intelligence can assemble a working system from the best open-source parts available, chosen by measurement and kept current every week, without writing the glue themselves.

These are the solutions of [The best parts for AI intelligence, assembled and proven](../esoi/README.md).

## How the solutions fit together

hub-of-hubs gives anyone a working AI assembled from measured open-source parts, and The Self is the whole that keeps its five kinds of part working as one. To respond to a request, The Self asks for the person's authority and preferences from Consciousness, asks where the system's data lives from Body, passes the request on for processing to Intelligence, and asks World how current the research is. The Self then keeps the run record in Body and asks Consciousness to learn from the person's feedback.

## Overview diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["World<br/><i>the-world</i>"]
    s1["The Self<br/><i>the-self</i>"]
    s2["Body<br/><i>the-body</i>"]
    s3["Intelligence<br/><i>the-intelligence</i>"]
    s4["Consciousness<br/><i>the-consciousness</i>"]
    s0 -->|"Material from outside the system, with its sources, and the result of using an outside tool"| s1
    s2 -->|"What a particular system declares about its own data and integrations"| s1
    s3 -->|"A response to one request, with the step of every part that took part"| s1
    s4 -->|"The person's Representative, and what the system learned from that person"| s1
```

## World (`the-world`)

Bring in what is outside the system and let the AI act on it through the best available tool.

- Entry call: `hubofhubs.run("the-world", 'latest Rust version')`
- Selected implementation: Search and papers through the tools (`composition`)
- Metric: Task pass rate and cost per passing task
- Implemented by: [`hubofhubs/the_world/__init__.py`](the_world/__init__.py), [`hubofhubs/the_world/flow.py`](the_world/flow.py), [`hubofhubs/the_world/interface.py`](the_world/interface.py), [`hubofhubs/the_world/learning/__init__.py`](the_world/learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](the_world/learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](the_world/learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](the_world/learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](the_world/learning/research_freshness_reader/interface.py) and 120 more

## The Self (`the-self`)

Keep every part working as one whole for one request.

- Entry call: `hubofhubs.run("the-self", ...)`
- Selected implementation: Responds through every container (`composition`)
- Metric: The assembled whole answers a real request, Integrated efficiency of the whole, Integrated efficiency of the whole
- Implemented by: [`hubofhubs/the_self/__init__.py`](the_self/__init__.py), [`hubofhubs/the_self/assembler/__init__.py`](the_self/assembler/__init__.py), [`hubofhubs/the_self/assembler/arm_needs.py`](the_self/assembler/arm_needs.py), [`hubofhubs/the_self/assembler/cli.py`](the_self/assembler/cli.py), [`hubofhubs/the_self/assembler/interface.py`](the_self/assembler/interface.py), [`hubofhubs/the_self/assembler/oneline.py`](the_self/assembler/oneline.py), [`hubofhubs/the_self/assembler/resolution.py`](the_self/assembler/resolution.py), [`hubofhubs/the_self/assembler/zero_config.py`](the_self/assembler/zero_config.py) and 21 more

## Body (`the-body`)

Let the hub apply to one particular system by declaring where its data lives, where its requests come from and which of its integrations the AI may use, and keep the run record, the configuration, the environment variables, the secrets and the stored authentication the tools need.

- Entry call: `hubofhubs.run("the-body", '')`
- Selected implementation: Declared sources and enduring integrations (`composition`)
- Metric: A system applies the hub to itself
- Implemented by: [`hubofhubs/the_body/__init__.py`](the_body/__init__.py), [`hubofhubs/the_body/filemodes.py`](the_body/filemodes.py), [`hubofhubs/the_body/flow.py`](the_body/flow.py), [`hubofhubs/the_body/hands/__init__.py`](the_body/hands/__init__.py), [`hubofhubs/the_body/hands/interface.py`](the_body/hands/interface.py), [`hubofhubs/the_body/intake_sources/__init__.py`](the_body/intake_sources/__init__.py), [`hubofhubs/the_body/intake_sources/interface.py`](the_body/intake_sources/interface.py), [`hubofhubs/the_body/intake_sources/queue.py`](the_body/intake_sources/queue.py) and 62 more

## Intelligence (`the-intelligence`)

Turn one request and what is known into a response that meets its goal.

- Entry call: `hubofhubs.run("the-intelligence", ...)`
- Selected implementation: One request through the long view, the target, the Mind and the checks (`composition`)
- Metric: A request is answered from what bears on it
- Implemented by: [`hubofhubs/the_intelligence/__init__.py`](the_intelligence/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/__init__.py`](the_intelligence/critical_thinking/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/__init__.py`](the_intelligence/critical_thinking/esoi_application/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/esoi_application/interface.py`](the_intelligence/critical_thinking/esoi_application/interface.py), [`hubofhubs/the_intelligence/critical_thinking/flow.py`](the_intelligence/critical_thinking/flow.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/__init__.py`](the_intelligence/critical_thinking/goal_completion/__init__.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/done_evidence.py`](the_intelligence/critical_thinking/goal_completion/done_evidence.py), [`hubofhubs/the_intelligence/critical_thinking/goal_completion/goal_completion.py`](the_intelligence/critical_thinking/goal_completion/goal_completion.py) and 136 more

## Consciousness (`the-consciousness`)

Keep the system aligned with the humans and policies it works for.

- Entry call: `hubofhubs.run("the-consciousness", '')`
- Selected implementation: Representative, priorities and feedback (`composition`)
- Metric: A representative asks when the person would want to be asked
- Implemented by: [`docs/reference/work-trace-event.schema.json`](../docs/reference/work-trace-event.schema.json), [`hubofhubs/the_consciousness/__init__.py`](the_consciousness/__init__.py), [`hubofhubs/the_consciousness/feedback_learning/__init__.py`](the_consciousness/feedback_learning/__init__.py), [`hubofhubs/the_consciousness/feedback_learning/interface.py`](the_consciousness/feedback_learning/interface.py), [`hubofhubs/the_consciousness/flow.py`](the_consciousness/flow.py), [`hubofhubs/the_consciousness/interface.py`](the_consciousness/interface.py), [`hubofhubs/the_consciousness/judgment_calls/__init__.py`](the_consciousness/judgment_calls/__init__.py), [`hubofhubs/the_consciousness/judgment_calls/interface.py`](the_consciousness/judgment_calls/interface.py) and 24 more

## Diagram

An arrow runs from the solution that provides to the solution that builds on it; its label is what the provider outputs.

```mermaid
flowchart LR
    s0["World<br/><i>the-world</i>"]
    s1["The Self<br/><i>the-self</i>"]
    s2["Body<br/><i>the-body</i>"]
    s3["Intelligence<br/><i>the-intelligence</i>"]
    s4["Consciousness<br/><i>the-consciousness</i>"]
    s0 -->|"Material from outside the system, with its sources, and the result of using an outside tool"| s1
    s2 -->|"What a particular system declares about its own data and integrations"| s1
    s3 -->|"A response to one request, with the step of every part that took part"| s1
    s4 -->|"The person's Representative, and what the system learned from that person"| s1
```

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Hand-wired general agent framework | `the-self:hand_wired_agent_framework` | no code yet |  |
| Responds through every container | `the-self:composition` | [`hubofhubs/the_self/respond.py`](the_self/respond.py) | selected |
| Declared sources and enduring integrations | `the-body:composition` | [`hubofhubs/the_body/flow.py`](the_body/flow.py) | selected |
| One request through the long view, the target, the Mind and the checks | `the-intelligence:composition` | [`hubofhubs/the_intelligence/flow.py`](the_intelligence/flow.py) | selected |
| Representative, priorities and feedback | `the-consciousness:composition` | [`hubofhubs/the_consciousness/flow.py`](the_consciousness/flow.py) | selected |
| The parts of the system | `the-self:parts` | no code yet |  |
| Search and papers through the tools | `the-world:composition` | [`hubofhubs/the_world/flow.py`](the_world/flow.py) | selected |

## Metrics

- Task pass rate and cost per passing task (`metric-the-world`)
- The assembled whole answers a real request (`metric-the-self`)
- A system applies the hub to itself (`metric-the-body`)
- A request is answered from what bears on it (`metric-the-intelligence`)
- A representative asks when the person would want to be asked (`metric-the-consciousness`)
- Integrated efficiency of the whole (`metric-integrated-efficiency`)

## Problems

- Parts re-glued by every team (`HP1`): Every team re-researches and re-glues the same AI parts, and the private copies drift apart.
- No evaluation of the parts (`HP2`): Lists of hubs say what exists, not which works best or fits together.
- One hub outage stops the system (`HP4`): One hub's outage, price change or shutdown stops the system, and switching needs code changes.
- The whole is never tested (`HP5`): Parts that are best alone can fail when assembled, and nobody tests the whole.
- Form wired to one product (`hprob-system-form-wired-to-one-product`): The form and internal context of an AI system are wired for one product, so another system cannot give the hub its own APIs, databases and files without rewriting the parts.
- Too much or too little context (`hprob-one-request-answered-from-too-much-or-too-little`): A request is answered from whatever happened to be nearby, so the AI sees too much to use or too little to answer.
- Every person treated alike (`hprob-ai-treats-every-person-alike`): An AI treats every person alike, so it asks the person who wanted it to proceed and acts without asking the person who wanted to be asked.

## Ideals

- Best by measurement (`HI1`): Each seat holds the part that measures best on shared cases.
- One-step assembly (`HI2`): Configuration in, working system out, no glue code.
- Always current (`HI3`): No area goes a week without a fresh search and comparison.
- Swappable parts (`HI4`): Any part can be replaced by configuration when another measures better or fails.
- Proven whole (`HI5`): The assembled system is tested end to end on a production consumer, not only part by part.
- Generic and thin (`HI6`): No consumer-specific content.

## Where to go next

- Intent: [The best parts for AI intelligence, assembled and proven](../esoi/README.md)
- Down: [hubofhubs/the_body/intake_sources](the_body/intake_sources/README.md)
- Down: [hubofhubs/the_body/internal_context](the_body/internal_context/README.md)
- Down: [hubofhubs/the_consciousness/judgment_calls](the_consciousness/judgment_calls/README.md)
- Down: [hubofhubs/the_consciousness/representatives](the_consciousness/representatives/README.md)
- Down: [hubofhubs/the_consciousness/request_intake](the_consciousness/request_intake/README.md)
- Down: [hubofhubs/the_intelligence/nervous_system](the_intelligence/nervous_system/README.md)
- Down: [hubofhubs/the_intelligence/proactivity](the_intelligence/proactivity/README.md)
- Down: [hubofhubs/the_self/assembler](the_self/assembler/README.md)
- Down: [hubofhubs/the_self/integrity](the_self/integrity/README.md)
- Down: [hubofhubs/the_world/learning](the_world/learning/README.md)
- Down: [hubofhubs/the_world/science](the_world/science/README.md)
- Down: [hubofhubs/the_intelligence/critical_thinking/goal_completion](the_intelligence/critical_thinking/goal_completion/README.md)
- Down: [hubofhubs/the_intelligence/critical_thinking/metric_translation](the_intelligence/critical_thinking/metric_translation/README.md)
- Down: [hubofhubs/the_intelligence/critical_thinking/response_quality](the_intelligence/critical_thinking/response_quality/README.md)
- Down: [hubofhubs/the_intelligence/mind/context_intake](the_intelligence/mind/context_intake/README.md)
- Down: [hubofhubs/the_intelligence/mind/delegation](the_intelligence/mind/delegation/README.md)
- Down: [hubofhubs/the_intelligence/mind/planner](the_intelligence/mind/planner/README.md)
- Down: [hubofhubs/the_intelligence/mind/response_writer](the_intelligence/mind/response_writer/README.md)
- Down: [hubofhubs/the_intelligence/subconscious/cards_from_files](the_intelligence/subconscious/cards_from_files/README.md)
- Down: [hubofhubs/the_intelligence/subconscious/context_retriever](the_intelligence/subconscious/context_retriever/README.md)
- Down: [hubofhubs/the_world/model_plumbing/model_tier_chooser](the_world/model_plumbing/model_tier_chooser/README.md)
- Down: [hubofhubs/the_world/model_plumbing/vendor_model_caller](the_world/model_plumbing/vendor_model_caller/README.md)
- Down: [hubofhubs/the_world/tools/connected_system_operations](the_world/tools/connected_system_operations/README.md)
- Down: [hubofhubs/the_world/tools/delegated_agent_sessions](the_world/tools/delegated_agent_sessions/README.md)
- Down: [hubofhubs/the_world/tools/file_editing](the_world/tools/file_editing/README.md)
- Down: [hubofhubs/the_world/tools/file_reading](the_world/tools/file_reading/README.md)
- Down: [hubofhubs/the_world/tools/web_search](the_world/tools/web_search/README.md)
- Repository: [top README](../README.md)
