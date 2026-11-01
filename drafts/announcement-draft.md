# Announcement draft (not published)

A draft LinkedIn post for the owner to edit. The first paragraph between the markers is generated from `esoi/results.csv` by
`python3 scripts/status.py`; do not edit it by hand. The three findings were filled from the README evidence table on 2026-10-31; refresh them from it if results change before posting. The post body (below the line) must stay under 1,300 characters once filled.

---

<!-- headline-compact:start -->
35 alternatives measured across 8 areas, from 448 researched candidates. By area: Memory store 1, RAG retrieval 6, LLM routing and failover 2, LLMs (model quality and cost) 12, Web search APIs 2, Scholarly search 6, Coding agents 3, Guardrails and oversight 3.
<!-- headline-compact:end -->

Lists of "best AI tools" say what exists, not which one works best or whether the difference is real. This open repository puts alternatives in the same seat and runs them on the same cases, and each lead is labelled significant (a paired test) or a best guess. Public research is graded and shown beside our numbers, never mixed in.

Three findings so far:
- Provider failover: 30 of 30 cases answered with a fallback router vs 12 of 30 with a single provider (p < 0.0001).
- Web search for a source: Gemini grounding found it in 32 of 40 questions vs 12 of 40 for provider-native search (p < 0.0001).
- Finding a paper for a research question: OpenAlex semantic search 52 of 150 vs web research 18 of 150 (p < 0.0001). Where the test does not separate two arms, we say so.

What is not measured yet is listed in the README with the reason.

One line to start: hubofhubs.assemble(environ=os.environ)

Repo: github.com/SpiritualData/ai-hub-of-hubs-structure
