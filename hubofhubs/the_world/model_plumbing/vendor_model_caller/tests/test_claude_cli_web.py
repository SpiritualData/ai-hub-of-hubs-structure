"""Offline tests for the web search and page tools of the ``claude_cli`` arm: no network, no model, no real process."""
import json

from hubofhubs.the_world.model_plumbing.vendor_model_caller import claude_cli as ccp
from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
from hubofhubs.the_world.tools.web_search.backends import select_search_backend
from hubofhubs.the_world.tools.web_search.claude_login import ClaudeLoginBackend


def run_with(monkeypatch, result, returncode=0):
    """A provider whose process is a fake returning ``result`` in the CLI's envelope; the captured command is returned beside it."""
    captured = {}

    def fake_run(cmd, **kwargs):
        captured.update(cmd=cmd, cwd=kwargs.get("cwd"), timeout=kwargs.get("timeout"))

        class Done:
            stdout = json.dumps({"result": result, "usage": {"input_tokens": 3, "output_tokens": 2}, "total_cost_usd": 0.01}).encode()
            stderr = b""
        Done.returncode = returncode
        return Done()

    monkeypatch.setattr(ccp, "_supported_flags", lambda binary: frozenset(ccp._ONE_SHOT_FLAGS))
    monkeypatch.setattr(ccp, "run_in_group", fake_run)
    return ClaudeCliProvider(), captured


def after(cmd, flag):
    return cmd[cmd.index(flag) + 1]


GOOD = json.dumps({"answer": "3.15 is current", "results": [
    {"title": "Python 3.15", "url": "https://www.python.org/downloads/", "snippet": "Download Python", "date": "2026-10-09"},
    {"title": "no link", "url": "not a url", "snippet": "x"}]})


def test_a_search_allows_only_the_search_tool_and_keeps_the_pure_completion_flags(monkeypatch):
    provider, seen = run_with(monkeypatch, GOOD)
    provider.web_search("latest python", model="haiku")
    cmd = seen["cmd"]
    assert after(cmd, "--tools") == "WebSearch" and after(cmd, "--allowed-tools") == "WebSearch"
    disallowed = after(cmd, "--disallowed-tools").split(",")
    assert "WebFetch" in disallowed and "Bash" in disallowed and "WebSearch" not in disallowed
    assert after(cmd, "--max-turns") == str(ccp.WEB_MAX_TURNS)
    for flag in ("--strict-mcp-config", "--exclude-dynamic-system-prompt-sections"):
        assert flag in cmd
    assert after(cmd, "--setting-sources") == "" and after(cmd, "--model") == "haiku"
    assert seen["cwd"] == ccp._neutral_cwd() and seen["timeout"] <= ccp.WEB_TIMEOUT_SECONDS


def test_a_page_read_allows_only_the_fetch_tool(monkeypatch):
    provider, seen = run_with(monkeypatch, "page text")
    assert provider.fetch_url("https://example.org", model="haiku")["text"] == "page text"
    assert after(seen["cmd"], "--tools") == "WebFetch" and "WebSearch" in after(seen["cmd"], "--disallowed-tools").split(",")


def test_a_pure_completion_still_has_no_tool(monkeypatch):
    provider, seen = run_with(monkeypatch, "ok")
    provider._invoke("hi", model="haiku")
    assert after(seen["cmd"], "--tools") == "" and "--allowed-tools" not in seen["cmd"] and "--max-turns" not in seen["cmd"]


def test_a_good_reply_gives_http_results_only_and_counts_usage(monkeypatch):
    provider, _ = run_with(monkeypatch, "```json\n" + GOOD + "\n```")
    found = provider.web_search("latest python", model="haiku", max_results=5)
    assert [r["url"] for r in found["results"]] == ["https://www.python.org/downloads/"]
    assert found["results"][0]["date"] == "2026-10-09" and found["answer"] == "3.15 is current" and "error" not in found
    assert provider.call_count == 1 and provider.tokens_in == 3 and provider.cost_usd == 0.01


def test_a_malformed_or_empty_reply_is_an_empty_result_with_an_error(monkeypatch):
    for reply in ("no json here", "", '{"results": "none"}'):
        provider, _ = run_with(monkeypatch, reply)
        found = provider.web_search("q", model="haiku")
        assert found["results"] == [] and found["error"]


def test_a_failed_process_is_an_empty_result_with_an_error(monkeypatch):
    provider, _ = run_with(monkeypatch, "boom", returncode=1)
    found = provider.web_search("q", model="haiku")
    assert found["results"] == [] and "error" in found


def test_the_backend_wraps_the_provider_and_is_chosen_only_by_name(monkeypatch):
    provider, _ = run_with(monkeypatch, GOOD)
    backend = select_search_backend({"WEB_SEARCH_BACKEND": "claude_login"}, provider=provider)
    assert isinstance(backend, ClaudeLoginBackend)
    assert backend.search("latest python").hits[0].url == "https://www.python.org/downloads/"
    assert select_search_backend({}, provider=provider) is None
    assert select_search_backend({"WEB_SEARCH_BACKEND": "claude_login", "WEB_SEARCH_ENABLED": "false"}, provider=provider) is None
