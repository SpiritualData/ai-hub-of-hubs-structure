"""Model-provider arms of the call-a-model seat: thin wrappers over one vendor SDK each (extras ``anthropic``, ``gemini``,
``openai``), the prefix router over them, retry and outage helpers, and the prompt-layer helpers they share. Settings come in
as constructor arguments; nothing here reads the environment. Third-party libraries are imported inside functions."""
