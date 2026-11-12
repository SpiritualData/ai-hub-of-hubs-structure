"""Chat input body: prompt mark, text area and history recall. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file vibe/cli/textual_ui/widgets/chat_input/body.py); modified from upstream: voice input and recording indicator, queue selection and edit, the bash and teleport prompt modes cut; imports rewritten."""

from __future__ import annotations

from functools import partial
from pathlib import Path
from typing import Any, ClassVar

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from ...commands import CommandRegistry
from ...history_manager import HistoryManager
from ...input_modes import InputMode
from ..no_markup_static import NoMarkupStatic
from ..spinner import SpinnerMixin, SpinnerType
from .text_area import ChatTextArea


class _PromptSpinner(SpinnerMixin, Static):
    SPINNER_TYPE: ClassVar[SpinnerType] = SpinnerType.BRAILLE

    def __init__(self) -> None:
        self._indicator_widget: Static | None = None
        self.init_spinner()
        super().__init__(self._spinner.current_frame(), id="prompt-spinner")

    def on_mount(self) -> None:
        self._indicator_widget = self
        self.start_spinner_timer()


class ChatInputBody(Widget):
    class Submitted(Message):
        def __init__(self, value: str) -> None:
            self.value = value
            super().__init__()

    class CompletionResetRequested(Message):
        pass

    class InlineNoticeRequested(Message):
        def __init__(self, message: str, *, timeout: float | None = 4.0) -> None:
            self.message = message
            self.timeout = timeout
            super().__init__()

    class InlineNoticeCleared(Message):
        pass

    def __init__(
        self,
        command_registry: CommandRegistry,
        history_file: Path | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.input_widget: ChatTextArea | None = None
        self.prompt_widget: NoMarkupStatic | None = None
        self._command_registry = command_registry
        self._switching_mode = False

        if history_file:
            self.history = HistoryManager(history_file)
        else:
            self.history = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            self.prompt_widget = NoMarkupStatic(">", id="prompt")
            yield self.prompt_widget

            self.input_widget = ChatTextArea(
                id="input",
                command_registry=self._command_registry,
            )
            yield self.input_widget

    def on_mount(self) -> None:
        if self.input_widget:
            self.input_widget.focus()

    def _parse_mode_and_text(self, text: str) -> tuple[InputMode, str]:
        if text.startswith("/"):
            return "/", text[1:]
        else:
            return ">", text

    def _update_prompt(self) -> None:
        if not self.input_widget or not self.prompt_widget:
            return

        self.prompt_widget.update(self.input_widget.input_mode)

    def on_chat_text_area_mode_changed(self, event: ChatTextArea.ModeChanged) -> None:
        if self.prompt_widget:
            self.prompt_widget.update(event.mode)

    def _load_history_entry(self, text: str, cursor_col: int | None = None) -> None:
        if not self.input_widget:
            return

        mode, display_text = self._parse_mode_and_text(text)

        self.input_widget._navigating_history = True
        self.input_widget.set_mode(mode)
        self.input_widget.load_text(display_text)

        first_line = display_text.split("\n")[0]
        col = cursor_col if cursor_col is not None else len(first_line)
        cursor_pos = (0, col)

        self.input_widget.move_cursor(cursor_pos)
        self.input_widget._cursor_pos_after_load = cursor_pos
        self.input_widget._cursor_moved_since_load = False

        self._update_prompt()
        self._notify_completion_reset()

    def on_chat_text_area_history_previous(
        self, _event: ChatTextArea.HistoryPrevious
    ) -> None:
        if not self.input_widget:
            return

        if not self.history:
            return

        if not self.history.is_navigating():
            self.input_widget._original_text = self.input_widget.text

        previous = self.history.get_previous(self.input_widget._original_text)

        if previous is not None:
            self._load_history_entry(previous)

    def on_chat_text_area_history_next(self, _event: ChatTextArea.HistoryNext) -> None:
        if not self.input_widget:
            return

        if not self.history:
            return

        next_entry = self.history.get_next()
        if next_entry is not None:
            self._load_history_entry(next_entry)
            if not self.history.is_navigating():
                self.input_widget._cursor_pos_after_load = None
                self.input_widget._cursor_moved_since_load = False

    def on_chat_text_area_history_reset(
        self, _event: ChatTextArea.HistoryReset
    ) -> None:
        if self.history:
            self.history.reset_navigation()
        if self.input_widget:
            self.input_widget._original_text = ""
            self.input_widget._cursor_pos_after_load = None
            self.input_widget._cursor_moved_since_load = False

    def on_chat_text_area_submitted(self, event: ChatTextArea.Submitted) -> None:
        event.stop()

        if self._switching_mode:
            return

        if not self.input_widget:
            return

        value = event.value.strip()
        if value:
            if self.history:
                self.history.add(value)
                self.history.reset_navigation()
                self.run_worker(
                    partial(self.history.persist, value),
                    group="history_persist",
                    thread=True,
                )

            self.input_widget.clear_text()
            self._update_prompt()

            self._notify_completion_reset()

        self.post_message(self.Submitted(value))

    @property
    def switching_mode(self) -> bool:
        return self._switching_mode

    @switching_mode.setter
    def switching_mode(self, value: bool) -> None:
        self.set_switching_mode(value)

    def set_switching_mode(
        self, value: bool, *, show_indicator: bool | None = None
    ) -> None:
        self._switching_mode = value
        self._set_switching_indicator(
            value if show_indicator is None else show_indicator
        )

    def _set_switching_indicator(self, visible: bool) -> None:
        if visible:
            if self.prompt_widget:
                self.prompt_widget.display = False
            if not self.query(_PromptSpinner):
                self.query_one(Horizontal).mount(_PromptSpinner(), before=0)
        else:
            for spinner in self.query(_PromptSpinner):
                spinner.remove()
            if self.prompt_widget:
                self.prompt_widget.display = True
                self._update_prompt()

    @property
    def value(self) -> str:
        if not self.input_widget:
            return ""
        return self.input_widget.get_full_text()

    @value.setter
    def value(self, text: str) -> None:
        if self.input_widget:
            mode, display_text = self._parse_mode_and_text(text)
            self.input_widget.set_mode(mode)
            self.input_widget.load_text(display_text)
            self._update_prompt()

    def focus_input(self) -> None:
        if self.input_widget:
            self.input_widget.focus()

    def _notify_completion_reset(self) -> None:
        self.post_message(self.CompletionResetRequested())

    def replace_input(self, text: str, cursor_offset: int | None = None) -> None:
        if not self.input_widget:
            return

        self.input_widget.load_text(text)
        self.input_widget.reset_history_state()
        self._update_prompt()

        if cursor_offset is not None:
            self.input_widget.set_cursor_offset(max(0, min(cursor_offset, len(text))))

