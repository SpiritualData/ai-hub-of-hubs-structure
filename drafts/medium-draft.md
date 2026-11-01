# Medium draft (not published)

A draft article for the owner to edit, about 900 words. The line between the markers is generated from `esoi/results.csv` by
`python3 scripts/status.py`. The findings below were filled from the README on 2026-10-31; refresh them from it if results change before publishing.

---

# Which AI part is actually best? We measure the alternatives on the same cases

<!-- headline-compact:start -->
36 alternatives measured across 8 areas, from 448 researched candidates. By area: Memory store 1, RAG retrieval 6, LLM routing and failover 2, LLMs (model quality and cost) 13, Web search APIs 2, Scholarly search 6, Coding agents 3, Guardrails and oversight 3.
<!-- headline-compact:end -->

## The problem with lists

Anyone building with AI meets lists of vector stores, search APIs, coding agents and guardrail tools. Each list says what exists, not which one works best for your job, whether the difference is real, or whether it is still true next quarter. Public benchmarks use different tasks and harnesses, so numbers from two leaderboards cannot be compared with each other.

We wanted one structure that answers the question the same way for every part, and that a reader can check.

## The idea

ai-hub-of-hubs-structure is an open repository. It describes an AI system as a mind with seats: memory, models, tools, search, risk, acting. Each seat is a narrow interface. Open-source hubs, combinations of them, or a plain fallback can fill a seat, and each one is called an arm. The repository contains the interface, the arms, the cases they are scored on, and every recorded result.

A consumer such as an AI product connects the hub and calls one function, `hubofhubs.assemble`. Each seat is filled with the arm that measured best, and a seat that needs something from you says exactly what to pass.

## The method

Three rules do most of the work.

First, every arm of a seat runs on exactly the same cases with the same budget. We record the pass rate with its 95% interval, the cost per passing case and the seconds per case.

Second, a challenger replaces the selected arm only when a one-sided exact paired test on the shared cases gives p below 0.05, with a correction when there are several rivals. If the test cannot show the challenger is better, the incumbent stays and the page says how many cases the two arms disagree on. More cases settle it, never a hand-picked margin.

Third, what other people measured sits beside our results and never inside them. Each public number keeps its source, who ran it, whether the method is disclosed, how many cases it used and its known confounds, and is graded A to D. A vendor reporting its own product is never above D. Public evidence helps decide which arms are worth building and acts as a check when it disagrees with us; it does not move our numbers.

Baselines and floors, such as "no overseer at all", are run so that a real arm has something to beat, but they are not counted as alternatives.

## What has been measured

The numbers below are generated from the results file each time the README is rebuilt.

<!-- headline-compact:start -->
36 alternatives measured across 8 areas, from 448 researched candidates. By area: Memory store 1, RAG retrieval 6, LLM routing and failover 2, LLMs (model quality and cost) 13, Web search APIs 2, Scholarly search 6, Coding agents 3, Guardrails and oversight 3.
<!-- headline-compact:end -->

Areas in the list are the ones people building agents tend to ask about: retrieval for RAG, the models themselves, routing and failover between providers, web search APIs, scholarly search, coding agents, guardrails and a memory store. The README has the full table, with the cases and their source for each check.

## Three findings

**Failover is a clear win, and cheap to check.** On simulated provider outages, a router that steps to a fallback model answered 30 of 30 cases while a single provider answered 12 of 30 on the same cases (exact McNemar test, p < 0.0001). This is plain mechanics rather than a research result, and the check exists because a real production assistant stopped answering when its only provider ran out of credit.

**Web search: one arm ahead, the rest unmeasured.** For finding a page that holds the answer to a factual question, Gemini grounding found the page in 32 of 40 questions against 12 of 40 for a provider-native search (p < 0.0001). Paid search APIs such as Brave, Serper and Tavily need keys that are not set where we measure, so they are listed as not measured and not guessed at. A close independent test in the public research found no engine clearly best, which is why we want to run them.

**Scholarly search: search by meaning wins.** For finding the paper that answers a research question, OpenAlex semantic search found it in 52 of 150 questions and web research in 18 of 150 (p < 0.0001); combining the two found 49. Public research favours search by meaning over keywords for this task, and our numbers agree. Keyword-only OpenAlex scored far lower on the smaller stage.

## What we have not measured

This is the part we think makes the rest believable. The README lists, with a reason, every seat that has no check: the higher mind that chooses whose long view grounds the work, critical thinking, and the planning loop that currently lives in the production consumer. It also lists arms we named but have not run, and why, such as an agent runner whose binary is not installed on the measuring machine. Rows recorded before later edits to the code are flagged for a re-run. Small samples give wide intervals, and the page shows them.

## Why this shape

Seats and arms make a choice replaceable. A better search API or a cheaper model becomes a new arm, runs on the existing cases, and either leads the incumbent, with the test saying whether the lead is real, or does not. Results carry the commit and case hash, and each area is re-researched within 90 days.

## Try it

Install it by path or from git, then call `hubofhubs.assemble(environ=os.environ)`. If you have an alternative that belongs in a seat, add it as an arm and the same cases will score it.

Repository: github.com/SpiritualData/ai-hub-of-hubs-structure
