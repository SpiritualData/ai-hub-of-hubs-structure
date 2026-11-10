"""Native tool calling of the vendor model callers: the neutral transcript becomes each vendor's documented request and the vendor's response is read back. Pure functions and
fake SDK clients; no network."""
from types import SimpleNamespace as NS

from hubofhubs.the_world.model_plumbing.vendor_model_caller import tool_calling as tc
from hubofhubs.the_world.model_plumbing.vendor_model_caller.anthropic import AnthropicProvider

TRANSCRIPT = [
    tc.user_message("do it"),
    {"role": "assistant", "text": "reading", "calls": [{"id": "t1", "name": "Read", "args": {"file_path": "a.txt"}}, {"id": "t2", "name": "Bash", "args": {"command": "ls"}}], "raw": None},
    tc.tool_message([{"id": "t1", "name": "Read", "text": "one"}, {"id": "t2", "name": "Bash", "text": "boom", "error": True}]),
]


def test_anthropic_parallel_results_share_one_user_message_and_the_last_block_is_cached():
    messages = tc.anthropic_messages(TRANSCRIPT)
    assert [m["role"] for m in messages] == ["user", "assistant", "user"]
    assert [b["type"] for b in messages[1]["content"]] == ["text", "tool_use", "tool_use"]
    results = messages[2]["content"]
    assert [b["tool_use_id"] for b in results] == ["t1", "t2"] and results[1]["is_error"] is True and "is_error" not in results[0]
    assert results[-1]["cache_control"] == {"type": "ephemeral"}


def test_anthropic_tools_use_input_schema_and_skip_builtin():
    specs = [tc.ToolSpec("Bash", "run", {"type": "object", "properties": {}}), tc.ToolSpec("apply_patch", builtin=tc.BUILTIN_APPLY_PATCH)]
    out = tc.anthropic_tools(specs)
    assert [t["name"] for t in out] == ["Bash"] and "input_schema" in out[0] and out[0]["cache_control"]["type"] == "ephemeral"


def test_anthropic_turn_reads_text_calls_and_cache_usage():
    response = NS(stop_reason="tool_use", content=[NS(type="text", text="ok"), NS(type="tool_use", id="x", name="Read", input={"file_path": "a"})],
                  usage=NS(input_tokens=5, cache_read_input_tokens=100, cache_creation_input_tokens=20, output_tokens=7))
    turn = tc.anthropic_turn(response)
    assert turn.text == "ok" and turn.calls[0].name == "Read" and turn.calls[0].args == {"file_path": "a"}
    assert (turn.tokens_in, turn.cache_read, turn.cache_write, turn.tokens_out, turn.finish) == (125, 100, 20, 7, "tool_use")


def test_anthropic_provider_tool_turn_builds_the_request_and_counts_the_cache():
    sent = {}

    class Messages:
        def create(self, **kwargs):
            sent.update(kwargs)
            return NS(stop_reason="end_turn", content=[NS(type="text", text="done")], usage=NS(input_tokens=1, cache_read_input_tokens=2, cache_creation_input_tokens=3, output_tokens=4))
    provider = AnthropicProvider(api_key="k")
    provider.client = NS(messages=Messages())
    turn = provider.tool_turn(TRANSCRIPT, model="claude-test", system="be brief", tools=[tc.ToolSpec("Bash", "run")])
    assert turn.text == "done" and sent["model"] == "claude-test" and sent["system"][0]["cache_control"]["type"] == "ephemeral" and sent["tools"][0]["name"] == "Bash"
    assert provider.cache_read_tokens == 2 and provider.cache_creation_tokens == 3 and provider.call_count == 1


def test_openai_input_answers_function_and_apply_patch_calls_with_their_own_output_items():
    transcript = [tc.user_message("go"),
                  {"role": "assistant", "text": "", "calls": [{"id": "c1", "name": "apply_patch", "args": {"type": "update_file", "path": "a", "diff": "@@"}},
                                                               {"id": "c2", "name": "shell", "args": {"command": ["ls"]}}], "raw": None},
                  tc.tool_message([{"id": "c1", "name": "apply_patch", "text": "Updated a"}, {"id": "c2", "name": "shell", "text": "x", "error": True}])]
    items = tc.openai_input(transcript)
    kinds = [i.get("type") or i.get("role") for i in items]
    assert kinds == ["user", "apply_patch_call", "function_call", "apply_patch_call_output", "function_call_output"]
    assert items[3]["status"] == "completed" and items[2]["arguments"] == '{"command": ["ls"]}'
    assert {"type": "apply_patch"} in tc.openai_tools([tc.ToolSpec("apply_patch", builtin=tc.BUILTIN_APPLY_PATCH)])


def test_openai_turn_reads_function_and_apply_patch_items():
    class Item:
        def __init__(self, data):
            self.data = data

        def model_dump(self, **_):
            return self.data
    response = NS(status="completed", output=[Item({"type": "function_call", "call_id": "f", "name": "shell", "arguments": '{"command": ["ls"]}'}),
                                              Item({"type": "apply_patch_call", "call_id": "p", "operation": {"type": "create_file", "path": "n", "diff": "x"}}),
                                              Item({"type": "message", "content": [{"type": "output_text", "text": "hi"}]})], usage=NS(input_tokens=3, output_tokens=2))
    turn = tc.openai_turn(response)
    assert [c.name for c in turn.calls] == ["shell", "apply_patch"] and turn.calls[0].args == {"command": ["ls"]} and turn.text == "hi" and len(turn.raw) == 3


def test_gemini_contents_rebuild_a_resumed_turn_and_answer_with_function_responses():
    contents = tc.gemini_contents(TRANSCRIPT)
    assert contents[1]["role"] == "model" and contents[1]["parts"][1] == {"function_call": {"name": "Read", "args": {"file_path": "a.txt"}}}
    assert contents[2]["parts"][1]["function_response"]["response"] == {"error": "boom"}
    declared = tc.gemini_tools([tc.ToolSpec("read_file", "r", {"type": "object"})])[0]["function_declarations"][0]
    assert declared["name"] == "read_file" and "parameters_json_schema" in declared
