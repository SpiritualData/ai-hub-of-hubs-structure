# science

Breadcrumb: [Top](../../../esoi/README.md) > [Awareness of the outside and interaction with it](../README.md) > science

Part of [Awareness of the outside and interaction with it](../README.md)

## Implementations

| Implementation | Handle | Purpose | Code | Selected |
|---|---|---|---|---|
| OpenAlex keyword search | `the-science:openalex` | Searches scholarly works in OpenAlex by keyword and looks up a DOI. | [`hubofhubs/the_world/science/openalex.py`](openalex.py) |  |
| OpenAlex semantic search | `the-science:openalex_semantic` | Matches the question to titles and abstracts by meaning, using OpenAlex's own embeddings. | [`hubofhubs/the_world/science/openalex_semantic.py`](openalex_semantic.py) | selected |
| OpenAlex keywords, rule rewrite | `the-science:openalex_keywords` | Cuts the question to a short keyword query by rule, then runs the keyword search. | [`hubofhubs/the_world/science/openalex_keywords.py`](openalex_keywords.py) |  |
| OpenAlex keywords, model rewrite | `the-science:openalex_keywords_model` | Has a cheap model write the keyword query through the model-call seat, then runs the keyword search. | [`hubofhubs/the_world/science/openalex_keywords.py`](openalex_keywords.py) |  |
| Semantic and web paper search | `the-science:openalex_semantic_and_web` | Finds papers by meaning through OpenAlex and adds a web search for what the index lacks. | [`hubofhubs/the_world/science/openalex_semantic_and_web.py`](openalex_semantic_and_web.py) |  |

## Where to go next

- Up: [hubofhubs](../../README.md)
- Intent: [Awareness of the outside and interaction with it](../README.md)
- Repository: [top README](../../../README.md)

*Generated from the CSV files in this folder by `esoi readmes`. Edit the CSV files, not this page.*
