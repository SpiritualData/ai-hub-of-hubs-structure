"""Chat message widgets for the hub's terminal screen. Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file cli/textual_ui/widgets/messages.py); modified from upstream: cut GreetingMessage, WhatsNewMessage, VscodeExtensionPromoMessage (and VSCODE_* constants), CustomToolsDeprecationMessage, TeleportUserMessage, HookRunContainer, HookSystemMessageLine, PlanFileMessage (file watching, editor suspend), FiredLoop support in UserMessage; "Vibe" wording replaced by "the AI"; imports rewritten."""

from __future__ import annotations

from enum import StrEnum, auto
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar, cast

from ..protocol.models import (
    FileImageSource,
    ImageAttachment,
    InlineImageSource,
)

if TYPE_CHECKING:
    from textual.widgets import Markdown
    from textual.widgets._markdown import MarkdownStream

    from ..chat_scroll import ChatScroll


from textual import events
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.content import Content
from textual.geometry import Size
from textual.widgets import Link, Static

from ..shortcut_hints import shortcut, shortcut_hint
from .collapsible import (
    ClickWithoutDragMixin,
    OverflowCollapsibleSection,
    lines_label,
)
from .no_markup_static import (
    NoMarkupStatic,
    NonSelectableStatic,
)
from .spinner import SpinnerMixin, SpinnerType
from .tool_widgets import clean_output


class ExpandingBorder(NonSelectableStatic):
    def __init__(self, *, classes: str | None = None) -> None:
        super().__init__(classes=classes)
        self._row_colors: dict[int, str] = {}

    def set_row_colors(self, colors: dict[int, str]) -> None:
        self._row_colors = colors
        self.refresh()

    # The border is always a single glyph column. Returning a constant avoids the
    # default measurement, which renders the widget (reading self.size) during
    # arrange and forces an O(N) compositor map rebuild on every layout pass.
    def get_content_width(self, container: Size, viewport: Size) -> int:
        return 1

    def render(self) -> Content | str:
        height = self.size.height
        chars = ["⎢"] * (height - 1) + ["⎣"]
        if not self._row_colors:
            return "\n".join(chars)

        rendered = Content("")
        for i, ch in enumerate(chars):
            if i > 0:
                rendered += Content("\n")
            if color := self._row_colors.get(i):
                rendered += Content.styled(ch, color)
            else:
                rendered += Content(ch)
        return rendered

    def on_resize(self) -> None:
        self.refresh()


# Mimic a border bottom with this component in order to have dimmed colors in ANSI themes
# Move back to border when Textual supports dimmed borders or foreground-muted in ANSI themes
class ExpandingSeparator(NonSelectableStatic):
    def render(self) -> str:
        return "─" * max(self.size.width, 1)

    def on_resize(self) -> None:
        self.refresh()


def _attachment_label(attachment: ImageAttachment) -> str:
    alias_path = Path(attachment.alias).expanduser()
    if not alias_path.is_absolute():
        return attachment.alias
    return _format_display_path(alias_path)


def _format_display_path(path: Path) -> str:
    home = Path.home()
    try:
        relative = path.relative_to(home)
    except ValueError:
        return str(path)
    if str(relative) == ".":
        return "~"
    return str(Path("~") / relative)


class UserMessageAttachment(Horizontal):
    def __init__(self, attachment: ImageAttachment) -> None:
        super().__init__(classes="user-message-attachment-line")
        self._attachment = attachment

    def compose(self) -> ComposeResult:
        yield NoMarkupStatic(
            "└ attached image: ", classes="user-message-attachment-label"
        )
        match self._attachment.source:
            case FileImageSource(path=path):
                image_path = Path(path)
                yield Link(
                    _attachment_label(self._attachment),
                    url=image_path.as_uri(),
                    classes="user-message-attachment-link",
                )
            case InlineImageSource():
                # Inline images have no file on disk, so there's nothing to link.
                yield NoMarkupStatic(
                    _attachment_label(self._attachment),
                    classes="user-message-attachment-link",
                )


class UserMessageSeverity(StrEnum):
    INFO = auto()
    WARNING = auto()
    ERROR = auto()


class UserMessage(Static):
    PROMPT_CHAR: ClassVar[str] = ">"
    SHOW_SEPARATOR: ClassVar[bool] = True

    def __init__(
        self,
        content: str,
        pending: bool = False,
        history_entry_id: str | None = None,
        images: list[ImageAttachment] | None = None,
        severity: UserMessageSeverity | None = None,
    ) -> None:
        super().__init__()
        self.add_class("user-message")
        self._content = content
        self._pending = pending
        self._images = images or []
        self.severity = severity
        self.history_entry_id = history_entry_id
        if severity is not None:
            self.add_class("user-message-severity")
            self.add_class(f"user-message-{severity.value}")

    def get_content(self) -> str:
        return self._content

    def update_content(self, content: str) -> None:
        self._content = content
        try:
            content_widget = self.query_one(".user-message-content", NoMarkupStatic)
            content_widget.update(content)
        except Exception:
            pass

    @property
    def pending(self) -> bool:
        return self._pending

    def compose(self) -> ComposeResult:
        with Vertical(classes="user-message-wrapper"):
            with Horizontal(classes="user-message-container"):
                if self.severity is None:
                    yield NonSelectableStatic(
                        f"{self.PROMPT_CHAR} ", classes="user-message-prompt"
                    )
                yield NoMarkupStatic(self._content, classes="user-message-content")
            if self._images:
                with Vertical(classes="user-message-attachments"):
                    for image in self._images:
                        yield UserMessageAttachment(image)
            if self.SHOW_SEPARATOR and self.severity is None:
                yield ExpandingSeparator(classes="user-message-separator")
            if self._pending:
                self.add_class("pending")

    @staticmethod
    def _attachment_label(attachment: ImageAttachment) -> str:
        return _attachment_label(attachment)

    @staticmethod
    def _format_display_path(path: Path) -> str:
        return _format_display_path(path)

    async def set_pending(self, pending: bool) -> None:
        if pending == self._pending:
            return

        self._pending = pending

        if pending:
            self.add_class("pending")
            return

        self.remove_class("pending")

    def set_show_separator(self, show: bool) -> None:
        self.set_class(not show, "no-separator")

    def set_follows_previous(self, follows: bool) -> None:
        self.set_class(follows, "follows-user")


class QueueHeaderMessage(Static):
    DEFAULT_LABEL = "» Queued"
    PAUSED_LABEL = f"» Queued: press {shortcut('Enter')} to send, type to add"

    def __init__(self, *, paused: bool = False) -> None:
        super().__init__()
        self.add_class("queue-header-message")
        self._paused = paused
        self._label_widget: NoMarkupStatic | None = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="queue-header-container"):
            self._label_widget = NoMarkupStatic(
                shortcut_hint(self._current_label()), classes="queue-header-content"
            )
            yield self._label_widget
            yield ExpandingSeparator(classes="queue-header-separator")

    def set_paused(self, paused: bool) -> None:
        if paused == self._paused:
            return
        self._paused = paused
        if self._label_widget is not None:
            self._label_widget.update(shortcut_hint(self._current_label()))

    def _current_label(self) -> str:
        return self.PAUSED_LABEL if self._paused else self.DEFAULT_LABEL


class SlashCommandMessage(UserMessage):
    PROMPT_CHAR = "/"
    SHOW_SEPARATOR = False

    def __init__(self, content: str, pending: bool = False) -> None:
        # content is the raw user input (e.g. "/clear"); the widget already
        # renders PROMPT_CHAR, so drop a leading slash to avoid "//clear".
        # Payload-path callers pass content without a slash (e.g. "model x").
        super().__init__(
            content[1:] if content.startswith("/") else content, pending=pending
        )
        self.add_class("slash-command-message")


class StreamingMessageBase(Static):
    def __init__(self, content: str) -> None:
        super().__init__()
        self._content = content
        self._markdown: Markdown | None = None
        self._stream: MarkdownStream | None = None
        self._content_initialized = False
        self._to_write_buffer = ""

    def _get_markdown(self) -> Markdown:
        if self._markdown is None:
            raise RuntimeError(
                "Markdown widget not initialized. compose() must be called first."
            )
        return self._markdown

    def _ensure_stream(self) -> MarkdownStream:
        if self._stream is None:
            from textual.widgets import Markdown

            self._stream = Markdown.get_stream(self._get_markdown())
        return self._stream

    def _is_chat_at_bottom(self) -> bool:
        try:
            chat = cast("ChatScroll", self.app.query_one("#chat"))
            return chat.is_at_bottom
        except Exception:
            return True

    async def append_content(self, content: str) -> None:
        if not content:
            return

        self._content += content

        if not self._should_write_content():
            return

        if self._is_chat_at_bottom():
            to_write = self._to_write_buffer + content
            self._to_write_buffer = ""
            stream = self._ensure_stream()
            await stream.write(to_write)
            return

        self._to_write_buffer += content

    async def write_initial_content(self) -> None:
        if self._content_initialized:
            return
        self._content_initialized = True
        if self._content and self._should_write_content():
            stream = self._ensure_stream()
            await stream.write(self._content)
            self._to_write_buffer = ""

    async def stop_stream(self) -> None:
        if self._to_write_buffer and self._should_write_content():
            stream = self._ensure_stream()
            await stream.write(self._to_write_buffer)
        self._to_write_buffer = ""

        if self._stream is None:
            return

        await self._stream.stop()
        self._stream = None

    def _should_write_content(self) -> bool:
        return True

    def get_content(self) -> str:
        return self._content

    def is_stripped_content_empty(self) -> bool:
        return self._content.strip() == ""


class AssistantMessage(StreamingMessageBase):
    def __init__(self, content: str) -> None:
        super().__init__(content)
        self.add_class("assistant-message")

    def compose(self) -> ComposeResult:
        from textual.widgets import Markdown

        markdown = Markdown("")
        self._markdown = markdown
        yield markdown


class ReasoningMessage(ClickWithoutDragMixin, SpinnerMixin, StreamingMessageBase):
    SPINNER_TYPE = SpinnerType.PULSE
    SPINNING_TEXT = "Thinking"
    COMPLETED_TEXT = "Thought"

    def __init__(
        self, content: str, collapsed: bool = True, *, completed: bool = False
    ) -> None:
        super().__init__(content)
        self.add_class("reasoning-message")
        self.collapsed = collapsed
        self._indicator_widget: Static | None = None
        self._header_widget: Horizontal | None = None
        self.init_spinner()
        self._is_spinning = not completed

    def compose(self) -> ComposeResult:
        with Vertical(classes="reasoning-message-wrapper"):
            self._header_widget = Horizontal(classes="reasoning-message-header")
            with self._header_widget:
                self._indicator_widget = NonSelectableStatic(
                    self._spinner.current_frame() if self._is_spinning else "■",
                    classes="reasoning-indicator",
                )
                yield self._indicator_widget
                self._status_text_widget = NoMarkupStatic(
                    self.SPINNING_TEXT if self._is_spinning else self.COMPLETED_TEXT,
                    classes="reasoning-collapsed-text",
                )
                yield self._status_text_widget
            from textual.widgets import Markdown

            markdown = Markdown("", classes="reasoning-message-content")
            markdown.display = not self.collapsed
            self._markdown = markdown
            yield markdown

    def on_mount(self) -> None:
        if self._is_spinning:
            self.start_spinner_timer()

    def on_resize(self) -> None:
        self.refresh_spinner()

    def stop_spinning(self, success: bool = True) -> None:
        super().stop_spinning(success)
        if self._indicator_widget:
            self._indicator_widget.remove_class("success", "error")
            self._indicator_widget.update("⏵" if self.collapsed else "⏷")

    def _is_click_on_toggle(self, event: events.Click) -> bool:
        return self._is_click_within(event, self._header_widget)

    async def on_click(self, event: events.Click) -> None:
        if self._click_is_passive(event):
            return
        await self._toggle_collapsed()

    async def _toggle_collapsed(self) -> None:
        await self.set_collapsed(not self.collapsed)

    def _should_write_content(self) -> bool:
        return not self.collapsed

    async def set_collapsed(self, collapsed: bool) -> None:
        if self.collapsed == collapsed:
            return

        self.collapsed = collapsed
        if self._indicator_widget and not self._is_spinning:
            self._indicator_widget.update("⏵" if collapsed else "⏷")
        if self._markdown:
            self._markdown.display = not collapsed
            if not collapsed and self._content:
                if self._stream is not None:
                    await self._stream.stop()
                    self._stream = None
                await self._markdown.update("")
                stream = self._ensure_stream()
                await stream.write(self._content)
                self._to_write_buffer = ""


class UserCommandMessage(Static):
    def __init__(self, content: str) -> None:
        super().__init__()
        self.add_class("user-command-message")
        self._content = content

    def compose(self) -> ComposeResult:
        from textual.widgets import Markdown

        with Horizontal(classes="user-command-container"):
            yield ExpandingBorder(classes="user-command-border")
            with Vertical(classes="user-command-content"):
                yield Markdown(self._content)


class InterruptMessage(Static):
    def __init__(self) -> None:
        super().__init__()
        self.add_class("interrupt-message")

    def compose(self) -> ComposeResult:
        with Horizontal(classes="interrupt-container"):
            yield ExpandingBorder(classes="interrupt-border")
            yield NoMarkupStatic(
                "Interrupted. What should the AI do instead?",
                classes="interrupt-content",
            )


class BashOutputMessage(ClickWithoutDragMixin, SpinnerMixin, Static):
    SPINNER_TYPE = SpinnerType.PULSE
    PREVIEW_LINES = 20

    def __init__(
        self,
        command: str,
        cwd: str,
        output: str = "",
        exit_code: int = 0,
        *,
        pending: bool = False,
    ) -> None:
        super().__init__()
        self.init_spinner()
        self.add_class("bash-output-message")
        self._command = command
        self._cwd = cwd
        self._output = output.rstrip("\n")
        self._exit_code = exit_code
        self._pending = pending
        self._output_widget: NoMarkupStatic | None = None
        self._overflow_widget: NoMarkupStatic | None = None
        self._section: OverflowCollapsibleSection | None = None
        self._output_container: Horizontal | None = None
        self._prompt_widget: NonSelectableStatic | None = None
        self._indicator_widget: Static | None = None

    def _clean_lines(self) -> list[str]:
        # Sanitize captured output (ANSI escapes, \r redraws, control bytes)
        # before splitting so it renders terminal-safe and line counts match.
        return clean_output(self._output).splitlines()

    def _preview_text(self) -> str:
        return "\n".join(self._clean_lines()[: self.PREVIEW_LINES])

    def _overflow_text(self) -> str:
        return "\n".join(self._clean_lines()[self.PREVIEW_LINES :])

    def _overflow_count(self) -> int:
        return max(0, len(self._clean_lines()) - self.PREVIEW_LINES)

    def _refresh_output_widgets(self) -> None:
        count = self._overflow_count()
        if self._output_widget:
            self._output_widget.update(self._preview_text())
        if self._overflow_widget:
            self._overflow_widget.update(self._overflow_text())
        if self._section:
            self._section.display = count > 0
            self._section.set_collapsed_label(lines_label(count, prefix="+"))

    def _update_spinner_frame(self) -> None:
        if not self._is_spinning or not self._prompt_widget:
            return
        # Frames are all the same size, so skip the relayout.
        self._prompt_widget.update(f"{self._spinner.next_frame()} ", layout=False)

    def on_mount(self) -> None:
        if self._pending:
            self.start_spinner_timer()

    @property
    def pending(self) -> bool:
        return self._pending

    def compose(self) -> ComposeResult:
        if self._pending:
            status_class = "bash-pending"
        elif self._exit_code != 0:
            status_class = "bash-error"
        else:
            status_class = "bash-success"
        self.add_class(status_class)
        if self._pending:
            prompt_text = f"{self._spinner.current_frame()} "
        else:
            prompt_text = "$ "
        with Horizontal(classes="bash-command-line"):
            self._prompt_widget = NonSelectableStatic(
                prompt_text, classes=f"bash-prompt {status_class}"
            )
            yield self._prompt_widget
            yield NoMarkupStatic(self._command, classes="bash-command")
        if not self._pending:
            count = self._overflow_count()
            self._output_widget = NoMarkupStatic(
                self._preview_text(), classes="bash-output"
            )
            self._overflow_widget = NoMarkupStatic(
                self._overflow_text(), classes="bash-output"
            )
            self._section = OverflowCollapsibleSection(
                self._overflow_widget, collapsed_label=lines_label(count, prefix="+")
            )
            self._section.display = count > 0
            self._output_container = Horizontal(classes="bash-output-container")
            with self._output_container:
                yield ExpandingBorder(classes="bash-output-border")
                with Vertical(classes="bash-output-body"):
                    yield self._output_widget
                    yield self._section

    async def on_click(self, event: events.Click) -> None:
        if self._click_is_passive(event):
            return
        if self._section and self._overflow_count() > 0:
            self._section.toggle()

    async def _ensure_output_container(self) -> None:
        if self._output_container is not None:
            return
        self._output_widget = NoMarkupStatic("", classes="bash-output")
        self._overflow_widget = NoMarkupStatic("", classes="bash-output")
        self._section = OverflowCollapsibleSection(
            self._overflow_widget, collapsed_label=lines_label(0, prefix="+")
        )
        self._section.display = False
        self._output_container = Horizontal(
            ExpandingBorder(classes="bash-output-border"),
            Vertical(self._output_widget, self._section, classes="bash-output-body"),
            classes="bash-output-container",
        )
        await self.mount(self._output_container)

    async def append_output(self, text: str) -> None:
        await self._ensure_output_container()
        self._output += text
        self._refresh_output_widgets()

    async def finish(self, exit_code: int, *, interrupted: bool = False) -> None:
        self._exit_code = exit_code
        self._pending = False
        self.stop_spinning()
        if self._prompt_widget:
            self._prompt_widget.update("$ ")
        if interrupted:
            new_class = "bash-interrupted"
        elif exit_code != 0:
            new_class = "bash-error"
        else:
            new_class = "bash-success"
        self.remove_class("bash-pending")
        self.add_class(new_class)
        if self._prompt_widget:
            self._prompt_widget.remove_class("bash-pending")
            self._prompt_widget.add_class(new_class)
        if interrupted:
            suffix = (
                "\n(interrupted)"
                if self._output and not self._output.endswith("\n")
                else "(interrupted)"
            )
            self._output += suffix
        if not self._output:
            self._output = "(no output)"
        await self._ensure_output_container()
        self._refresh_output_widgets()


class ErrorMessage(Static):
    def __init__(
        self, error: str | Content, collapsed: bool = False, show_border: bool = True
    ) -> None:
        super().__init__()
        self.add_class("error-message")
        self._error = error
        self.collapsed = collapsed
        self._show_border = show_border
        self._content_widget: Static | None = None

    def compose(self) -> ComposeResult:
        with Horizontal(classes="error-container"):
            if self._show_border:
                yield ExpandingBorder(classes="error-border")
            error = (
                self._error
                if isinstance(self._error, Content)
                else Content(clean_output(self._error))
            )
            text = Content("Error: ") + error if self._show_border else error
            self._content_widget = NoMarkupStatic(text, classes="error-content")
            yield self._content_widget

    def set_collapsed(self, collapsed: bool) -> None:
        pass


class WarningMessage(Static):
    def __init__(self, message: str, show_border: bool = True) -> None:
        super().__init__()
        self.add_class("warning-message")
        self._message = message
        self._show_border = show_border

    def compose(self) -> ComposeResult:
        with Horizontal(classes="warning-container"):
            if self._show_border:
                yield ExpandingBorder(classes="warning-border")
            yield NoMarkupStatic(self._message, classes="warning-content")
