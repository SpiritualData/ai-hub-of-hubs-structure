# Web Search

**Purpose:** Run one web search and return its hits with their sources.

Breadcrumb: [Top](../../../../esoi/README.md) > [Awareness of the outside and interaction with it](../../README.md) > [Using the tools of the outside world](../README.md) > Web Search

Part of [Using the tools of the outside world](../README.md)

## Web Search (`web-search`)

- Out of scope: Public research papers (Science does that) and reading a person's own data (Internal Context declares where it is and File Reading reads it).
- Delegates to: the-science
- Entry call: `hubofhubs.run("web-search", 'latest Rust version')`
- Selected implementation: Gemini grounding (`gemini`)
- Metric: Search finds the source
- Implemented by: [`hubofhubs/the_world/__init__.py`](../../__init__.py), [`hubofhubs/the_world/flow.py`](../../flow.py), [`hubofhubs/the_world/interface.py`](../../interface.py), [`hubofhubs/the_world/learning/__init__.py`](../../learning/__init__.py), [`hubofhubs/the_world/learning/interface.py`](../../learning/interface.py), [`hubofhubs/the_world/learning/investigation_record.py`](../../learning/investigation_record.py), [`hubofhubs/the_world/learning/investigation_store.py`](../../learning/investigation_store.py), [`hubofhubs/the_world/learning/registry_research.py`](../../learning/registry_research.py) and 188 more

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| Brave Search API | `web-search:brave` | Searches the Brave Search API through the generic JSON-API backend; the entry is data. | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |
| Claude Code login search | `web-search:claude_login` | Searches the web through the Claude Code login: one headless claude call allowed only the CLI's own web search tool, which returns titles, links, snippets and dates as JSON. | [`hubofhubs/the_world/tools/web_search/claude_login.py`](claude_login.py) |  |
| Gemini grounding | `web-search:gemini` | Searches through Gemini's Google Search grounding tool and resolves the redirect links to the real pages. | [`hubofhubs/the_world/tools/web_search/gemini.py`](gemini.py) | selected |
| Provider-native search | `web-search:provider` | Wraps any model provider object that exposes web_search(query, model, max_results). | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |
| SearXNG metasearch | `web-search:searxng` | Searches a self-hosted SearXNG instance by base url. | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |
| Serper Google search | `web-search:serper` | Searches the Serper API through the generic JSON-API backend; the entry is data. | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |
| Tavily search API | `web-search:tavily` | Searches the Tavily API through the generic JSON-API backend; the entry is data. | [`hubofhubs/the_world/tools/web_search/backends.py`](backends.py) |  |

## Metrics

- Search finds the source (`metric-web-search`): leader `gemini`, 32 of 40 cases

## Where to go next

- Up: [hubofhubs](../../../README.md)
- Intent: [Using the tools of the outside world](../README.md)
- Repository: [top README](../../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
