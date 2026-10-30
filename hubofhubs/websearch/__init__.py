"""Web search that executes: search backends (SearXNG, JSON search APIs described as data, Gemini grounding, a provider's own
search), a cache, a daily limiter, SSRF-guarded page fetching and extraction, and the planner-facing research adapter.
Importing this package runs nothing; third-party libraries are loaded lazily by the arm that needs them (extras ``web``,
``gemini``, ``pages``)."""
