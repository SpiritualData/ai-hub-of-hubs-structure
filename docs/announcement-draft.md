# Announcement draft (not published)

A draft LinkedIn post for the owner to edit. Every number comes from the README evidence table or its seats table as generated on
2026-10-31; check each against the README before posting, because the table regenerates when new results are recorded.

---

Lists of "best AI tools" say what exists, not which part works best or whether the difference is real.

We built ai-hub-of-hubs-structure to answer that. It is an open repository with one seat for each part of an AI mind (memory, models, search, risk, acting) and several open-source arms competing for each seat on the same cases. A seat keeps the arm that measures best, and a challenger only wins when a paired test says so.

What the 15 recorded checks show so far:
- Provider failover: 30 of 30 cases answered, against 12 of 30 for a single provider (McNemar p=3.81e-06).
- Web search for a source: Gemini grounding 30 of 40, a provider-native search 12 of 40 (p=2e-05).
- Finding a paper for a research question: 6 of 40 against 2 of 40, which the test does not separate. We say so.

What is not measured yet is listed in the README with the reason: the higher mind (hold-the-intents), critical thinking and the planning loop have no check. Public research is graded and shown beside our numbers, never mixed into them.

One line gets you started: hubofhubs.assemble(environ=os.environ). It builds the seats that need nothing more from you and says exactly what to pass for the rest.

Repo: github.com/SpiritualData/ai-hub-of-hubs-structure
