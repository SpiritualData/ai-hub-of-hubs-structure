# Web search

*ESOI records kept beside the code in `hubofhubs/websearch`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

## Web search (`search-backend`)

Run a web search through any service, for any consumer that needs sources.

- Entry call: `hubofhubs.run("search-backend", 'latest Rust release')`
- Selected implementation: `gemini`
- Metric: Search finds the source
- Implemented by: [`hubofhubs/websearch/__init__.py`](__init__.py), [`hubofhubs/websearch/apis.py`](apis.py), [`hubofhubs/websearch/backends.py`](backends.py), [`hubofhubs/websearch/cache.py`](cache.py), [`hubofhubs/websearch/fetch.py`](fetch.py), [`hubofhubs/websearch/gemini.py`](gemini.py), [`hubofhubs/websearch/limiter.py`](limiter.py), [`hubofhubs/websearch/link_access.py`](link_access.py) and 14 more

## Implementations

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Brave Search API | `search-backend:brave` | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| Gemini grounding | `search-backend:gemini` | [`hubofhubs/websearch/gemini.py`](gemini.py) | selected |
| Provider-native search | `search-backend:provider` | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| SearXNG metasearch | `search-backend:searxng` | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| Serper Google search | `search-backend:serper` | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| Tavily search API | `search-backend:tavily` | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| Web research | `know-the-world:web_research` | [`hubofhubs/websearch/research.py`](research.py) |  |

## Metrics

- Search finds the source (`metric-search-backend`): leader `gemini`, 32 of 40 cases

## Where to go next

- Up: [hubofhubs](../README.md)
- Intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
