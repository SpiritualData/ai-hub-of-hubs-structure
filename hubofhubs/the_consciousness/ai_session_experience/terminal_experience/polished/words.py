"""The words the polished terminal shows a person, merged into the terminal's one string table (``strings.EN``) when this module is imported.

Every sentence a person reads on the polished screen is a key here and is said with ``say``: a consumer changes the wording with ``strings.register_overrides`` and
the screen shows no raw key and no internal name. Plural forms are ``key_one`` and ``key_other`` and ``{{name}}`` marks a value. Standard library and the strings module only.
"""
from __future__ import annotations

from hubofhubs.the_consciousness.ai_session_experience.terminal_experience import strings

WORDS = {
    # the prompt: what typing does now, short enough to be drawn whole at 80 columns
    "polished.prompt.ready": "Type a goal… Enter=send, {{newline}}, /help",
    "polished.prompt.busy": "Type to add a note for the AI. Esc stops the work.",
    "polished.prompt.asking": "Type y to approve or n to refuse…",
    "polished.prompt.stopped": "Type resume to continue. /quit leaves.",
    "polished.prompt.newline": "Shift+Enter or Ctrl+J=newline",
    "polished.prompt.newlineVte": "Ctrl+J or Alt+Enter=newline",
    # the key line under the prompt: whole hints only
    "polished.key.stop": "Stop",
    "polished.key.details": "Details",
    "polished.key.nextRun": "Next run",
    "polished.key.structure": "Structure",
    "polished.key.resume": "Resume",
    "polished.key.scroll": "Scroll",
    "polished.key.quit": "Quit",
    "polished.key.answer": "Answer",
    # the activity bar
    "polished.activity.working": "Working…",
    "polished.activity.stopping": "Stopping…",
    "polished.activity.waiting": "Waiting for your answer",
    "polished.activity.read": "Reading {{label}}",
    "polished.activity.edit": "Changing {{label}}",
    "polished.activity.run": "Running {{label}}",
    "polished.activity.check": "Checking {{label}}",
    "polished.activity.tool": "Using {{label}}",
    "polished.activity.delegate": "Handing off {{label}}",
    "polished.activity.note": "Working on {{label}}",
    "polished.activity.waitingNotes_one": "{{count}} message waiting",
    "polished.activity.waitingNotes_other": "{{count}} messages waiting",
    "polished.activity.newBelow": "↓ new output below",
    # the work panel and its detail
    "polished.work.untitled": "The work",
    "polished.work.running": "running",
    "polished.work.asking": "waiting for your answer",
    "polished.work.stopping": "stopping",
    "polished.work.open": "Alt+D or click for details",
    "polished.work.openMany": "Alt+D or click for details, Tab for the next run",
    "polished.work.detailTitleMany": "run {{position}} of {{total}}: {{title}}",
    "polished.work.detailTitle": "{{title}}",
    "polished.work.detailNav": "PgUp/PgDn to scroll, Alt+D to close",
    "polished.work.detailNavMany": "PgUp/PgDn to scroll, Tab for the next run, Alt+D to close",
    "polished.work.detailFollowing": "following the newest step",
    "polished.work.detailPaused": "scrolled back: PgDn to the end follows again",
    "polished.work.metrics": "Metric results",
    "polished.work.structureHidden": "structure (Alt+T hides)",
    # what the person typed while the AI worked
    "polished.note.echo": "you: {{text}}",
    "polished.note.pickedUp_one": "Your note was taken up.",
    "polished.note.pickedUp_other": "Your {{count}} notes were taken up.",
    "polished.note.flushed_one": "Sending your {{count}} waiting note as the next message.",
    "polished.note.flushed_other": "Sending your {{count}} waiting notes as one message.",
    "polished.note.back_one": "Your note is back in the box. Send it with your answer or clear it.",
    "polished.note.back_other": "Your {{count}} notes are back in the box. Send them with your answer or clear them.",
    "polished.note.heldStopped": "stopped",
    # keys: copy, stop, quit
    "polished.ctrlc.copied": "Copied: {{preview}}",
    "polished.ctrlc.stopped": "Stopped. Press Ctrl+C again to quit.",
    "polished.ctrlc.idle": "Press Ctrl+C again to quit.",
    "polished.copy.nothing": "Nothing to copy yet",
    "polished.copy.last": "Last reply · {{detail}}",
    "polished.copy.selection_one": "{{count}} character · {{detail}}",
    "polished.copy.selection_other": "{{count}} characters · {{detail}}",
    "polished.copy.clipboard": "clipboard",
    "polished.copy.sent": "sent to terminal (if paste fails, install wl-clipboard or xclip)",
    "polished.copy.title": "Copy",
    "polished.copy.titleDone": "Copied",
    # the closing line: one shape for every run
    "polished.closing.met": "Done: the goal was met",
    "polished.closing.unmet": "Finished: the goal was not met",
    "polished.closing.stopped": "Stopped: your work is kept",
    "polished.closing.failed": "Failed",
    "polished.closing.callsOne": "{{count}} call",
    "polished.closing.callsOther": "{{count}} calls",
    # warnings folded to one short line
    "polished.notice.line": "⚠ {{text}}",
    "polished.notice.more_one": "{{count}} more notice. Details: {{where}}",
    "polished.notice.more_other": "{{count}} more notices. Details: {{where}}",
    "polished.notice.details": "Details: {{where}}",
    "polished.notice.detailsVerbose": "Details: run with -v",
    # the command menu
    "polished.menu.complete": "(Tab completes)",
    "polished.command.help": "show or hide the list of keys",
    "polished.command.resume": "continue the run that was stopped",
    "polished.command.stop": "stop one helper and keep the rest going",
    "polished.command.tree": "show or hide the structure of the work",
    "polished.command.open": "open one solution's fields in the structure",
    "polished.command.close": "close one solution in the structure",
    "polished.command.who": "show who the AI acts for and the authority in force",
    "polished.command.clear": "clear the screen (the session is kept)",
    "polished.command.quit": "leave (Ctrl+D too)",
    "polished.command.custom": "a command of this build",
    "polished.command.harness": "show or switch which worker does the work (a new session starts)",
    "polished.command.new": "start a new session with the same worker",
    "polished.command.session": "show the session id",
    "polished.help.rows.esc": "Esc: stop the run and keep the session",
    "polished.help.rows.type": "Type and Enter: add a note; @name text steers one helper, /stop name stops one",
    "polished.help.rows.answer": "y or n: answer a question the run asks",
    "polished.help.rows.panel": "Alt+D: open the run's full history; Tab picks the next run",
    "polished.help.rows.structure": "Alt+T: show or hide the structure of the work",
    "polished.help.rows.copy": "Drag to select and Ctrl+C copies; Alt+Y copies the last reply",
    # the screen's own start and end
    "polished.screen.title": "AI Hub of Hubs Structure",
    "polished.screen.intro": "Type a goal and press Enter; it runs in this folder. /help lists commands.",
    "polished.screen.cleared": "The screen is cleared; the session is kept.",
    "polished.screen.starting": "starting",
}


def register() -> None:
    """Merge the polished words into the shared table (idempotent). A consumer's registered overrides still win over these defaults."""
    strings.EN.update(WORDS)


register()


def say(key: str, /, **params: object) -> str:
    """The polished sentence for ``key`` (the terminal's ``strings.say``, with these words present)."""
    return strings.say(key, None, **params)


__all__ = ["WORDS", "register", "say"]
