# Announcement draft (not published)

A draft LinkedIn post for the owner to edit. The first paragraph between the markers is generated from `esoi/results.csv` by
`python3 scripts/status.py`; do not edit it by hand. Items marked FILL take their number from the README evidence table on the day
of posting. The post body (below the line) must stay under 1,300 characters once filled.

---

<!-- headline-compact:start -->
33 alternatives measured across 8 areas, from 448 researched candidates. By area: Memory store 1, RAG retrieval 4, LLM routing and failover 2, LLMs (model quality and cost) 12, Web search APIs 2, Scholarly search 6, Coding agents 3, Guardrails and oversight 3.
<!-- headline-compact:end -->

Lists of "best AI tools" say what exists, not which one works best or whether the difference is real. This open repository puts alternatives in the same seat and runs them on the same cases, with a paired test before any challenger replaces the incumbent. Public research is graded and shown beside our numbers, never mixed into them.

Three findings so far:
- Provider failover: [FILL: passing cases of the router vs a single provider, and p] (README row: call-a-model, failover).
- Web search for a source: [FILL: gemini vs provider-native search, and p] (README row: search-backend).
- Finding a paper for a research question: [FILL: web_research vs openalex, and the verdict]. Where the test does not separate two arms, we say so.

What is not measured yet is listed in the README with the reason.

One line to start: hubofhubs.assemble(environ=os.environ)

Repo: github.com/SpiritualData/ai-hub-of-hubs-structure
