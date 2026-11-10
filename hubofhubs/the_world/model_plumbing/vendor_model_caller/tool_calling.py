"""Native tool calling for the vendor model callers: one neutral turn shape, and per vendor the pure functions that turn it into the vendor's documented
request and read the vendor's response back. A model does best in the tool interface it is trained on, so an agent loop speaks each vendor's own
(Anthropic tool use, Gemini function calling, OpenAI Responses function and apply_patch items) and not a private text protocol.

The neutral transcript is a list of plain dicts, so a session can be saved and resumed as JSON:

* ``{"role": "user", "text": str}``
* ``{"role": "assistant", "text": str, "calls": [{"id", "name", "args"}], "raw": <the vendor's own turn, kept to send back>}``
* ``{"role": "tool", "results": [{"id", "name", "text", "error": bool}]}``

Every function here is pure (no network, no environment). ``tool_turn`` on a provider (``AnthropicProvider``, ``GeminiProvider``, ``OpenAIProvider``) calls
the vendor SDK, imported on first use, with what these functions build. Anthropic is the path measured end to end; Gemini and OpenAI are written against
their documented interfaces and tested here against the shapes only. Standard library only.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence

BUILTIN_APPLY_PATCH = {"type": "apply_patch"}   # OpenAI's built-in apply_patch tool: declared with no schema, answered with apply_patch_call items


@dataclass
class ToolSpec:
    """One tool the model may call. ``schema`` is a JSON Schema object for the arguments; ``builtin`` is a vendor-defined tool declared by its own
    ``type`` (OpenAI ``apply_patch``) with no schema of ours."""
    name: str
    description: str = ""
    schema: Dict[str, Any] = field(default_factory=lambda: {"type": "object", "properties": {}})
    builtin: Optional[Dict[str, Any]] = None


@dataclass
class ToolCall:
    id: str
    name: str
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelTurn:
    """What one model call returned: its text, the tool calls it asked for, the vendor's own turn (``raw``, to put back in the transcript) and the tokens."""
    text: str = ""
    calls: List[ToolCall] = field(default_factory=list)
    raw: Any = None
    tokens_in: int = 0           # all input tokens, cached or not
    tokens_out: int = 0
    cache_read: int = 0
    cache_write: int = 0
    finish: str = ""

    def as_message(self) -> Dict[str, Any]:
        return {"role": "assistant", "text": self.text, "calls": [{"id": c.id, "name": c.name, "args": c.args} for c in self.calls], "raw": self.raw}


def user_message(text: str) -> Dict[str, Any]:
    return {"role": "user", "text": text}


def tool_message(results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {"role": "tool", "results": [{"id": str(r["id"]), "name": str(r.get("name") or ""), "text": str(r.get("text") or ""), "error": bool(r.get("error"))}
                                        for r in results]}


def jsonable(value: Any) -> Any:
    """``value`` as plain JSON data (an SDK object through its ``model_dump``), so a transcript can be saved."""
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, Mapping):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


# --- Anthropic: Messages API tool use ----------------------------------------------------------------------------------------------------

def anthropic_tools(tools: Sequence[ToolSpec]) -> List[Dict[str, Any]]:
    """The ``tools`` of a Messages request (``input_schema``); the last carries a cache breakpoint, so the whole tool list is read from the cache."""
    out = [{"name": t.name, "description": t.description, "input_schema": t.schema} for t in tools if not t.builtin]
    if out:
        out[-1] = dict(out[-1], cache_control={"type": "ephemeral"})
    return out


def anthropic_messages(transcript: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """The ``messages`` of a Messages request. The results of one turn's parallel tool calls go in ONE user message as ``tool_result`` blocks (the documented
    rule). The last message carries a cache breakpoint, so each call reads the whole earlier transcript from the cache."""
    messages: List[Dict[str, Any]] = []
    for message in transcript:
        role = message.get("role")
        if role == "user":
            messages.append({"role": "user", "content": [{"type": "text", "text": str(message.get("text") or "") or "(empty)"}]})
        elif role == "assistant":
            blocks: List[Dict[str, Any]] = [{"type": "text", "text": str(message["text"])}] if str(message.get("text") or "").strip() else []
            blocks += [{"type": "tool_use", "id": c["id"], "name": c["name"], "input": c.get("args") or {}} for c in message.get("calls") or []]
            messages.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "(no text)"}]})
        elif role == "tool":
            messages.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": r["id"], "content": r["text"] or "(no output)",
                                                          **({"is_error": True} if r.get("error") else {})} for r in message.get("results") or []]})
    if messages and isinstance(messages[-1]["content"], list) and messages[-1]["role"] == "user":
        last = messages[-1]["content"][-1]
        last["cache_control"] = {"type": "ephemeral"}
    return messages


def anthropic_turn(response: Any) -> ModelTurn:
    turn = ModelTurn(finish=str(getattr(response, "stop_reason", "") or ""))
    texts: List[str] = []
    for block in list(getattr(response, "content", None) or []):
        kind = getattr(block, "type", None)
        if kind == "text":
            texts.append(str(getattr(block, "text", "") or ""))
        elif kind == "tool_use":
            turn.calls.append(ToolCall(id=str(block.id), name=str(block.name), args=dict(getattr(block, "input", None) or {})))
    turn.text = "".join(texts)
    usage = getattr(response, "usage", None)
    if usage is not None:
        turn.cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        turn.cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        turn.tokens_in = int((getattr(usage, "input_tokens", 0) or 0) + turn.cache_read + turn.cache_write)
        turn.tokens_out = int(getattr(usage, "output_tokens", 0) or 0)
    return turn


# --- Gemini: generate_content with function declarations -------------------------------------------------------------------------------

def gemini_tools(tools: Sequence[ToolSpec]) -> List[Dict[str, Any]]:
    return [{"function_declarations": [{"name": t.name, "description": t.description, "parameters_json_schema": t.schema} for t in tools if not t.builtin]}]


def gemini_contents(transcript: Sequence[Mapping[str, Any]]) -> List[Any]:
    """The ``contents`` of a Gemini request. A model turn is sent back as the vendor returned it (``raw``), which keeps the thought signatures newer models
    require; a turn with no ``raw`` (a resumed session) is rebuilt from its text and calls."""
    contents: List[Any] = []
    for message in transcript:
        role = message.get("role")
        if role == "user":
            contents.append({"role": "user", "parts": [{"text": str(message.get("text") or "")}]})
        elif role == "assistant":
            if message.get("raw") is not None and not isinstance(message["raw"], (dict, list)):
                contents.append(message["raw"])
                continue
            parts: List[Dict[str, Any]] = [{"text": str(message["text"])}] if message.get("text") else []
            parts += [{"function_call": {"name": c["name"], "args": c.get("args") or {}}} for c in message.get("calls") or []]
            contents.append({"role": "model", "parts": parts or [{"text": ""}]})
        elif role == "tool":
            contents.append({"role": "user", "parts": [{"function_response": {"name": r["name"], "response": {"error": r["text"]} if r.get("error") else {"output": r["text"]}}}
                                                       for r in message.get("results") or []]})
    return contents


def gemini_turn(response: Any) -> ModelTurn:
    turn = ModelTurn()
    candidates = list(getattr(response, "candidates", None) or [])
    content = getattr(candidates[0], "content", None) if candidates else None
    turn.finish = str(getattr(candidates[0], "finish_reason", "") or "") if candidates else ""
    texts: List[str] = []
    for index, part in enumerate(list(getattr(content, "parts", None) or [])):
        call = getattr(part, "function_call", None)
        if call is not None and getattr(call, "name", None):
            turn.calls.append(ToolCall(id=str(getattr(call, "id", None) or f"call_{index}"), name=str(call.name), args=dict(getattr(call, "args", None) or {})))
        elif getattr(part, "text", None) and not getattr(part, "thought", False):
            texts.append(str(part.text))
    turn.text = "".join(texts)
    turn.raw = content
    meta = getattr(response, "usage_metadata", None)
    if meta is not None:
        turn.tokens_in = int(getattr(meta, "prompt_token_count", 0) or 0)
        turn.tokens_out = int((getattr(meta, "candidates_token_count", 0) or 0) + (getattr(meta, "thoughts_token_count", 0) or 0))
    return turn


# --- OpenAI: Responses API function and apply_patch items ----------------------------------------------------------------------------------

def openai_tools(tools: Sequence[ToolSpec]) -> List[Dict[str, Any]]:
    return [dict(t.builtin) if t.builtin else {"type": "function", "name": t.name, "description": t.description, "parameters": t.schema} for t in tools]


def openai_input(transcript: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """The ``input`` items of a Responses request (stateless: the whole transcript is sent). A model turn is its own output items (``raw``, plain dicts); a
    result answers a ``function_call`` with ``function_call_output`` and an ``apply_patch_call`` with ``apply_patch_call_output``."""
    items: List[Dict[str, Any]] = []
    for message in transcript:
        role = message.get("role")
        if role == "user":
            items.append({"role": "user", "content": str(message.get("text") or "")})
        elif role == "assistant":
            if isinstance(message.get("raw"), list):
                items.extend(message["raw"])
                continue
            if str(message.get("text") or "").strip():
                items.append({"role": "assistant", "content": str(message["text"])})
            for call in message.get("calls") or []:
                if call["name"] == "apply_patch":
                    items.append({"type": "apply_patch_call", "call_id": call["id"], "status": "completed", "operation": call.get("args") or {}})
                else:
                    items.append({"type": "function_call", "call_id": call["id"], "name": call["name"], "arguments": json.dumps(call.get("args") or {})})
        elif role == "tool":
            for r in message.get("results") or []:
                if r["name"] == "apply_patch":
                    items.append({"type": "apply_patch_call_output", "call_id": r["id"], "status": "failed" if r.get("error") else "completed", "output": r["text"]})
                else:
                    items.append({"type": "function_call_output", "call_id": r["id"], "output": r["text"]})
    return items


def openai_turn(response: Any) -> ModelTurn:
    turn = ModelTurn(finish=str(getattr(response, "status", "") or ""))
    raw: List[Dict[str, Any]] = []
    texts: List[str] = []
    for item in list(getattr(response, "output", None) or []):
        data = jsonable(item)
        raw.append(data)
        kind = data.get("type")
        if kind == "function_call":
            try:
                args = json.loads(data.get("arguments") or "{}")
            except ValueError:
                args = {"_unparsed": data.get("arguments")}
            turn.calls.append(ToolCall(id=str(data.get("call_id")), name=str(data.get("name")), args=args if isinstance(args, dict) else {"value": args}))
        elif kind == "apply_patch_call":
            turn.calls.append(ToolCall(id=str(data.get("call_id")), name="apply_patch", args=dict(data.get("operation") or {})))
        elif kind == "message":
            texts += [str(c.get("text") or "") for c in data.get("content") or [] if c.get("type") == "output_text"]
    turn.text = "".join(texts)
    turn.raw = raw
    usage = getattr(response, "usage", None)
    if usage is not None:
        turn.tokens_in, turn.tokens_out = int(getattr(usage, "input_tokens", 0) or 0), int(getattr(usage, "output_tokens", 0) or 0)
    return turn
