"""The binding layer: a thin Textual application that composes the widgets of the adopted screen (the vendored Mistral Vibe interface) the way its own application does, and is driven by the
adapter's events. The widgets are not rewritten: this file only lays them out, hands each typed entry to the vendored event handler, mounts the hub's own rows (the goal as the person's message,
a note sent and taken up, quiet hub lines, the closing), swaps the input for the approval or question screen, and turns keys into the shared driver's key tokens (``esc``, ``line``, ``tree``,
``help``, ``interrupt``, ``eof``). Textual and the vendored widgets are imported inside ``make_app``, so importing this module needs neither."""
from __future__ import annotations

import queue
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.adopted_session import adapter as hub

HUB_CSS = """
* { scrollbar-color: #6cb6ff; scrollbar-color-hover: #8fcbff; scrollbar-color-active: #8fcbff; scrollbar-background: #1c1c1c; scrollbar-background-hover: #1c1c1c; scrollbar-background-active: #1c1c1c; }
Screen .collapsible-toggle.header .collapsible-header-verb, Screen .tool-call-header.running.collapsible-result .collapsible-header-verb { text-opacity: 100%; }
#hub-header { height: 1; width: 100%; padding: 0 1; background: $surface; color: $text; text-style: bold; }
#hub-structure { height: auto; width: 100%; padding: 0 1; color: $text-muted; }
#hub-structure.empty { display: none; }
#hub-help { height: auto; width: 100%; padding: 0 1; color: $text-muted; }
#hub-help.empty { display: none; }
#bottom-bar { height: 1; width: 100%; padding: 0 1; }
#hub-hint { width: 1fr; height: 1; color: $text-muted; }
#hub-status { width: auto; height: 1; color: $text-muted; }
.hub-note { width: 100%; height: auto; padding: 0 1; color: $text-muted; }
.hub-note-stopping, .hub-note-stopped { color: $warning; }
.hub-detail { width: 100%; height: auto; padding: 0 1; color: $text-muted; }
.hub-outcome { width: 100%; height: auto; padding: 0 1; text-style: bold; }
.hub-outcome-met, .hub-outcome-finished { color: $success; }
.hub-outcome-unmet, .hub-outcome-stopped { color: $warning; }
.hub-outcome-failed { color: $error; }
.hub-resume-lead { width: 100%; height: auto; padding: 0 1; margin-top: 1; color: $text-muted; }
.hub-resume { width: 100%; height: auto; padding: 0 1; text-style: bold; }
"""


#: The hub's colours for the adopted screen. Upstream draws with the terminal's own palette (an ANSI theme), whose contrast cannot be known; these are fixed values with informative
#: text at 4.5 to 1 or more on the dark default (the scrollbar and rules 3 to 1), so the screen reads the same on every terminal.
THEME_COLORS = dict(primary="#6cb6ff", secondary="#8fb8e8", warning="#ffb454", error="#ff7b7b", success="#5fd787", accent="#ffb454", foreground="#e6e6e6", background="#0d0d0d",
                    surface="#1c1c1c", panel="#262626")


def css_path() -> str:
    """The vendored screen's stylesheet (kept whole, as upstream ships it)."""
    return str(Path(__file__).resolve().parent.parent / "vendor" / "mistral_vibe_ui" / "app.tcss")


def make_app(history_file: Any = None, theme: str = "hub-dark") -> Any:
    """The application, built when it is needed (Textual and the vendored widgets are imported here and nowhere else)."""
    from rich.text import Text
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, VerticalGroup
    from textual.screen import Screen
    from textual.theme import Theme
    from textual.widget import Widget
    from textual.widgets import Static

    from ..vendor.mistral_vibe_ui.chat_scroll import ChatScroll
    from ..vendor.mistral_vibe_ui.commands import CommandRegistry
    from ..vendor.mistral_vibe_ui.handlers.event_handler import EventHandler
    from ..vendor.mistral_vibe_ui.protocol.models import ApprovalCallbackDetail, UserInputCallbackDetail
    from ..vendor.mistral_vibe_ui.widgets.approval_app import ApprovalApp
    from ..vendor.mistral_vibe_ui.widgets.chat_input import ChatInputContainer
    from ..vendor.mistral_vibe_ui.widgets.chat_input.subagent_list import SubagentList
    from ..vendor.mistral_vibe_ui.widgets.collapsible import CollapsibleSection
    from ..vendor.mistral_vibe_ui.widgets.inline_notice import InlineNotice
    from ..vendor.mistral_vibe_ui.widgets.loading import LoadingWidget
    from ..vendor.mistral_vibe_ui.widgets.messages import AssistantMessage, StreamingMessageBase, UserMessage
    from ..vendor.mistral_vibe_ui.widgets.no_markup_static import NoMarkupStatic
    from ..vendor.mistral_vibe_ui.widgets.question_app import QuestionApp
    from ..vendor.mistral_vibe_ui.widgets.subagent_transcripts import SubagentTranscripts
    from ..vendor.mistral_vibe_ui.widgets.todo_status import TodoStatusRow
    from ..vendor.mistral_vibe_ui.widgets.tools import ToolGroup
    from ..vendor.mistral_vibe_ui.word_selection import WordSelectScreen

    class HubUserMessage(UserMessage):
        """The person's own message, drawn with the hub's prompt glyph."""
        PROMPT_CHAR = "❯"

    class HubApproval(ApprovalApp):
        """The adopted approval screen with the two answers the hub's contract has: approve or refuse."""

        def _build_options(self) -> List[Any]:
            return [("Approve", "yes", "once", None), ("Refuse", "no", "deny", None)]

        def compose(self) -> ComposeResult:
            yield from super().compose()
            if self.help_widget is not None:
                self.help_widget.update("y approve  n refuse  Esc stop")

        def _recompute_height(self) -> None:
            """Upstream sizes the box from the options, the title and the tool info; the reason row (here the question) and the border are part of it too, or what will change is cut off."""
            options = self.query_one("#approval-options")
            scroll = self.query_one(".approval-tool-info-scroll")
            natural = options.outer_size.height + self.title_widget.outer_size.height + (1 if self.reason else 0) + scroll.virtual_size.height + 3       # +3: the border, and the row of margin above the tool info that the scroll's own size leaves out
            self.styles.height = min(natural, max(int(self.app.size.height * 0.7), 8))

    class HubApp(App):
        ENABLE_COMMAND_PALETTE = False
        CSS_PATH = css_path()
        CSS = HUB_CSS
        BINDINGS = [Binding("escape", "stop", "Stop", show=False, priority=True), Binding("ctrl+c", "interrupt", "Stop", show=False, priority=True),
                    Binding("ctrl+d", "leave", "Leave", show=False, priority=True), Binding("ctrl+o", "toggle_tool", "Tool output", show=False),
                    Binding("tab", "structure", "Structure", show=False, priority=True)]

        def __init__(self) -> None:
            super().__init__()
            self.press: Optional[Callable[..., None]] = None
            self.attendance: Any = None
            self.start_hook: Callable[[], None] = lambda: None
            self.lines: "queue.Queue[Optional[str]]" = queue.Queue()
            self.drawing: "queue.Queue[Any]" = queue.Queue()
            self.ended = False
            self.history_file = history_file
            self.commands = CommandRegistry()
            self.event_handler: Optional[EventHandler] = None
            self.loading: Any = None
            self.helpers: Dict[str, Any] = {}
            self.viewed: Optional[str] = None
            self.tools_collapsed = False
            self.notes: Dict[str, Any] = {}
            self.waiting_notes: List[Any] = []
            self.open_ask = ""
            self.reading = False

        # --- the layout: the upstream application's, with a header and a hub key line ---------------------------------------------------

        def get_default_screen(self) -> Screen:
            return WordSelectScreen(id="_default")

        def compose(self) -> ComposeResult:
            yield NoMarkupStatic("", id="hub-header")
            yield NoMarkupStatic("", id="hub-structure", classes="empty")
            with ChatScroll(id="chat"):
                yield VerticalGroup(id="messages")
                yield SubagentTranscripts(id="subagent-transcripts")
            yield NoMarkupStatic("", id="hub-help", classes="empty")
            with Horizontal(id="loading-area"):
                yield Static(id="loading-area-content")
                yield InlineNotice(id="inline-notice")
            with Static(id="bottom-app-container"):
                yield ChatInputContainer(command_registry=self.commands, history_file=self.history_file, id="input-container")
            yield TodoStatusRow()
            with Horizontal(id="bottom-bar"):
                yield NoMarkupStatic("", id="hub-hint")
                yield NoMarkupStatic("", id="hub-status")

        def on_mount(self) -> None:
            if theme == "hub-dark":
                self.register_theme(Theme(name="hub-dark", dark=True, **THEME_COLORS))
            self.theme = theme
            self.event_handler = EventHandler(mount_callback=self.mount_and_scroll, get_tools_collapsed=lambda: self.tools_collapsed)
            self.query_one(ChatInputContainer).focus_input()
            threading.Thread(target=self.pump, daemon=True).start()
            self.ready_timer = self.set_interval(0.02, self.check_ready)       # the run starts once the screen has its first layout: entries mounted before it make the layout chase its own size

        def check_ready(self) -> None:
            if self.query_one("#chat").size.height > 0 and self.query_one(ChatInputContainer).size.height > 0:
                self.ready_timer.stop()
                self.set_timer(0.1, self.start_hook)        # a short beat after it: entries applied in the very tick of the first layout make it chase its own size (seen: a full-screen render loop)

        def on_unmount(self) -> None:
            self.ended = True
            self.drawing.put(None)
            self.lines.put(None)

        def open_url(self, url: str, *, new_tab: bool = True) -> None:
            """The hub opens no browser: a link in the transcript is shown, never followed."""

        # --- drawing calls from the driver's thread, applied in order on the screen's loop ---------------------------------------------------

        add_line = None      # the screen draws from typed entries; the plain transcript is the arm's buffer, so the harness of the presentation metric is handed no line writer

        def post(self, function: Callable[..., Any], *args: Any) -> None:
            if not self.ended:
                self.drawing.put((function, args))

        def settle(self, seconds: float = 5.0) -> None:
            """Return once every drawing call posted so far has been applied (the driver calls it before the application is closed, so the closing is on the screen)."""
            done = threading.Event()
            self.post(done.set)
            if not self.ended:
                done.wait(seconds)

        def pump(self) -> None:
            """Apply the posted drawing calls in order. The entries that wait together (a helper's burst of events) are applied in one call and one screen update, so the screen is never
            further behind the run than the time one batch takes."""
            after: List[Any] = []        # the call that ended a batch, applied next
            while True:
                item = after.pop() if after else self.drawing.get()
                if item is None:
                    return
                if item[0] == self.apply:
                    merged = list(item[1][0])
                    while True:
                        try:
                            more = self.drawing.get_nowait()
                        except queue.Empty:
                            break
                        if more is not None and more[0] == self.apply:
                            merged.extend(more[1][0])
                        else:
                            after.append(more)
                            break
                    item = (self.apply, (merged,))
                try:
                    self.call_from_thread(item[0], *item[1])
                except Exception:  # noqa: BLE001 -- a screen that is gone is not the run's failure
                    if self.ended:
                        return

        async def mount_and_scroll(self, widget: Widget, after: Optional[Widget] = None, before: Optional[Widget] = None, *, container: Optional[Widget] = None) -> None:
            """Where the upstream application mounts a message: after or before a sibling, in a container, or at the end of the transcript, and keeps the newest row in view."""
            chat, area = self.query_one("#chat", ChatScroll), self.query_one("#messages")
            anchor = isinstance(widget, UserMessage) or chat.is_at_bottom
            if isinstance(widget, ToolGroup):
                widget.set_collapsed(self.tools_collapsed)       # open from the first frame: each step is a row a person can read as it happens (Ctrl+O folds them)
            with self.batch_update():
                if before is not None and isinstance(before.parent, Widget):
                    await before.parent.mount(widget, before=before)
                elif after is not None and isinstance(after.parent, Widget):
                    await after.parent.mount(widget, after=after)
                elif container is not None:
                    await container.mount(widget)
                else:
                    await area.mount(widget)
                if widget.is_mounted and isinstance(widget, StreamingMessageBase):
                    await widget.write_initial_content()
            if anchor:
                chat.anchor()

        async def apply(self, items: List[Any]) -> None:
            with self.batch_update():
                for item in items:
                    await self.dispatch(item)
            if self.viewed is not None:
                await self.refresh_child(self.viewed)

        async def dispatch(self, item: Any) -> None:
            events = hub.vendored().events
            handler = self.event_handler
            if isinstance(item, (events.HistoryEntryAdded, events.HistoryEntryUpdated)):
                await self.ensure_loading()
                if handler is not None:
                    await handler.handle_event(item, self.loading)
            elif isinstance(item, events.ChildSessionUpdated):
                self.helpers[item.child_session.id] = item.child_session
                self.refresh_children()
            elif isinstance(item, events.CallbackRequested):
                await self.show_callback(item.callback)
            elif isinstance(item, hub.GoalSent):
                await self.ensure_loading()
                await self.mount_and_scroll(HubUserMessage(item.text))
            elif isinstance(item, hub.NoteSent):
                await self.note_sent(item)
            elif isinstance(item, hub.NoteTakenUp):
                await self.note_taken_up(item)
            elif isinstance(item, hub.HubLine):
                await self.mount_and_scroll(NoMarkupStatic(item.text, classes=f"hub-note hub-note-{item.kind}"))
            elif isinstance(item, hub.AskClosed):
                await self.close_ask(item.ask_id)
            elif isinstance(item, hub.Closing):
                await self.close_run(item)

        # --- the run: the loading line, the transcript, a note sent, the closing --------------------------------------------------------------

        async def ensure_loading(self) -> None:
            if self.loading is not None and self.loading.parent is not None:
                return
            self.loading = LoadingWidget(status="Working", show_hint=False)      # the key line says what Esc does, once, and the header carries the clock
            await self.query_one("#loading-area-content").mount(self.loading)

        async def remove_loading(self) -> None:
            if self.loading is not None and self.loading.parent is not None:
                await self.loading.remove()
            self.loading = None

        async def note_sent(self, item: Any) -> None:
            """A note typed while the AI works: the person's own line, once, marked as queued until the harness takes it up."""
            widget = HubUserMessage(f"{item.text}  (queued: read after the current step)", pending=True)
            self.notes[item.message_id] = (widget, item.text)
            self.waiting_notes.append(item.message_id)
            await self.mount_and_scroll(widget)

        async def note_taken_up(self, item: Any) -> None:
            key = item.message_id if item.message_id in self.notes else (self.waiting_notes[0] if self.waiting_notes else "")
            if not key or key not in self.notes:
                return
            widget, text = self.notes.pop(key)
            if key in self.waiting_notes:
                self.waiting_notes.remove(key)
            widget.update_content(f"{text}  (taken up)")
            await widget.set_pending(False)

        async def close_run(self, closing: Any) -> None:
            """The end of a run: the answer once (markdown), the quiet detail, one outcome line and the command that resumes, alone on its own line."""
            await self.remove_loading()
            if self.event_handler is not None:
                await self.event_handler.finalize_streaming()
                self.event_handler.stop_current_tool_call(success=closing.state in ("met", "finished"), cancelled=closing.state == "stopped")
            if closing.answer:
                message = AssistantMessage(closing.answer)
                await self.mount_and_scroll(message)
                await message.stop_stream()
            if closing.detail:
                await self.mount_and_scroll(NoMarkupStatic("\n".join(closing.detail), classes="hub-detail"))
            if closing.outcome:
                await self.mount_and_scroll(NoMarkupStatic("\n".join(closing.outcome), classes=f"hub-outcome hub-outcome-{closing.state}"))
            if closing.resume:
                await self.mount_and_scroll(NoMarkupStatic(closing.resume[0], classes="hub-resume-lead"))
                for row in closing.resume[1:]:
                    await self.mount_and_scroll(NoMarkupStatic(row, classes="hub-resume"))

        # --- the bottom: input, approval, question --------------------------------------------------------------------------------------------

        async def show_callback(self, callback: Any) -> None:
            """A question from the run: the approval screen (approve or refuse, with what will change) or a question screen, in place of the input."""
            await self.ensure_loading()
            if self.loading is not None:
                self.loading.begin_action_required("Waiting for you")
            self.open_ask = callback.callback_id
            detail = callback.detail
            if isinstance(detail, ApprovalCallbackDetail):
                widget: Widget = HubApproval(effect=detail.effect, reason=detail.reason)
            elif isinstance(detail, UserInputCallbackDetail):
                widget = QuestionApp(args=detail.request)
            else:
                return
            container = self.query_one("#bottom-app-container")
            self.query_one(ChatInputContainer).display = False
            self.query_one(ChatInputContainer).disabled = True
            for stale in list(self.query("#approval-app, #question-app")):
                await stale.remove()
            await container.mount(widget)
            self.call_after_refresh(widget.focus)
            self.query_one("#chat", ChatScroll).anchor()

        async def close_ask(self, ask_id: str) -> None:
            for stale in list(self.query("#approval-app, #question-app")):
                await stale.remove()
            self.open_ask = ""
            if self.loading is not None and self.loading.parent is not None:
                self.loading.end_action_required()
            box = self.query_one(ChatInputContainer)
            box.disabled = False
            box.display = True
            self.call_after_refresh(box.focus_input)

        def answer(self, word: str) -> None:
            if self.press is not None:
                self.press("line", word)

        def on_approval_app_approval_granted(self, message: Any) -> None:
            self.answer("y")

        def on_approval_app_approval_rejected(self, message: Any) -> None:
            self.answer("n")

        def on_question_app_answered(self, message: Any) -> None:
            first = message.answers[0].answer if message.answers else ""
            asked = self.attendance.adapter.options_of(self.open_ask) if self.attendance is not None else ()
            self.answer("y" if asked and first == asked[0] else "n")

        def on_question_app_cancelled(self, message: Any) -> None:
            self.answer("n")

        # --- sub-agents: the status list under the input and the transcript of one helper -------------------------------------------------

        def refresh_children(self) -> None:
            if not self.is_mounted:
                return
            self.query_one(SubagentList).update_sessions(tuple(self.helpers.values()), selected_session_id=self.viewed)

        async def on_subagent_list_selected(self, event: Any) -> None:
            transcripts = self.query_one(SubagentTranscripts)
            area = self.query_one("#messages")
            if event.session_id is None:
                self.viewed = None
                transcripts.select(None)
                area.display = True
                self.query_one(ChatInputContainer).set_subagent_view(False)
            else:
                self.viewed = event.session_id
                area.display = False
                if not transcripts.select(event.session_id):
                    await transcripts.prepare(event.session_id)
                    transcripts.select(event.session_id)
                self.query_one(ChatInputContainer).set_subagent_view(True)
                await self.refresh_child(event.session_id)
            self.refresh_children()

        async def refresh_child(self, session_id: str) -> None:
            if self.attendance is None:
                return
            history = self.attendance.adapter.history_for(session_id)
            await self.query_one(SubagentTranscripts).replace_history(session_id, history, tools_collapsed=self.tools_collapsed, show_thinking=True, history_complete=True)

        # --- figures: the header, the key line, the status line, the structure ----------------------------------------------------------------

        def set_figures(self, figures: Any) -> None:
            if not self.is_mounted:
                return
            self.query_one("#hub-header", NoMarkupStatic).update(Text(figures.header))
            self.query_one("#hub-hint", NoMarkupStatic).update(Text(figures.hint))
            self.query_one("#hub-status", NoMarkupStatic).update(Text(figures.status))
            structure = self.query_one("#hub-structure", NoMarkupStatic)
            structure.update(Text("\n".join(figures.structure)))
            structure.set_class(not figures.structure, "empty")
            helps = self.query_one("#hub-help", NoMarkupStatic)
            helps.update(Text("\n".join(figures.help)))
            helps.set_class(not figures.help, "empty")

        # --- keys ------------------------------------------------------------------------------------------------------------------------------

        def send(self, token: str, text: str = "") -> None:
            if self.press is not None:
                self.press(token, text)

        def action_stop(self) -> None:
            if self.viewed is not None:
                self.viewed = None
                self.post(self.show_main)
                return
            self.send("esc")

        async def show_main(self) -> None:
            await self.on_subagent_list_selected(SubagentList.Selected(None))

        def action_interrupt(self) -> None:
            if self.press is not None:
                self.send("interrupt")
            else:
                self.lines.put(None)

        def action_leave(self) -> None:
            if self.press is not None:
                self.send("eof")
            self.lines.put(None)

        def action_structure(self) -> None:
            self.send("tree")

        def check_action(self, action: str, parameters: tuple) -> Optional[bool]:
            if action == "structure":
                box = self.query_one(ChatInputContainer)
                return not box.value.startswith("/")     # Tab completes a slash command in the input, and shows the structure anywhere else
            return True

        async def action_toggle_tool(self) -> None:
            self.tools_collapsed = not self.tools_collapsed
            for section in self.query(CollapsibleSection):
                section.set_collapsed(self.tools_collapsed)
            for group in self.query(ToolGroup):
                group.set_collapsed(self.tools_collapsed)

        def on_chat_input_container_submitted(self, event: Any) -> None:
            text = event.value.strip()
            if not text:
                return
            parsed = self.commands.parse_command(text)
            if parsed is not None:
                self.run_command(parsed[1].handler)
            elif self.press is not None:
                self.send("line", text)
            else:
                self.lines.put(text)

        def run_command(self, handler: str) -> None:
            if handler == "_stop_turn":
                self.send("esc")
            elif handler == "_resume_turn":
                self.send("line", "resume")
            elif handler == "_show_who":
                self.send("who")
            elif handler == "_show_structure":
                self.send("tree")
            elif handler == "_show_help":
                self.send("help")
            elif handler == "_exit_app":
                if self.press is not None:
                    self.send("line", "/quit")
                self.lines.put(None)

        def set_prompt(self, text: str) -> None:
            self.post(lambda: setattr(self.query_one(ChatInputContainer), "value", ""))

        def read(self, prompt: str) -> Optional[str]:
            """One typed line, for the interactive command between runs."""
            self.reading = True
            try:
                return self.lines.get()
            finally:
                self.reading = False

    return HubApp()
