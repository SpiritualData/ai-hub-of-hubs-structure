"""ClaudeLoginBackend: web search through the Claude Code login, with no search key.

The hub's provider-native backend over the hub's ``claude_cli`` provider, whose ``web_search`` runs one headless ``claude -p`` call
allowed only the CLI's own search tool. It is for a deployment that has the Claude Code login and no search service: it is named
explicitly in the settings (``backend`` of ``select_search_backend``), so it never changes which backend a deployment gets by itself.
"""
from __future__ import annotations

from typing import Any

from esoi import implementation

from hubofhubs.the_self.assembler import arm_needs as needs
from hubofhubs.the_world.tools.web_search.backends import ProviderNativeBackend


@implementation("web-search", "claude_login")
class ClaudeLoginBackend(ProviderNativeBackend):
    """Provider-native search over the Claude Code login (a ``ClaudeCliProvider`` is built when none is given)."""
    REQUIRES = (needs.CLAUDE_BINARY, needs.CLAUDE_ACCOUNT)

    PAID = True      # every search is a model call on the login: never run by a free (offline) metric run

    name = "claude-login"

    def __init__(self, provider: Any = None, model: str = "") -> None:
        if provider is None:
            from hubofhubs.the_world.model_plumbing.vendor_model_caller.claude_cli import ClaudeCliProvider
            provider = ClaudeCliProvider()
        super().__init__(provider, model)
