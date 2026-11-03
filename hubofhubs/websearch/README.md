# search-backend: run one web search

*ESOI records kept beside the code in `hubofhubs/websearch`, generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*

## search-backend: run one web search (`search-backend`)

Run a web search through any service, for any consumer that needs sources.

- Entry call: `hubofhubs.run("search-backend", 'latest Rust release')`
- Selected implementation: `gemini`
- Metric: Search finds the source
- Implemented by: [`hubofhubs/websearch/__init__.py`](__init__.py), [`hubofhubs/websearch/apis.py`](apis.py), [`hubofhubs/websearch/backends.py`](backends.py), [`hubofhubs/websearch/cache.py`](cache.py), [`hubofhubs/websearch/fetch.py`](fetch.py), [`hubofhubs/websearch/gemini.py`](gemini.py), [`hubofhubs/websearch/limiter.py`](limiter.py), [`hubofhubs/websearch/link_access.py`](link_access.py) and 14 more

## Implementations

| Implementation | Name | Code | Selected |
|---|---|---|---|
| `search-backend:brave` | Brave Search API | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| `search-backend:gemini` | Gemini grounding | [`hubofhubs/websearch/gemini.py`](gemini.py) | selected |
| `search-backend:provider` | Provider-native search | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| `search-backend:searxng` | SearXNG | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| `search-backend:serper` | Serper | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| `search-backend:tavily` | Tavily | [`hubofhubs/websearch/backends.py`](backends.py) |  |
| `know-the-world:web_research` | Web research | [`hubofhubs/websearch/research.py`](research.py) |  |

## Metrics

- `metric-search-backend`, Search finds the source: leader `gemini`, 32 of 40 cases

## Where to go next

- Up: [hubofhubs](../README.md)
- Intent: [The best parts for AI intelligence, assembled and proven](../../esoi/README.md)
- Repository: [top README](../../README.md)
