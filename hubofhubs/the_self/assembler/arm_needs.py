"""What the hub's arms need from their environment, stated once and shared.

Each arm sets ``REQUIRES`` from the pieces below (see ``esoi.requirements``). A service several arms use (Gemini for the model
and for web search, OpenAlex for all the scholarly arms) is declared here once, so the same facts are reported once. Every free-tier
and rate-limit statement is copied from the vendor's own page and dated ``AS_OF``; a fact that could not be confirmed on the
official page is left out. Nothing here reads the environment and nothing contacts a service: these are data.

Python requirements name the owning package's extra (``pyproject.toml``); ``hubofhubs/the_self/integrity/tests/test_requirements.py`` checks that every
declared module is provided by that extra.
"""
from esoi import requirements

AS_OF = "2026-10-31"

# --- python requirements: one per extra of pyproject.toml ------------------------------------------------------------------

HTTPX = requirements.python("httpx", "hubofhubs", extra="web")
HTTPX_SCIENCE = requirements.python("httpx", "hubofhubs", extra="science")
FILELOCK = requirements.python("filelock", "hubofhubs", extra="locks", required=False)
GOOGLE_GENAI = requirements.python("google.genai", "hubofhubs", extra="gemini")
ANTHROPIC_SDK = requirements.python("anthropic", "hubofhubs", extra="anthropic")
OPENAI_SDK = requirements.python("openai", "hubofhubs", extra="openai")
MCP_SDK = requirements.python("mcp", "hubofhubs", extra="mcp")
TRAFILATURA = requirements.python("trafilatura", "hubofhubs", extra="pages", required=False)
PYPDF = requirements.python("pypdf", "hubofhubs", extra="pages", required=False)
QDRANT_CLIENT = requirements.python("qdrant_client", "hubofhubs", extra="qdrant", required=False)
FASTEMBED = requirements.python("fastembed", "hubofhubs", extra="qdrant", required=False)
VOYAGE_SDK = requirements.python("voyageai", "hubofhubs", extra="voyage", required=False)
ACP_SDK = requirements.python("acp", "hubofhubs", extra="acp")
BM25S = requirements.python("bm25s", "hubofhubs", extra="bm25")
STEMMER = requirements.python("Stemmer", "hubofhubs", extra="bm25")
GRAPHIFY = requirements.python("graphify", "hubofhubs", extra="graphify")
FASTEMBED_LOCAL = requirements.python("fastembed", "hubofhubs", extra="retrieval")
NUMPY = requirements.python("numpy", "hubofhubs", extra="retrieval")
SKLEARN = requirements.python("sklearn", "hubofhubs", extra="retrieval")

# --- model vendors ----------------------------------------------------------------------------------------------------------

ANTHROPIC_API = requirements.api(
    "Anthropic", key=requirements.env("ANTHROPIC_API_KEY", option="api_key", secret=True),
    signup_url="https://platform.claude.com/", docs_url="https://platform.claude.com/docs/en/api/rate-limits",
    pricing_url="https://platform.claude.com/docs/en/about-claude/pricing",
    rate_limit="limits are set per organization by usage tier (requests, input tokens and output tokens a minute per model), "
               "with a monthly spend cap per tier; new organizations may start on a lower Evaluation tier",
    as_of=AS_OF)

GEMINI_API_NOTE = ("Google Search grounding free allowance: 500 requests a day shared by Gemini 2.5 Flash and Flash-Lite; "
                   "5,000 a month shared by Gemini 3 and newer models")
GEMINI_API_FREE = ("a free plan for developers and small projects (some models are not on it); " + GEMINI_API_NOTE)
GEMINI_API_RATE = "Gemini 3 and newer: a default cap of 1,500 grounded requests a day per project"


def gemini_api(*names: str):
    """The Gemini API, with the key variables in the order the arm uses them."""
    return requirements.api("Gemini", key=requirements.env(names[0], option="api_key", secret=True, also=names[1:]),
               signup_url="https://aistudio.google.com/apikey", docs_url="https://ai.google.dev/gemini-api/docs",
               pricing_url="https://ai.google.dev/gemini-api/docs/pricing", free_tier=GEMINI_API_FREE,
               rate_limit=GEMINI_API_RATE, as_of=AS_OF)


OPENAI_API = requirements.api(
    "OpenAI", signup_url="https://platform.openai.com/api-keys", docs_url="https://platform.openai.com/docs",
    pricing_url="https://openai.com/api/pricing/",
    rate_limit="limits depend on the organization's usage tier and the model; the tier rises automatically with total credit "
               "purchases ($5 Build, $100 Launch, $500 Grow)",
    as_of=AS_OF, note="a key, or a base url for an endpoint that takes none")
OPENAI_KEY = requirements.env("OPENAI_API_KEY", option="api_key", secret=True, group="openai key or endpoint")
OPENAI_BASE_URL = requirements.env("OPENAI_BASE_URL", option="base_url", group="openai key or endpoint")

DEEPSEEK_API = requirements.api(
    "DeepSeek", key=requirements.env("DEEPSEEK_API_KEY", option="api_key", secret=True),
    signup_url="https://platform.deepseek.com/", docs_url="https://api-docs.deepseek.com/",
    pricing_url="https://api-docs.deepseek.com/quick_start/pricing",
    rate_limit="concurrency limits of 2,500 (deepseek-flash) and 500 (deepseek-v4-pro)", as_of=AS_OF)
DEEPSEEK_BASE_URL = requirements.env("DEEPSEEK_BASE_URL", option="base_url", required=False)

# --- web search APIs --------------------------------------------------------------------------------------------------------

SERPER_API = requirements.api(
    "Serper", key=requirements.env("SERPER_API_KEY", option="api_key", secret=True),
    signup_url="https://serper.dev/", docs_url="https://serper.dev/", pricing_url="https://serper.dev/",
    free_tier="2,500 free queries on signup, no credit card required", as_of=AS_OF)

BRAVE_API = requirements.api(
    "Brave Search", key=requirements.env("BRAVE_SEARCH_API_KEY", option="api_key", secret=True, also=("BRAVE_API_KEY",)),
    signup_url="https://brave.com/search/api/", docs_url="https://brave.com/search/api/", pricing_url="https://brave.com/search/api/",
    free_tier="the Search plan ($5 per 1,000 requests) includes $5 in free credits every month",
    rate_limit="Search plan: 50 queries per second", as_of=AS_OF)

TAVILY_API = requirements.api(
    "Tavily", key=requirements.env("TAVILY_API_KEY", option="api_key", secret=True, also=("WEB_SEARCH_API_KEY",)),
    signup_url="https://app.tavily.com/", docs_url="https://docs.tavily.com/",
    pricing_url="https://docs.tavily.com/documentation/api-credits",
    free_tier="1,000 free API credits every month", as_of=AS_OF)

SEARXNG_SERVICE = requirements.service("SearXNG", "SEARXNG_URL", health_path=None)
SEARXNG_URL = requirements.env("SEARXNG_URL", option="base_url", note="a self-hosted SearXNG instance whose settings allow the json format (the arm requests format=json)")

# Every arm that sends a request to a hosted service declares the network, so an offline run answers pending-network for it
# and never tries a live call.
GEMINI_NETWORK = requirements.network("generativelanguage.googleapis.com", note="Gemini calls and Google Search grounding go to Google")
ANTHROPIC_NETWORK = requirements.network("api.anthropic.com", note="model calls go to Anthropic")
OPENAI_NETWORK = requirements.network("api.openai.com", note="model calls go to OpenAI, or to the endpoint named by the base url")
DEEPSEEK_NETWORK = requirements.network("api.deepseek.com", note="model calls go to DeepSeek")
WEB_SEARCH_NETWORK = requirements.network("", note="the search API is called over the network")
SEARXNG_NETWORK = requirements.network("", note="the SearXNG instance is reached over the network")
WEB_PAGES_NETWORK = requirements.network("", note="pages are fetched from the web")

# --- scholarly and DOI services ---------------------------------------------------------------------------------------------

# Every scholarly arm reaches OpenAlex over the network, so an offline run answers pending-network for it and never tries a live call.
OPENALEX_NETWORK = requirements.network("api.openalex.org", note="the scholarly arms search OpenAlex live")

OPENALEX_API = requirements.api(
    "OpenAlex", key=requirements.env("OPENALEX_API_KEY", option="api_key", secret=True), keyless=True,
    signup_url="https://help.openalex.org/how-to-use-the-api/rate-limits-and-authentication",
    docs_url="https://help.openalex.org/how-to-use-the-api/rate-limits-and-authentication",
    pricing_url="https://help.openalex.org/how-to-use-the-api/rate-limits-and-authentication",
    free_tier="works with no key; a free key gives 10 times the keyless daily budget (each free account gets $1 a day, key works once its email is verified)",
    rate_limit="10 requests per second with no key, 30 with a free key; semantic search 1 request per second; the daily budget resets at midnight UTC",
    as_of=AS_OF)

CROSSREF_API = requirements.api(
    "Crossref", keyless=True, docs_url="https://www.crossref.org/documentation/retrieve-metadata/rest-api/",
    as_of=AS_OF, required=False)

# --- retrieval --------------------------------------------------------------------------------------------------------------

QDRANT_SERVICE = requirements.service("Qdrant", "QDRANT_URL", default_url="http://localhost:6333", health_path="healthz", required=False)
FASTEMBED_MODEL = requirements.download("BAAI/bge-small-en-v1.5 (fastembed, ONNX)", size_mb=67, cache_hint="/tmp")
VOYAGE_API = requirements.api(
    "Voyage AI", key=requirements.env("VOYAGE_API_KEY", option="api_key", secret=True), required=False,
    signup_url="https://dashboard.voyageai.com/", docs_url="https://docs.voyageai.com/",
    pricing_url="https://docs.voyageai.com/docs/pricing",
    free_tier="new accounts get 200 million free tokens on the voyage-4 family; older models get none", as_of=AS_OF)

# --- acting -----------------------------------------------------------------------------------------------------------------

WRITE_ROOT = requirements.env("HUBOFHUBS_WRITE_ROOT", option="root",
                 note="the one folder the file-editing runner may write in; nothing is writable until you name it")

# --- the Claude Code runners ------------------------------------------------------------------------------------------------

CLAUDE_BINARY = requirements.binary("claude", "install Claude Code: https://code.claude.com/docs/en/setup", version_args=("--version",))
CLAUDE_ACCOUNT = requirements.resource("Claude Code needs a Pro, Max, Ultra, Team, Enterprise or Console account (the free claude.ai plan does not include it); "
                          "a run bills that account (https://code.claude.com/docs/en/setup)")
CLAUDE_CLI_BOUNDARY = requirements.isolatable("cli")
ACP_BINARY = requirements.binary("claude-agent-acp", "install the Claude ACP agent with npm; it needs Node 22 or later", version_args=("--version",))
NODE_BINARY = requirements.binary("node", "install Node 22 or later (the ACP agent declares it)", version_args=("--version",))
ACP_BOUNDARY = requirements.isolatable("subprocess")
