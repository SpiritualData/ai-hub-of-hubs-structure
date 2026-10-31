"""One way to ask every model the same prompt: the hub's provider classes for the API arms, the Claude Code CLI for Claude.

Each runner returns ``fn(kind, args) -> text``. Reasoning is switched ON for every model that has it, with the setting named in
``SETTINGS`` and recorded in the README. Output is capped at ``MAX_OUTPUT`` tokens for every model (a truncated answer fails).
Claude is called through ``claude -p`` on the existing subscription with the API key variables removed from the child environment, so
no API dollars are spent; tokens are those the CLI reports (prompt tokens include its fixed system prompt and cache reads).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from priced import first_env, price_of, priced  # noqa: E402

MAX_OUTPUT = 32768
PROMPT = ("Solve this problem. Think it through, then end with one last line of exactly this form, with only the integer "
          "(from 0 to 999, no units, no commas): Final answer: <integer>\n\n{question}")

SETTINGS = {
    "gemini": "thinking_budget=-1 (dynamic thinking on)",
    "openai": "reasoning_effort=medium",
    "deepseek": "thinking enabled (the model's default)",
    "claude": "claude -p --effort high, no tools, no settings sources",
}


def gemini_arm(model):
    from hubofhubs.models.gemini import GeminiProvider

    def build(meter):
        provider = priced(GeminiProvider, price_of("gemini", model))(api_key=first_env("GOOGLE_API_KEY", "GEMINI_API_KEY", "GOOGLE_AI_API_KEY"))
        meter.model = model
        meter.wrap(provider, ("request",))
        config = {"thinking_config": {"thinking_budget": -1}, "max_output_tokens": MAX_OUTPUT, "http_options": {"timeout": 900_000}}

        def run(kind, args):
            response = provider.request(model, PROMPT.format(question=args["question"]), config)
            return response.text or ""
        return run
    return build


def chat_arm(vendor, model, provider_name, variables, provider_options=None, **options):
    """OpenAI-compatible chat completion on the hub's OpenAI or DeepSeek provider; ``options`` are request keyword arguments."""
    import hubofhubs.models.openai as hub

    def build(meter):
        provider = priced(getattr(hub, provider_name), price_of(vendor, model))(api_key=first_env(*variables), **(provider_options or {}))
        meter.model = model
        meter.wrap(provider, ("complete",))

        def run(kind, args):
            response = provider.complete(model, [{"role": "user", "content": PROMPT.format(question=args["question"])}],
                                         max_completion_tokens=MAX_OUTPUT, **options) if vendor == "openai" else \
                provider.complete(model, [{"role": "user", "content": PROMPT.format(question=args["question"])}],
                                  max_tokens=MAX_OUTPUT, **options)
            return response.choices[0].message.content or ""
        return run
    return build


def openai_arm(model):
    return chat_arm("openai", model, "OpenAIProvider", ("OPENAI_API_KEY",), reasoning_effort="medium")


def deepseek_arm(model):
    return chat_arm("deepseek", model, "DeepSeekProvider", ("DEEPSEEK_API_KEY",), provider_options={"thinking": True},
                    extra_body={"thinking": {"type": "enabled"}})


class SubscriptionCounter:
    """Token and call counters in the shape ``CallMeter.wrap`` reads; cost stays 0.0 because nothing is billed per token."""
    tokens_in = tokens_out = 0
    cost_usd = 0.0


def claude_arm(alias):
    """``claude -p`` for the model alias (haiku, sonnet, opus). The recorded model is the id the CLI reports having used."""
    def build(meter):
        counter = SubscriptionCounter()
        scratch = tempfile.mkdtemp(prefix="aime-claude-")
        environ = {k: v for k, v in os.environ.items() if not k.startswith("ANTHROPIC_API") and k not in ("ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL")}

        def ask(question):
            done = subprocess.run(
                ["claude", "-p", PROMPT.format(question=question), "--model", alias, "--effort", "high", "--output-format", "json",
                 "--tools", "", "--setting-sources", "", "--strict-mcp-config", "--no-session-persistence"],
                capture_output=True, text=True, timeout=1800, cwd=scratch, env=environ, stdin=subprocess.DEVNULL)
            out = json.loads(done.stdout)
            if out.get("is_error"):
                raise RuntimeError(f"claude -p failed: {out.get('result')}")
            usage = out.get("usage", {})
            counter.tokens_in += sum(usage.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
            counter.tokens_out += usage.get("output_tokens", 0) or 0
            meter.model = next(iter(out.get("modelUsage", {})), alias)
            return out.get("result") or ""
        counter.ask = ask
        meter.wrap(counter, ("ask",))

        def run(kind, args):
            return counter.ask(args["question"])
        return run
    return build
