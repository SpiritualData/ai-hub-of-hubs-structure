"""Offline tests of the model-provider arms, the router, retry and outage helpers: fake SDK clients, no network, no key."""
import sys
import types
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hubofhubs.models import family, layers, outage, retry  # noqa: E402
from hubofhubs.models.anthropic import AnthropicProvider, build_cached_system, thinking_kwargs  # noqa: E402
from hubofhubs.models.gemini import GeminiProvider, split_layers_for_gemini  # noqa: E402
from hubofhubs.models.openai import DEEPSEEK_BASE_URL, DeepSeekProvider, OpenAIProvider  # noqa: E402
from hubofhubs.models.router import MultiProvider  # noqa: E402

BLOCKS = [{"text": "HEAD", "cache": True}, {"text": "CTX", "cache": True}, {"text": "TAIL", "cache": False}]
TOOL = {"name": "decide", "input_schema": {"type": "object"}}


class Obj(types.SimpleNamespace):
    pass


# ---- retry and outage -------------------------------------------------------------------------------------------------

def test_parse_json_retries_until_valid_and_then_raises():
    seq = iter(["not json", "{bad", '{"action": "deep"}'])
    assert retry.parse_json_with_retry(lambda: next(seq), max_retries=3, base_delay=0.0) == {"action": "deep"}
    with pytest.raises(ValueError):
        retry.parse_json_with_retry(lambda: "nope", max_retries=1, base_delay=0.0)
    assert retry.parse_json_with_retry(lambda: {"a": 1}) == {"a": 1}
    seq = iter(['{"x": 1}', '{"action": "answer"}'])
    assert retry.parse_json_with_retry(lambda: next(seq), base_delay=0.0, validate=lambda o: "action" in o) == {"action": "answer"}


def test_transient_errors_are_retried_and_a_give_up_records_an_outage(monkeypatch):
    monkeypatch.setattr(retry.time, "sleep", lambda s: None)
    outage.reset_for_tests()
    calls = []

    @retry.retry_transient(max_retries=2, base_delay=0.0)
    def flaky(fail):
        calls.append(1)
        if fail:
            raise type("ServerError", (Exception,), {})("503 service unavailable")
        return "ok"

    assert flaky(False) == "ok" and len(calls) == 1
    with pytest.raises(Exception, match="503"):
        flaky(True)
    assert len(calls) == 4 and outage.seen_since(0) is not None
    assert not retry.is_transient_error(ValueError("bad input")) and retry.is_transient_error(FileNotFoundError("claude"))
    assert "billing" in retry.format_provider_error(type("ClientError", (Exception,), {})("403 PERMISSION_DENIED dunning"))
    assert "Rate limit" in retry.format_provider_error(RuntimeError("429 slow down"))


def test_outage_wording_and_the_raised_from_chain():
    outage.reset_for_tests()
    assert outage.is_outage(RuntimeError("529 Overloaded")) and not outage.is_outage(RuntimeError("timeout reading"))
    try:
        try:
            raise RuntimeError("503 service unavailable")
        except RuntimeError as inner:
            raise ValueError("wrapped") from inner
    except ValueError as exc:
        assert outage.from_exception(exc) is not None
        outage.note(exc)
    assert outage.seen_since(0) is not None and outage.seen_since(2e12) is None


# ---- family and routing -----------------------------------------------------------------------------------------------

def test_prefix_routing_is_data_and_a_family_name_means_the_newest_release():
    assert [family.provider_name_for_model(m) for m in ("claude-haiku-5-5", "gemini-3.1-flash-lite", "models/x", "gpt-4o", "deepseek-chat", "llama")] \
        == ["anthropic", "gemini", "gemini", "openai", "deepseek", None]
    assert family.provider_name_for_model("gpt-4o", {"anthropic"}) is None
    assert family.provider_name_for_model("llama-3", None, {"llama": "openai"}) == "openai"
    live = ["claude-opus-9", "claude-sonnet-9-1", "claude-sonnet-9", "claude-haiku-9"]
    assert family.resolve_model_name("sonnet", live) == "claude-sonnet-9-1" and family.resolve_model_name("claude-opus", live) == "claude-opus-9"
    assert family.resolve_model_name("claude-sonnet-9", live) == "claude-sonnet-9" and family.resolve_model_name("sonnet", []) == "sonnet"
    assert family.newest_in_family("gemini-flash-lite", ["gemini-3.1-flash", "gemini-3.1-flash-lite", "gemini-3.0-flash-lite"]) == "gemini-3.1-flash-lite"


def test_layer_helpers_cap_breakpoints_and_keep_the_last():
    assert layers.cache_control_indices([{"cache": True}] * 5 + [{"cache": False}], max_breakpoints=4) == [1, 2, 3, 4]
    assert layers.blocks_to_prompt(BLOCKS) == "HEAD\n\nCTX\n\nTAIL" and layers.join_layers("a", "", "b") == "a\n\nb"


# ---- Anthropic -------------------------------------------------------------------------------------------------------

class Messages:
    def __init__(self, thinking_param=True):
        self.last, self.thinking_param = None, thinking_param
        if not thinking_param:
            self.create = self.create_old

    def create(self, *, model, max_tokens, messages, system=None, tools=None, tool_choice=None, thinking=None):
        self.last = dict(model=model, messages=messages, system=system, tools=tools, tool_choice=tool_choice, thinking=thinking)
        block = Obj(type="tool_use", name="decide", input={"mode": "answer"}) if tool_choice else Obj(type="text", text="ok")
        return Obj(content=[block], usage=Obj(input_tokens=7, output_tokens=3))

    def create_old(self, *, model, max_tokens, messages, system=None, tools=None, tool_choice=None):
        self.last = dict(messages=messages)
        return Obj(content=[Obj(type="text", text="ok")])


def anthropic(messages=None, **kw):
    p = AnthropicProvider(api_key="offline", **kw)
    p.client = Obj(messages=messages or Messages())
    p.resolve_model = lambda m: m
    return p


def test_anthropic_turns_thinking_off_unless_enabled_or_unsupported():
    m = Messages()
    p = anthropic(m)
    assert p.plan("pick", model="haiku", tool_schema=TOOL) == {"mode": "answer"} and m.last["thinking"] == {"type": "disabled"}
    assert m.last["tool_choice"] == {"type": "tool", "name": "decide"}
    p.answer([{"role": "user", "content": "hi"}], model="haiku")
    assert m.last["thinking"] == {"type": "disabled"} and (p.tokens_in, p.tokens_out, p.call_count) == (14, 6, 2)
    on = Messages()
    anthropic(on, thinking=True).answer([], model="haiku")
    assert on.last["thinking"] is None
    old = Messages(thinking_param=False)
    assert anthropic(old).answer([{"role": "user", "content": "hi"}], model="haiku") == "ok" and thinking_kwargs(old.create) == {}


def test_anthropic_layers_become_a_cached_system_array_and_plain_calls_are_unchanged():
    m = Messages()
    p = anthropic(m)
    assert p.answer([{"role": "user", "content": "ignored"}], model="x", system="voice", layers=BLOCKS) == "ok"
    assert m.last["system"] == [{"type": "text", "text": "voice"}, {"type": "text", "text": "HEAD", "cache_control": {"type": "ephemeral"}},
                                {"type": "text", "text": "CTX", "cache_control": {"type": "ephemeral"}}]
    assert m.last["messages"] == [{"role": "user", "content": "TAIL"}]
    p.plan("fallback", model="x", tool_schema=TOOL, layers=BLOCKS)
    assert m.last["tools"] == [TOOL] and m.last["messages"] == [{"role": "user", "content": "TAIL"}]
    p.answer([{"role": "user", "content": "hello"}], model="x", system="be brief")
    assert m.last["messages"] == [{"role": "user", "content": "hello"}] and m.last["system"] == "be brief"
    p.plan("PLAIN", model="x", tool_schema=TOOL)
    assert m.last["messages"] == [{"role": "user", "content": "PLAIN"}] and m.last["system"] is None
    system, tail = build_cached_system(None, [{"text": f"b{i}", "cache": True} for i in range(6)] + [{"text": "t", "cache": False}])
    assert [b["text"] for b in system if "cache_control" in b] == ["b2", "b3", "b4", "b5"] and tail == "t"


def test_anthropic_web_search_collects_citations_and_family_names_resolve():
    p = anthropic()
    reply = Obj(content=[Obj(type="text", text="a", citations=[Obj(title="T", url="u1", cited_text="c")]),
                         Obj(type="web_search_tool_result", content=[Obj(type="web_search_result", title="T2", url="u2"),
                                                                     Obj(type="web_search_result", title="dup", url="u1")])])
    p.client.messages.create = lambda **kw: reply
    assert p.web_search("q", model="x") == {"answer": "a", "results": [{"title": "T", "url": "u1", "snippet": "c"}, {"title": "T2", "url": "u2", "snippet": ""}]}
    q = AnthropicProvider(api_key="k")
    q.listing.models, q.listing.at = ["claude-opus-9", "claude-sonnet-9-1", "claude-sonnet-9"], float("inf")
    assert q.resolve_model("sonnet") == "claude-sonnet-9-1" and q.resolve_model("claude-sonnet-9") == "claude-sonnet-9"
    assert AnthropicProvider().supports_web_search() is False and AnthropicProvider(api_key="k").supports_web_search()


# ---- Gemini ----------------------------------------------------------------------------------------------------------

class GeminiModels:
    def __init__(self, response):
        self.response, self.last = response, None

    def generate_content(self, **kwargs):
        self.last = kwargs
        return self.response


def gemini(text="ok", **extra):
    p = GeminiProvider(api_key="offline")
    p.client = Obj(models=GeminiModels(Obj(text=text, usage_metadata=Obj(prompt_token_count=5, candidates_token_count=2), **extra)))
    p.resolve_model = lambda m: m
    return p


def test_gemini_layers_become_system_instruction_and_stable_contents():
    assert split_layers_for_gemini("voice", BLOCKS) == ("voice\n\nHEAD", "CTX\n\nTAIL")
    assert split_layers_for_gemini(None, [{"text": "only tail", "cache": False}]) == (None, "only tail")
    p = gemini()
    assert p.answer([{"role": "user", "content": "ignored"}], model="m", system="voice", layers=BLOCKS) == "ok"
    assert p.client.models.last["config"] == {"system_instruction": "voice\n\nHEAD"} and p.client.models.last["contents"] == "CTX\n\nTAIL"
    assert p.plan("fallback", model="m", tool_schema=TOOL, layers=BLOCKS) == {}      # "ok" is not JSON: the safe empty decision
    assert p.client.models.last["config"]["response_mime_type"] == "application/json" and (p.tokens_in, p.tokens_out, p.call_count) == (20, 8, 4)


def test_gemini_plain_answer_flattens_and_sends_images_as_inline_parts():
    p = gemini()
    p.answer([{"role": "user", "content": "hello"}], model="m", system="be brief")
    assert p.client.models.last["contents"] == "System: be brief\nUser: hello" and p.client.models.last["config"] is None
    image = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "AAA"}}
    p.answer([{"role": "user", "content": [{"type": "text", "text": "see"}, image, {"type": "image", "source": {"type": "url"}}]}], model="m")
    parts = p.client.models.last["contents"][0]["parts"]
    assert parts[1] == {"inline_data": {"mime_type": "image/jpeg", "data": "AAA"}} and "[Image included]" in parts[0]["text"]


def test_gemini_minimal_reasoning_retries_without_the_thinking_config_when_rejected():
    p = gemini()
    seen = []
    real = p.client.models.generate_content

    def generate_content(**kw):
        seen.append(kw["config"])
        if kw["config"] and "thinking_config" in kw["config"]:
            raise RuntimeError("model does not support thinking")
        return real(**kw)
    p.client.models.generate_content = generate_content
    assert p.answer([{"role": "user", "content": "x"}], model="m", reasoning="minimal") == "ok"
    assert seen[0] == {"thinking_config": {"thinking_level": "minimal"}} and seen[1] is None


def test_gemini_url_fetch_reads_the_retrieval_status_and_fails_loudly():
    entry = Obj(url_retrieval_status="URL_RETRIEVAL_STATUS_SUCCESS", retrieved_url="https://example.org/final")
    ok = gemini("page text", candidates=[Obj(url_context_metadata=Obj(url_metadata=[entry]))])
    assert ok.supports_url_fetch() and not GeminiProvider().supports_url_fetch()
    assert ok.fetch_url("https://example.org/a", model="m") == {"text": "page text", "url": "https://example.org/final",
                                                                "status": "URL_RETRIEVAL_STATUS_SUCCESS"}
    bad = Obj(url_retrieval_status="URL_RETRIEVAL_STATUS_ERROR", retrieved_url="")
    with pytest.raises(RuntimeError, match="could not retrieve"):
        gemini("x", candidates=[Obj(url_context_metadata=Obj(url_metadata=[bad]))]).fetch_url("https://example.org/a", model="m")
    with pytest.raises(RuntimeError, match="no content"):
        gemini("  ", candidates=[]).fetch_url("https://example.org/a", model="m")


def test_gemini_model_list_is_cached_filtered_and_falls_back():
    p = GeminiProvider(api_key="k")
    names = [Obj(name=n) for n in ("models/gemini-3.1-flash", "models/gemini-exp-1", "models/other")]
    p.client = Obj(models=Obj(list=lambda: names))
    assert p.list_models() == ["models/gemini-3.1-flash"]
    p.client.models.list = lambda: (_ for _ in ()).throw(RuntimeError("down"))
    assert p.list_models() == ["models/gemini-3.1-flash"]                      # cached
    p.listing.at = -1e9
    assert p.list_models() == ["gemini-2.0-flash", "gemini-1.5-pro"]


# ---- OpenAI and DeepSeek ---------------------------------------------------------------------------------------------

def fake_openai(monkeypatch, captured):
    mod = types.ModuleType("openai")
    mod.OpenAI = lambda **kw: captured.update(kw) or Obj()
    monkeypatch.setitem(sys.modules, "openai", mod)


def test_openai_and_deepseek_clients_take_their_settings_as_arguments(monkeypatch):
    captured = {}
    fake_openai(monkeypatch, captured)
    DeepSeekProvider(api_key="k-test").get_client()
    assert captured == {"api_key": "k-test", "base_url": DEEPSEEK_BASE_URL}
    DeepSeekProvider(api_key="k", base_url="https://example.invalid").get_client()
    assert captured["base_url"] == "https://example.invalid"
    with pytest.raises(RuntimeError, match="API key"):
        DeepSeekProvider().get_client()
    OpenAIProvider(base_url="http://localhost:8000/v1", keyless=True).get_client()
    assert captured == {"api_key": "not-needed", "base_url": "http://localhost:8000/v1"}
    assert DeepSeekProvider(api_key="k").create_kwargs == {"extra_body": {"thinking": {"type": "disabled"}}}
    assert DeepSeekProvider(api_key="k", thinking=True).create_kwargs == {} and DeepSeekProvider().model_marker == "deepseek"


def test_openai_answer_counts_tokens_and_plan_falls_back_to_an_empty_decision(monkeypatch):
    p = OpenAIProvider(api_key="k")
    reply = lambda text: Obj(choices=[Obj(message=Obj(content=text))], usage=Obj(prompt_tokens=4, completion_tokens=2))
    create = Obj(calls=[])
    create.completions = Obj(create=lambda **kw: create.calls.append(kw) or reply('{"a": 1}'))
    p.client = Obj(chat=create)
    p.resolve_model = lambda m: m
    assert p.plan("x", model="m", tool_schema=TOOL) == {"a": 1} and create.calls[0]["response_format"] == {"type": "json_object"}
    assert p.answer([{"role": "user", "content": "hi"}], model="m", system="s") == '{"a": 1}'
    assert create.calls[1]["messages"] == [{"role": "system", "content": "s"}, {"role": "user", "content": "hi"}]
    assert (p.tokens_in, p.tokens_out) == (8, 4)
    create.completions.create = lambda **kw: reply("not json")
    monkeypatch.setattr(retry.time, "sleep", lambda s: None)
    assert p.plan("x", model="m", tool_schema=TOOL) == {}


# ---- the router ------------------------------------------------------------------------------------------------------

class Registry:
    def __init__(self, top):
        self.top = dict(top)
        self.order = {"best": "quality", "quality": "balanced", "balanced": "fast"}

    def top_models(self):
        return dict(self.top)

    def resolve_tier(self, tier):
        return self.top[tier]

    def lower_tier(self, tier):
        return self.order.get(tier)


class Flaky:
    def __init__(self, fail=None):
        self.fail, self.tokens_in, self.tokens_out, self.calls = dict(fail or {}), 0, 0, []

    def check(self, model):
        self.calls.append(model)
        self.tokens_in += 10
        self.tokens_out += 5
        if model in self.fail:
            raise self.fail[model]

    def plan(self, prompt, *, model, tool_schema, layers=None):
        self.check(model)
        return {"model": model}

    def answer(self, messages, *, model, system=None, layers=None):
        self.check(model)
        return f"answered by {model}"

    def web_search(self, query, *, model, max_results=5):
        self.check(model)
        return {"answer": model, "results": []}

    def list_models(self):
        return list(self.fail)


TOP = {"fast": "m-fast", "balanced": "m-balanced", "quality": "m-quality", "best": "m-best"}
QUOTA = Exception("429 RESOURCE_EXHAUSTED: quota exceeded")


def test_a_quota_error_steps_down_tier_by_tier_and_other_errors_do_not():
    flaky = Flaky({"m-best": QUOTA, "m-quality": QUOTA})
    mp = MultiProvider(flaky, registry=Registry(TOP))
    assert mp.plan("p", model="m-best", tool_schema={}) == {"model": "m-balanced"}
    assert mp.web_search("q", model="m-quality")["answer"] == "m-balanced"
    for fail, registry in (({"m-fast": QUOTA}, Registry(TOP)), ({"pinned": QUOTA}, Registry(TOP)), ({"m-best": QUOTA}, None),
                           ({"m-best": ValueError("blocked")}, Registry(TOP))):
        with pytest.raises(Exception):
            MultiProvider(Flaky(fail), registry=registry).answer([], model="pinned" if "pinned" in fail else next(iter(fail)))


def test_an_exhausted_model_is_skipped_during_its_cooldown():
    flaky = Flaky({"m-quality": QUOTA})
    mp = MultiProvider(flaky, {"gemini": flaky}, registry=Registry(TOP))
    mp.answer([], model="m-quality")
    mp.answer([], model="m-quality")
    assert flaky.calls == ["m-quality", "m-balanced", "m-balanced"]


def test_the_router_routes_by_prefix_counts_the_delta_and_stops_at_the_limit():
    anthropic_p, gemini_p, primary = Flaky(), Flaky(), Flaky()
    seen = []

    class Tracker:
        def over_limit(self):
            return bool(seen) and seen[-1][0] > 10

        def record(self, tokens_in, tokens_out, spec_id="", seconds=0.0):
            seen.append((tokens_in, tokens_out, spec_id))

    mp = MultiProvider(primary, {"anthropic": anthropic_p, "gemini": gemini_p}, usage_tracker=Tracker(), spec_of=lambda: "spec-1",
                       limit_message=lambda: "limit reached")
    assert mp.answer([], model="gemini-3.1-flash-lite") == "answered by gemini-3.1-flash-lite" and gemini_p.calls and not anthropic_p.calls
    mp.answer([], model="unknown-model")
    assert primary.calls == ["unknown-model"] and (mp.tokens_in, mp.tokens_out, mp.call_count) == (20, 10, 2)
    assert seen == [(10, 5, "spec-1"), (10, 5, "spec-1")]
    seen.append((11, 0, ""))
    assert mp.answer([], model="claude-haiku-5-5") == "limit reached" and mp.plan("p", model="m", tool_schema={})["action"] == "answer"
    assert mp.web_search("q", model="m")["results"] == [] and sorted(mp.list_models()) == []
