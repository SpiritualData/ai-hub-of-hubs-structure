# Arms in models

*ESOI arms kept in `hubofhubs/models`, generated from the records of the intents that own them by `esoi readmes`. Edit those records, not this page.*

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Anthropic provider | `call-a-model:anthropic` | [`hubofhubs/models/anthropic.py`](anthropic.py) |  |
| Claude Code CLI | `call-a-model:claude_cli` | [`hubofhubs/models/claude_cli.py`](claude_cli.py) | selected |
| DeepSeek provider | `call-a-model:deepseek` | [`hubofhubs/models/openai.py`](openai.py) |  |
| Gemini provider | `call-a-model:gemini` | [`hubofhubs/models/gemini.py`](gemini.py) |  |
| Multi-provider router | `call-a-model:multi_provider` | [`hubofhubs/models/router.py`](router.py) |  |
| OpenAI provider | `call-a-model:openai` | [`hubofhubs/models/openai.py`](openai.py) |  |
| Built on the vendor model caller | `model-call:via_call_a_model` | [`hubofhubs/models/via_provider.py`](via_provider.py) | selected |

## Where to go next

- Owning intent: [The parts working as one whole](../the_self/README.md)
- Repository: [top README](../../README.md)
