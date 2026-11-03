# Compared with other projects

The one idea: each component of an LLM application (model calls, search, retrieval, memory, coding agents, guardrails) is an interface
with several implementations. The default for each is chosen by a recorded paired eval on shared cases, and a lockfile pins it.

| Project | What it is | How hubofhubs differs |
|---|---|---|
| LangChain | A framework of chains, agents and integrations for LLM applications. | It offers components to compose; hubofhubs picks each component's default by a recorded eval. |
| LlamaIndex | A framework for retrieval and data connectors over your documents. | Its retrievers are candidates for the retrieval area, scored on the same cases as the rest. |
| Haystack | A pipeline framework for search and question answering. | A pipeline is wired by you; here each part's default comes from a recorded result. |
| DSPy | A framework that compiles prompts and programs against a metric. | It optimizes one program's prompts; hubofhubs compares implementations of each component. |
| LiteLLM | A library and proxy that calls many model providers through one interface. | A provider layer is one candidate for the model-call area, with failover measured. |
| OpenRouter | A hosted service that routes requests to many models. | A routing service is a candidate; the default tier and model are chosen by recorded evals. |
| MLflow model registry | A registry that versions and stages trained models. | It tracks model versions; hubofhubs tracks which implementation of each component is the default, and why. |
| promptfoo | A tool for running evals and red-team tests on prompts and models. | An eval tool; hubofhubs records paired results per component and promotes the default from them. |
| Inspect | A framework from the UK AI Security Institute for writing and running model evals. | An eval framework; hubofhubs uses recorded cases and results to choose component defaults. |
| lm-evaluation-harness | A harness that runs language models on standard benchmarks. | It scores models; hubofhubs scores components such as search and retrieval as well. |
| MTEB | A benchmark and leaderboard for text embedding models. | Embedding results are public evidence shown beside the hub's own numbers, never added to them. |
| LMArena | A public leaderboard of models ranked by human votes. | A general ranking; the hub ranks on its own cases for its own tasks. |
| Artificial Analysis | A site that benchmarks models and providers on quality, speed and price. | Its figures are public evidence; defaults here use cases and costs recorded in this repository. |
| mem0 | A memory layer that stores and retrieves facts for an LLM application. | A memory product is a candidate for the memory area, scored on the same cases. |
| Letta | An agent framework with persistent, self-editing memory (formerly MemGPT). | A candidate for the memory area. |
| Zep | A memory service that builds a temporal knowledge graph from conversations. | A candidate for the memory area. |
| Graphiti | An open-source library for building temporal knowledge graphs, used by Zep. | A candidate for the memory area. |
| MCP Registry | A catalog of Model Context Protocol servers. | A catalog the hub reads when it researches tools; it does not choose among them. |

Terms: [glossary](glossary.md). How results are measured: [how we measure](how-we-measure.md).
