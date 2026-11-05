# Web Search

*ESOI records kept beside the code in `hubofhubs/the_world/tools/web_search`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

The AI uses the tool of each category the person's authority allows, and a category gains a better integration without any product rewriting its code.

These are the solutions of [Using the tools of the outside world](../README.md).

## How the solutions fit together

Tools lets the AI use the tool of a category and refuses a category the authority does not allow. Web Search brings in the live web. File Reading reads the files of a folder. File Editing changes one file by instruction. Connected System Operations calls a write operation of a connected system. Delegated Agent Sessions gives open-ended work to an agent that runs in its own session.

## Web Search (`web-search`)

Run one web search and return its hits with their sources.

- Entry call: `hubofhubs.run("web-search", 'latest Rust version')`
- Selected implementation: Gemini grounding (`gemini`)
- Metric: Search finds the source
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py), [`hubofhubs/the_world/learning/research_freshness_reader/__init__.py`](../../learning/research_freshness_reader/__init__.py), [`hubofhubs/the_world/learning/research_freshness_reader/interface.py`](../../learning/research_freshness_reader/interface.py) and 122 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Brave Search API | `web-search:brave` | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |
| Gemini grounding | `web-search:gemini` | [`hubofhubs/the_world/tools/web_search/gemini.py`](gemini.py) | selected |
| Provider-native search | `web-search:provider` | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |
| SearXNG metasearch | `web-search:searxng` | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |
| Serper Google search | `web-search:serper` | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |
| Tavily search API | `web-search:tavily` | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |

## Metrics

- Search finds the source (`metric-web-search`): leader `gemini`, 32 of 40 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)
