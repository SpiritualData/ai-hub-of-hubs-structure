"""The full-screen client's own closing text is left out; everything else passes byte for byte."""
from hubofhubs.the_consciousness.ai_session_experience.opencode_server.terminal_run import ExitTextFilter, run_full_screen

EXIT = b"\x1b[?1049l\x1b[?2031l\x1b]0;\x07\x1b[0 q\x1b[?25h"
FOOTER = b"   \x1b[0m\xe2\x96\x84\r\n  \x1b[90mContinue  \x1b[0m\x1b[1mopencode -s ses_x\x1b[0m\r\n"


def test_the_screen_and_the_cursor_restore_pass_and_the_clients_closing_text_is_dropped():
    assert ExitTextFilter().feed(b"draw" + EXIT + FOOTER) == b"draw" + EXIT


def test_it_holds_across_chunk_boundaries():
    filtered, out = ExitTextFilter(), b""
    data = b"draw" + EXIT + FOOTER
    for i in range(0, len(data), 3):
        out += filtered.feed(data[i:i + 3])
    assert out == b"draw" + EXIT


def test_output_before_the_client_leaves_the_screen_is_never_touched():
    assert ExitTextFilter().feed(b"  plain text  \x1b[1mbold\x1b[0m") == b"  plain text  \x1b[1mbold\x1b[0m"


def test_without_a_terminal_the_client_runs_as_an_ordinary_child(tmp_path, capfd):
    code = run_full_screen(["sh", "-c", "echo hi; exit 3"], str(tmp_path), {"PATH": "/usr/bin:/bin"})
    assert code == 3 and "hi" in capfd.readouterr().out
