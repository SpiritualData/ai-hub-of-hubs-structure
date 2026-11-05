# The best parts for AI intelligence, assembled and proven

AI builders have consistent interfaces for whatever the current best AI solutions are, to adapt only what is unique to their project.

*ESOI records of this intent (evolvable structure that optimizes intent), generated from the CSV files beside this page by `esoi readmes`. Edit the CSV files, not this page.*

Opportunities: Any product that needs an AI grounded in a person or team's own goals can start from the assembled whole instead of researching and gluing parts again; a production consumer is the hardest test of the assembly.

## How the solutions fit together

The AI Hub of Hubs gives anyone a working AI assembled from measured open-source parts, and The Self is the whole that keeps its five kinds of part working as one. To respond to a request, The Self asks Consciousness for the person's authority and preferences, asks Body where the system's data lives, and passes the request to Intelligence, which draws tools, models and outside knowledge from World. The Self then keeps the run record in Body, has Integrity audit it, and asks Consciousness to learn from the person's feedback. When asked for its health, The Self reports on itself, and for the research it asks World how current it is.

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

## Solutions at a glance

| Solution | Handle | Entry call | Selected implementation | Metric |
|---|---|---|---|---|
| World | `the-world` | `hubofhubs.run("the-world", 'latest Rust version')` | Search and papers through the tools (`composition`) | Task pass rate and cost per passing task |
| The Self | `the-self` | `hubofhubs.run("the-self", ...)` | Responds through every container (`composition`) | The assembled whole answers a real request, Integrated efficiency of the whole |
| Body | `the-body` | `hubofhubs.run("the-body", '')` | Declared sources and enduring integrations (`composition`) | A system applies the hub to itself |
| Intelligence | `the-intelligence` | `hubofhubs.run("the-intelligence", ...)` | One request through the long view, the target, the Mind and the checks (`composition`) | A request is answered from what bears on it |
| Consciousness | `the-consciousness` | `hubofhubs.run("the-consciousness", '')` | Representative, priorities and feedback (`composition`) | A representative asks when the person would want to be asked |

## Problems and ideals

**Problems**

- Parts re-glued by every team (`HP1`): Many teams research and wire up the same open-source AI parts on their own, and their private versions drift apart.
- Parts not compared on the job at hand (`HP2`): Lists of hubs say what exists, not which works best for a given job or how well parts work together.
- Wired to one hub (`HP4`): When a system is wired to one hub, that hub's outage, price change or shutdown can stop the system or raise its cost, and switching usually means changing code.
- Parts not judged by what they add to the whole (`HP5`): Each part is usually tuned and chosen on its own, so a part can be kept for how well it does alone even when the whole gains little from it or pays more for it.
- Form wired to one product (`hprob-system-form-wired-to-one-product`): AI systems are usually built around one product's data, so another system cannot give the hub its own APIs, databases and files without rewriting parts.
- Too much or too little context (`hprob-one-request-answered-from-too-much-or-too-little`): A request is often answered from whatever context is at hand (the recent chat, a fixed set of files), so the AI sees too much to use well or too little to answer.
- Every person treated alike (`hprob-ai-treats-every-person-alike`): Most AI assistants use the same rule for every person, so they ask a person who wanted them to go ahead and act without asking a person who wanted to be asked.

**Ideals**

- The best option for each case is in use (`HI1`): The implementations selected for solutions always reflect the best alternative available across all known resources and methods.
- One-step assembly (`HI2`): Anyone gets a working system from the best parts without writing glue code.
- Always current (`HI3`): What the hub recommends reflects the best parts available now.
- Swappable parts (`HI4`): When a better part appears or a part fails, the system keeps working with the better or the working one, and no caller changes.
- Every part earns its place in the whole (`HI5`): The assembled whole does real work well for its users, and every part in it adds more to the whole than it costs.
- Generic and thin (`HI6`): Any team can use the hub as it is, and can change any default without forking it.

## Metrics and their leaders

- Task pass rate and cost per passing task (`metric-the-world`)
- The assembled whole answers a real request (`metric-the-self`)
- A system applies the hub to itself (`metric-the-body`)
- A request is answered from what bears on it (`metric-the-intelligence`)
- A representative asks when the person would want to be asked (`metric-the-consciousness`)
- Integrated efficiency of the whole (`metric-integrated-efficiency`)

## Where to go next

- Sub-intent: [The form and internal context of a system](../hubofhubs/the_body/README.md) (The AI system fits the particular system it lives in.)
- Sub-intent: [Adapting to the humans the system works with](../hubofhubs/the_consciousness/README.md) (The AI representatives of a team learn each person's way: which authority they carry, when to ask that person and when not to, which priorities the person implies, and how that person wants the work done, from the person's own feedback.)
- Sub-intent: [How the AI processes information](../hubofhubs/the_intelligence/README.md) (AI requests are handled in the best way possible, given all relevant information.)
- Sub-intent: [The parts working as one whole](../hubofhubs/the_self/README.md) (The parts of the system work as one whole: each part knows its role, what the system claims matches its evidence, its records match its code, and one call builds the parts from configuration.)
- Sub-intent: [Awareness of the outside and interaction with it](../hubofhubs/the_world/README.md) (The AI knows what is outside the system and can interact with it: it brings in knowledge a reader can check, uses the right tool for each kind of need, asks a model through one measured path and keeps its own research current.)
- Repository: [top README](../README.md)
- Records beside the code: [hubofhubs](../hubofhubs/README.md)
- Records: [intent.csv](intent.csv)
- Diagram page: [diagram.md](diagram.md)

---

## The full record

### Problems

- Parts re-glued by every team (`HP1`): Many teams research and wire up the same open-source AI parts on their own, and their private versions drift apart.
- Parts not compared on the job at hand (`HP2`): Lists of hubs say what exists, not which works best for a given job or how well parts work together.
- Wired to one hub (`HP4`): When a system is wired to one hub, that hub's outage, price change or shutdown can stop the system or raise its cost, and switching usually means changing code.
- Parts not judged by what they add to the whole (`HP5`): Each part is usually tuned and chosen on its own, so a part can be kept for how well it does alone even when the whole gains little from it or pays more for it.
- Form wired to one product (`hprob-system-form-wired-to-one-product`): AI systems are usually built around one product's data, so another system cannot give the hub its own APIs, databases and files without rewriting parts.
- Too much or too little context (`hprob-one-request-answered-from-too-much-or-too-little`): A request is often answered from whatever context is at hand (the recent chat, a fixed set of files), so the AI sees too much to use well or too little to answer.
- Every person treated alike (`hprob-ai-treats-every-person-alike`): Most AI assistants use the same rule for every person, so they ask a person who wanted them to go ahead and act without asking a person who wanted to be asked.

### Ideals

- The best option for each case is in use (`HI1`): The implementations selected for solutions always reflect the best alternative available across all known resources and methods.
- One-step assembly (`HI2`): Anyone gets a working system from the best parts without writing glue code.
- Always current (`HI3`): What the hub recommends reflects the best parts available now.
- Swappable parts (`HI4`): When a better part appears or a part fails, the system keeps working with the better or the working one, and no caller changes.
- Every part earns its place in the whole (`HI5`): The assembled whole does real work well for its users, and every part in it adds more to the whole than it costs.
- Generic and thin (`HI6`): Any team can use the hub as it is, and can change any default without forking it.

### Solutions

| Solution | Handle | Selected | Metric |
|---|---|---|---|
| World | `the-world` | Search and papers through the tools (`composition`) | Task pass rate and cost per passing task |
| The Self | `the-self` | Responds through every container (`composition`) | The assembled whole answers a real request, Integrated efficiency of the whole |
| Body | `the-body` | Declared sources and enduring integrations (`composition`) | A system applies the hub to itself |
| Intelligence | `the-intelligence` | One request through the long view, the target, the Mind and the checks (`composition`) | A request is answered from what bears on it |
| Consciousness | `the-consciousness` | Representative, priorities and feedback (`composition`) | A representative asks when the person would want to be asked |

### Implementations

| Implementation | Handle | Where | Sub-intent |
|---|---|---|---|
| Hand-wired general agent framework | `the-self:hand_wired_agent_framework` |  |  |
| Responds through every container | `the-self:composition` | [hubofhubs/the_self/respond.py](../hubofhubs/the_self/respond.py) | [the_self](the_self/README.md) |
| Declared sources and enduring integrations | `the-body:composition` | [hubofhubs/the_body/flow.py](../hubofhubs/the_body/flow.py) | [the_body](the_body/README.md) |
| One request through the long view, the target, the Mind and the checks | `the-intelligence:composition` | [hubofhubs/the_intelligence/flow.py](../hubofhubs/the_intelligence/flow.py) | [the_intelligence](the_intelligence/README.md) |
| Representative, priorities and feedback | `the-consciousness:composition` | [hubofhubs/the_consciousness/flow.py](../hubofhubs/the_consciousness/flow.py) | [the_consciousness](the_consciousness/README.md) |
| Search and papers through the tools | `the-world:composition` | [hubofhubs/the_world/flow.py](../hubofhubs/the_world/flow.py) | [the_world](the_world/README.md) |

### Metrics

- Task pass rate and cost per passing task (`metric-the-world`): `none`
- The assembled whole answers a real request (`metric-the-self`): `none`
- A system applies the hub to itself (`metric-the-body`): `none`
- A request is answered from what bears on it (`metric-the-intelligence`): `none`
- A representative asks when the person would want to be asked (`metric-the-consciousness`): `none`
- Integrated efficiency of the whole (`metric-integrated-efficiency`): `none`
