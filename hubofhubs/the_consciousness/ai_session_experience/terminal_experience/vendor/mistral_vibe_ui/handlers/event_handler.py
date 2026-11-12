"""Turns the typed history events of the hub into widgets for the terminal screen. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file cli/textual_ui/handlers/event_handler.py); modified from upstream: hook notices, fired loops, plan review, model change, session title, profile and context-cleared callbacks cut; the constructor drops on_profile_changed, on_context_cleared and on_session_title_changed."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from pydantic import ValidationError
from textual.widget import Widget

from ..protocol.events import (
    AppServerEvent,
    HistoryEntryAdded,
    HistoryEntryUpdated,
    SessionSnapshot,
)
from ..protocol.models import (
    CancelledEffectState,
    CompletedEffectState,
    ContextClearedNoticeDetail,
    FailedEffectState,
    JsonPatchOperation,
    PublicCallbackEntry,
    PublicCheckpointEntry,
    PublicEffectEntry,
    PublicEntryGenerationStatus,
    PublicHistoryEntry,
    PublicMessageEntry,
    PublicNoticeEntry,
    PublicReasoningEntry,
    SkippedEffectState,
    TodoEffectOutput,
    WaitingForInputNoticeDetail,
)
from ..protocol.tool_presentation import ToolEffectKind
from ..todo_tracker import TodoTracker
from ..widgets.compact import CompactMessage
from ..widgets.loading import DEFAULT_LOADING_STATUS, THINKING_LOADING_STATUS
from ..widgets.messages import (
    AssistantMessage,
    ErrorMessage,
    ReasoningMessage,
    SlashCommandMessage,
)
from ..widgets.tools import (
    ToolCallMessage,
    ToolGroup,
    ToolResultMessage,
    _effect_state_is_failure,
    _effect_state_to_indicator,
    entry_keeps_tool_group,
    is_manual_shell_entry,
)
from ..windowing.history import history_entry_renders_widget

if TYPE_CHECKING:
    from ..widgets.loading import LoadingWidget


@dataclass(slots=True)
class _RetryPresentation:
    assistant: AssistantMessage | None
    transient_widgets: list[Widget] = field(default_factory=list)
    active: bool = False


class EventHandler:
    def __init__(
        self,
        mount_callback: Callable,
        get_tools_collapsed: Callable[[], bool],
        get_show_thinking: Callable[[], bool] | None = None,
        todo_tracker: TodoTracker | None = None,
        on_todos_changed: Callable[[], None] | None = None,
    ) -> None:
        self.mount_callback = mount_callback
        self.get_tools_collapsed = get_tools_collapsed
        self.get_show_thinking = get_show_thinking or (lambda: True)
        self.todo_tracker = todo_tracker
        self.on_todos_changed = on_todos_changed
        self.tool_calls: dict[str, ToolCallMessage] = {}
        self.current_compact: CompactMessage | None = None
        self.current_streaming_message: AssistantMessage | None = None
        self._turn_assistant_message: AssistantMessage | None = None
        self.current_streaming_reasoning: ReasoningMessage | None = None
        self.current_tool_group: ToolGroup | None = None
        self._tool_call_anchors: dict[str, Widget] = {}
        self._pending_error_results: list[ToolResultMessage] = []
        self._retry_presentation: _RetryPresentation | None = None

    def offer_retry(self, error: ErrorMessage | None = None) -> None:
        presentation = self._retry_presentation
        if presentation is None:
            presentation = _RetryPresentation(self._turn_assistant_message)
            self._retry_presentation = presentation
        elif presentation.assistant is None:
            presentation.assistant = self._turn_assistant_message
        if error is not None:
            presentation.transient_widgets.append(error)
        presentation.active = False

    def begin_retry(self, command: SlashCommandMessage | None = None) -> bool:
        if self._retry_presentation is None:
            return False
        if command is not None:
            self._retry_presentation.transient_widgets.append(command)
        self._retry_presentation.active = True
        return True

    def cancel_retry_presentation(self) -> None:
        self._retry_presentation = None
        self._turn_assistant_message = None

    async def handle_event(
        self, event: AppServerEvent, loading_widget: LoadingWidget | None = None
    ) -> ToolCallMessage | None:
        match event:
            case HistoryEntryAdded(entry=entry):
                return await self._handle_entry_added(entry, loading_widget)
            case HistoryEntryUpdated() as update:
                await self._handle_entry_updated(update, loading_widget)
            case SessionSnapshot(state=state) if loading_widget is not None:
                loading_widget.set_retrying(state.retrying is not None)
            case _:
                pass
        return None

    async def _handle_entry_added(
        self, entry: PublicHistoryEntry, loading_widget: LoadingWidget | None
    ) -> ToolCallMessage | None:
        if isinstance(
            entry, PublicCheckpointEntry
        ) and not history_entry_renders_widget(entry):
            return None
        if self.current_tool_group is not None and not entry_keeps_tool_group(entry):
            self._finalize_tool_group()

        match entry:
            case PublicMessageEntry(role="assistant"):
                await self._handle_assistant_delta(entry.text, loading_widget)
                if entry.generation_status is PublicEntryGenerationStatus.COMPLETED:
                    await self.finalize_streaming()
            case PublicMessageEntry(role="user"):
                self.cancel_retry_presentation()
                await self.finalize_streaming()
            case PublicMessageEntry(role="system"):
                await self._resolve_retry_presentation(continue_assistant=False)
            case PublicReasoningEntry():
                await self._resolve_retry_presentation(continue_assistant=False)
                await self._handle_reasoning_delta(entry.text, loading_widget)
                if entry.generation_status is PublicEntryGenerationStatus.COMPLETED:
                    await self.finalize_streaming()
            case PublicEffectEntry():
                await self._resolve_retry_presentation(continue_assistant=False)
                await self.finalize_streaming()
                tool_call = await self._handle_effect_started(entry, loading_widget)
                if _effect_is_terminal(entry):
                    await self._handle_effect_completed(entry, loading_widget)
                return tool_call
            case PublicCheckpointEntry():
                await self._resolve_retry_presentation(continue_assistant=False)
                await self.finalize_streaming()
                await self._handle_checkpoint_added(entry)
            case PublicNoticeEntry():
                await self._resolve_retry_presentation(continue_assistant=False)
                await self._handle_notice(entry, loading_widget)
            case PublicCallbackEntry():
                await self._resolve_retry_presentation(continue_assistant=False)
                await self.finalize_streaming()
            case _:
                raise TypeError(
                    f"Unsupported public history entry: {type(entry).__name__}"
                )
        return None

    async def _handle_checkpoint_added(self, entry: PublicCheckpointEntry) -> None:
        """Render a transcript annotation the Harness wrote.

        An unknown kind is skipped rather than raised on: checkpoint kinds are
        added by the Harness, and a Runtime newer than this CLI must not take
        the event stream down with it.
        """
        match entry.kind:
            case "compaction":
                await self._handle_compact_start()
                if entry.generation_status is PublicEntryGenerationStatus.COMPLETED:
                    await self._handle_compact_end()

    async def _handle_entry_updated(
        self, update: HistoryEntryUpdated, loading_widget: LoadingWidget | None
    ) -> None:
        entry = update.entry
        match entry:
            case PublicMessageEntry(role="assistant"):
                if delta := _appended_text(update.patch, "/content/0/text"):
                    if self.current_tool_group is not None:
                        self._finalize_tool_group()
                    await self._handle_assistant_delta(delta, loading_widget)
                if entry.generation_status is PublicEntryGenerationStatus.COMPLETED:
                    await self.finalize_streaming()
            case PublicReasoningEntry():
                if delta := _appended_text(update.patch, "/text"):
                    await self._handle_reasoning_delta(delta, loading_widget)
                if entry.generation_status is PublicEntryGenerationStatus.COMPLETED:
                    await self.finalize_streaming()
            case PublicEffectEntry():
                call = self.tool_calls.get(entry.id)
                if call is not None:
                    call.update_entry(entry)
                    if output := _appended_text(update.patch, "/state/outputText"):
                        call.set_stream_message(output)
                if _effect_became_terminal(update):
                    await self.finalize_streaming()
                    await self._handle_effect_completed(entry, loading_widget)
                elif loading_widget is not None:
                    loading_widget.set_status(entry.detail.display.status_text)
            case PublicCheckpointEntry(kind="compaction"):
                if entry.generation_status is PublicEntryGenerationStatus.COMPLETED:
                    await self.finalize_streaming()
                    await self._handle_compact_end()
            case _:
                pass

    async def _handle_effect_started(
        self, entry: PublicEffectEntry, loading_widget: LoadingWidget | None
    ) -> ToolCallMessage:
        existing = self.tool_calls.get(entry.id)
        if existing is not None:
            existing.update_entry(entry)
            tool_call = existing
        else:
            tool_call = ToolCallMessage(entry)
            self.tool_calls[entry.id] = tool_call
            self._tool_call_anchors[entry.id] = tool_call
            if is_manual_shell_entry(entry):
                # Mounted at top level, not in a group: `_handle_entry_added`
                # already closed the open one, and folding the user's own `!`
                # command into a summary line would hide what they ran it for.
                await self.mount_callback(tool_call)
            else:
                group = await self._ensure_tool_group()
                group.add_call_kind(entry.detail.kind)
                await self._mount_in_group(group, tool_call)
        if loading_widget is not None:
            loading_widget.set_status(entry.detail.display.status_text)
        return tool_call

    def _record_todos(self, entry: PublicEffectEntry) -> str | None:
        # ``None`` means "render this the old way".
        if self.todo_tracker is None or entry.detail.kind is not ToolEffectKind.TODO:
            return None
        if not isinstance(entry.state, CompletedEffectState):
            return None
        try:
            output = TodoEffectOutput.model_validate(entry.state.output)
        except ValidationError:
            return None
        delta = self.todo_tracker.record(output.todos)
        if self.on_todos_changed is not None:
            self.on_todos_changed()
        return delta

    async def _handle_effect_completed(
        self, entry: PublicEffectEntry, loading_widget: LoadingWidget | None
    ) -> None:
        call_widget = self.tool_calls.get(entry.id)
        anchor = self._tool_call_anchors.get(entry.id) or call_widget
        result = ToolResultMessage(
            entry, call_widget, todo_delta=self._record_todos(entry)
        )
        await self.mount_callback(result, after=anchor)
        if _effect_state_is_failure(entry.state):
            self._pending_error_results.append(result)
        elif isinstance(entry.state, CompletedEffectState):
            # A successful call means earlier errors in the group were
            # recoverable: keep their indicators muted (grey) instead of
            # escalating them to red at turn end.
            self._resolve_pending_errors(escalate=False)
        if self.current_tool_group is not None and not is_manual_shell_entry(entry):
            self.current_tool_group.settle_indicator(
                _effect_state_to_indicator(entry.state)
            )
        self._tool_call_anchors[entry.id] = result
        self.tool_calls.pop(entry.id, None)
        if loading_widget is not None and not self.tool_calls:
            loading_widget.set_status(DEFAULT_LOADING_STATUS)

    async def _handle_assistant_delta(
        self, content: str, loading_widget: LoadingWidget | None
    ) -> None:
        if self.current_streaming_reasoning is not None:
            self.current_streaming_reasoning.stop_spinning()
            await self.current_streaming_reasoning.stop_stream()
            self.current_streaming_reasoning = None
        if self.current_streaming_message is None:
            if loading_widget is not None:
                loading_widget.set_status(DEFAULT_LOADING_STATUS)
            message = await self._resolve_retry_presentation(continue_assistant=True)
            if message is not None:
                self.current_streaming_message = message
                self._turn_assistant_message = message
                await message.append_content(content)
                return
            message = AssistantMessage(content)
            self.current_streaming_message = message
            self._turn_assistant_message = message
            await self.mount_callback(message)
            return
        await self.current_streaming_message.append_content(content)

    async def _resolve_retry_presentation(
        self, *, continue_assistant: bool
    ) -> AssistantMessage | None:
        presentation = self._retry_presentation
        if presentation is None or not presentation.active:
            return None
        self._retry_presentation = None
        for widget in presentation.transient_widgets:
            if widget.parent is not None:
                await widget.remove()
        assistant = presentation.assistant
        if not continue_assistant or assistant is None or assistant.parent is None:
            return None
        return assistant

    async def _handle_reasoning_delta(
        self, content: str, loading_widget: LoadingWidget | None
    ) -> None:
        if loading_widget is not None:
            loading_widget.set_status(THINKING_LOADING_STATUS)
        if self.current_streaming_message is not None:
            await self.current_streaming_message.stop_stream()
            if self.current_streaming_message.is_stripped_content_empty():
                await self.current_streaming_message.remove()
            self.current_streaming_message = None
        if self.current_streaming_reasoning is None:
            message = ReasoningMessage(content, collapsed=self.get_tools_collapsed())
            self.current_streaming_reasoning = message
            group = await self._ensure_tool_group()
            if self.get_show_thinking():
                group.mark_reasoning()
            await self._mount_in_group(group, message)
            if not self.get_show_thinking():
                message.display = False
                group.sync_visibility()
            return
        await self.current_streaming_reasoning.append_content(content)

    async def _handle_notice(
        self, entry: PublicNoticeEntry, loading_widget: LoadingWidget | None
    ) -> None:
        match entry.detail:
            case ContextClearedNoticeDetail() | WaitingForInputNoticeDetail():
                await self.finalize_streaming()

    def _finalize_tool_group(self, *, escalate: bool = True) -> None:
        if self.current_tool_group is not None:
            self._resolve_pending_errors(escalate=escalate)
            self.current_tool_group.finalize()
        self.current_tool_group = None

    async def _ensure_tool_group(self) -> ToolGroup:
        if self.current_tool_group is None:
            group = ToolGroup()
            self.current_tool_group = group
            await self.mount_callback(group)
        return self.current_tool_group

    async def _mount_in_group(self, group: ToolGroup, widget: Widget) -> None:
        children = list(group.content_container.children)
        if children:
            await self.mount_callback(widget, after=children[-1])
        else:
            await self.mount_callback(widget, container=group.content_container)
        group.sync_visibility()

    async def _handle_compact_start(self) -> None:
        compact = CompactMessage()
        self.current_compact = compact
        await self.mount_callback(compact)

    async def _handle_compact_end(self) -> None:
        if self.current_compact is None:
            return
        self.current_compact.set_complete()
        self.current_compact = None

    def _resolve_pending_errors(self, *, escalate: bool) -> None:
        if escalate:
            for result in self._pending_error_results:
                result.escalate_error()
        self._pending_error_results.clear()

    def escalate_unresolved_errors(self) -> None:
        self._resolve_pending_errors(escalate=True)

    async def finalize_streaming(self) -> None:
        if self.current_streaming_reasoning is not None:
            self.current_streaming_reasoning.stop_spinning()
            await self.current_streaming_reasoning.stop_stream()
            self.current_streaming_reasoning = None
        if self.current_streaming_message is not None:
            await self.current_streaming_message.stop_stream()
            self.current_streaming_message = None

    def stop_current_tool_call(
        self, success: bool = True, *, cancelled: bool = False
    ) -> None:
        for tool_call in self.tool_calls.values():
            if cancelled:
                tool_call.show_muted()
            else:
                tool_call.stop_spinning(success=success)
        self.tool_calls.clear()
        self._tool_call_anchors.clear()
        self._finalize_tool_group(escalate=not cancelled)

    def stop_current_compact(self) -> None:
        if self.current_compact:
            self.current_compact.stop_spinning(success=False)
            self.current_compact = None


def _appended_text(patch: list[JsonPatchOperation], path: str) -> str:
    return "".join(
        operation.value
        for operation in patch
        if operation.op == "append"
        and operation.path == path
        and isinstance(operation.value, str)
    )


def _effect_is_terminal(entry: PublicEffectEntry) -> bool:
    return isinstance(
        entry.state,
        CompletedEffectState
        | FailedEffectState
        | CancelledEffectState
        | SkippedEffectState,
    )


def _effect_became_terminal(update: HistoryEntryUpdated) -> bool:
    return (
        isinstance(update.entry, PublicEffectEntry)
        and _effect_is_terminal(update.entry)
        and (
            not isinstance(update.previous, PublicEffectEntry)
            or not _effect_is_terminal(update.previous)
        )
    )
