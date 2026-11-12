"""The final answer's markdown, drawn for a terminal with the standard library: headings bold, emphasis and inline code styled, bullets as dots, code blocks indented and
dim, rules as a line. Plain text (no colour) is returned as written, so a pipe or a log keeps the model's own characters. A richer renderer (the Textual arm uses the
``rich`` library's) replaces this one where it is installed; this one is what every terminal gets."""
from __future__ import annotations

import re
import textwrap
from typing import List

BOLD, DIM, CODE, RESET = "\x1b[1m", "\x1b[38;5;245m", "\x1b[36m", "\x1b[0m"      # quiet detail is an explicit grey, never SGR 2 (faint is drawn at a strength each terminal chooses)
HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
NUMBERED = re.compile(r"^(\s*)(\d+)[.)]\s+(.*)$")
RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")


def inline(text: str) -> str:
    """Bold, emphasis and inline code of one line."""
    text = re.sub(r"`([^`]+)`", lambda m: f"{CODE}{m.group(1)}{RESET}", text)
    text = re.sub(r"\*\*([^*]+)\*\*", lambda m: f"{BOLD}{m.group(1)}{RESET}", text)
    text = re.sub(r"(?<![\w*])\*([^*\s][^*]*)\*(?![\w*])", lambda m: f"\x1b[3m{m.group(1)}{RESET}", text)
    return re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", lambda m: f"{m.group(1)} ({m.group(2)})", text)


def markdown_lines(text: str, width: int = 0, color: bool = True) -> List[str]:
    """``text`` as lines for a terminal ``width`` wide (0: not wrapped). Without ``color`` the lines are the text as written."""
    if not color:      # no colour (a pipe, a file, a screen that draws its own markdown): the words, with the markers taken out and the lines wrapped at word boundaries
        from hubofhubs.the_consciousness.ai_session_experience.terminal_experience.present import strip_markdown
        plain = strip_markdown(text).splitlines()
        return [piece for line in plain for piece in (wrap("", line.strip(), width) if width and line.strip() and not line.startswith("    ") else [line])] if width else plain
    lines = text.strip().splitlines()
    out: List[str] = []
    fenced = False
    for line in lines:
        if line.strip().startswith("```"):
            fenced = not fenced
            continue
        if fenced:
            out.append(f"{DIM}    {line}{RESET}")
            continue
        heading, bullet, numbered = HEADING.match(line), BULLET.match(line), NUMBERED.match(line)
        if heading:
            out.extend(["", f"{BOLD}{inline(heading.group(2))}{RESET}"])
        elif RULE.match(line):
            out.append(f"{DIM}{'-' * min(width or 40, 60)}{RESET}")
        elif bullet:
            lead = bullet.group(1) + "• "
            out.extend(wrap(lead, inline(bullet.group(2)), width))
        elif numbered:
            lead = f"{numbered.group(1)}{numbered.group(2)}. "
            out.extend(wrap(lead, inline(numbered.group(3)), width))
        elif line.lstrip().startswith(("|", ">")) or not line.strip():
            out.append(inline(line))
        else:
            out.extend(wrap("", inline(line), width))
    return out


def wrap(lead: str, text: str, width: int) -> List[str]:
    """One paragraph or item wrapped to ``width`` with its continuation indented under the text (escape codes are not counted by eye, so a styled line may wrap early)."""
    if not width or len(text) + len(lead) <= width:
        return [lead + text]
    return textwrap.wrap(text, width, initial_indent=lead, subsequent_indent=" " * len(lead), break_long_words=False, break_on_hyphens=False) or [lead + text]


__all__ = ["markdown_lines"]
