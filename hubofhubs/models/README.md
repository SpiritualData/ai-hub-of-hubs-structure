# Arms in models

*ESOI arms kept in `hubofhubs/models`, generated from the records of the intents that own them by `esoi readmes`. Edit those records, not this page.*

| Implementation | Handle | Code | Selected |
|---|---|---|---|
| Tier chooser then vendor | `model-plumbing:via_vendor` | [`hubofhubs/models/via_provider.py`](via_provider.py) | selected |
| Anthropic provider | `vendor-model-caller:anthropic` | [`hubofhubs/models/anthropic.py`](anthropic.py) |  |
| Claude Code CLI | `vendor-model-caller:claude_cli` | [`hubofhubs/models/claude_cli.py`](claude_cli.py) | selected |
| DeepSeek provider | `vendor-model-caller:deepseek` | [`hubofhubs/models/openai.py`](openai.py) |  |
| Gemini provider | `vendor-model-caller:gemini` | [`hubofhubs/models/gemini.py`](gemini.py) |  |
| Multi-provider router | `vendor-model-caller:multi_provider` | [`hubofhubs/models/router.py`](router.py) |  |
| OpenAI provider | `vendor-model-caller:openai` | [`hubofhubs/models/openai.py`](openai.py) |  |

## Where to go next

- Owning intent: [Awareness of the outside and interaction with it](../the_world/README.md)
- Repository: [top README](../../README.md)
