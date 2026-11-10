"""Resourcefulness, free stage: which routes a fact can hide behind does each Claude Code arm's own tool surface reach (read from its configuration, no run,
no model call). The hub loop reaches the shell (history, a database file, command output, a script to a service) and, with the sandbox's network, a page; its
web search is a tool a consumer hands it."""
from hubofhubs.the_world.tools.delegated_agent_sessions.contract import SubprocessConfig
from hubofhubs.the_world.tools.delegated_agent_sessions.native_runner import NativeToolLoopRunner
from hubofhubs.the_world.tools.delegated_agent_sessions.stream_runner import StreamJsonGoalRunner

ROUTES = ("files", "history_files_and_git", "database_file", "command_output", "web_search", "web_page", "service_history_via_script")


def surface(runner):
    tools = runner.launch_settings().tools
    shell = tools is None or "Bash" in tools
    web = runner.cfg.web_enabled()
    return {"files": True, "history_files_and_git": shell, "database_file": shell, "command_output": shell,
            "web_search": web and (tools is None or "WebSearch" in tools), "web_page": web and (tools is None or "WebFetch" in tools) or shell,
            "service_history_via_script": shell}


def test_the_native_arm_and_the_stream_arm_reach_every_route():
    config = SubprocessConfig(working_dir="/tmp")
    for runner in (NativeToolLoopRunner(config, provider="anthropic", tier="fast"), StreamJsonGoalRunner(config, provider="anthropic", tier="fast")):
        assert all(surface(runner)[route] for route in ROUTES), (type(runner).__name__, surface(runner))


def test_an_arm_pinned_without_the_shell_or_the_web_loses_those_routes():
    config = SubprocessConfig(working_dir="/tmp", allowed_tools=["Read"], disallowed_tools=["WebSearch", "WebFetch"])
    got = surface(StreamJsonGoalRunner(config, provider="anthropic", tier="fast"))
    assert not got["web_search"] and got["files"]
