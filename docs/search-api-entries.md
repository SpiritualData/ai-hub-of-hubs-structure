# Search APIs described as data

A hosted search API that answers JSON over HTTP needs no class. A consumer reads a list of entries from a JSON file and runs
each with one generic backend. An entry has these fields:

| Field | Meaning |
|---|---|
| `name` | the backend name |
| `method` | `GET` or `POST` |
| `url` | the endpoint |
| `key_env` | environment variable names that may hold the key; the first one set is used |
| `headers` | sent as given; `{key}` is replaced by the key |
| `send` | `json` (request body) or `params` (query string) |
| `payload` | what is sent; the value `"{query}"` becomes the query and `"{max_results}"` the integer count |
| `results_path` | dotted path to the list of results in the reply |
| `fields` | `title`, `url`, `snippet`, `date`: each a list of keys; the first non-empty one in a result is used |
| `strip_tags` | fields whose HTML tags are removed |
| `answer_paths` | dotted paths tried in order for a direct answer; an empty list means none |

An entry is one service, so it is an integration, not a hub connection: prefer a federating engine, and keep an entry as a
fallback only with a recorded reason.
