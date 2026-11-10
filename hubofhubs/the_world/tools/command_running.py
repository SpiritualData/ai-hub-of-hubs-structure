"""Run one shell command in a folder, bounded: its own process group, a timeout that kills the group, merged and clipped output.

Role: a harness that executes the actions a model wrote needs a command runner that never hangs, never floods the prompt and refuses the
few commands that should not run unattended. ``run_command`` runs ``bash -c`` with the folder as its working directory; ``refusal`` is the
floor of what is not run at all.

``refusal`` is a floor, not a sandbox. It scans the command's words, so a program that opens a path itself (``python -c "open('/etc/x')"``)
passes. A deployment that needs real confinement passes ``wrap``, an argv prefix of a sandbox launcher put before ``bash``; ``sandbox_wrap``
builds the bubblewrap prefix (whole disk read-only, the working folder and a private temp folder writable). With a ``wrap`` the sandbox enforces
the folder boundary, so ``refusal`` leaves out its path checks and keeps the rest of the floor.
Standard library and the hub's process-group helpers only; nothing here reads the environment.
"""
from __future__ import annotations

import os
import posixpath
import re
import shlex
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence, Tuple

from hubofhubs.the_world.tools.delegated_agent_sessions.contract import kill_process_group

CLIPPED = "\n... [{n} characters left out] ...\n"
SEGMENT = re.compile(r"\|\||&&|[;&|\n]")
SHELL_PIPE = re.compile(r"\|\s*(?:sudo\s+)?(?:\S*/)?(?:ba|z|da|k)?sh\b")
DOWNLOADER = re.compile(r"\b(?:curl|wget|fetch)\b")
POWER = ("shutdown", "reboot", "halt", "poweroff")
WHOLE_DISK = ("/", "/*", "~", "~/", "~/*", "$HOME", "$HOME/", "${HOME}", "${HOME}/")
DEVICES = ("/dev/null", "/dev/stdin", "/dev/stdout", "/dev/stderr", "/dev/zero", "/dev/urandom")


@dataclass
class CommandResult:
    """What one command did: its exit code (-9 after a timeout kill, 126 when refused), its merged and clipped output, whether the
    timeout ended it and the reason it was refused ('' when it ran)."""
    code: int
    output: str
    timed_out: bool = False
    refused: str = ""


def clip(text: str, limit: int) -> str:
    """``text`` cut to about ``limit`` characters, keeping the head and the tail and saying how much was left out."""
    if limit <= 0 or len(text) <= limit:
        return text
    keep_head = limit * 2 // 3
    keep_tail = max(limit - keep_head, 0)
    left_out = len(text) - keep_head - keep_tail
    return text[:keep_head] + CLIPPED.format(n=left_out) + (text[len(text) - keep_tail:] if keep_tail else "")


def words(segment: str) -> List[str]:
    try:
        return shlex.split(segment, comments=False)
    except ValueError:
        return segment.split()


def command_words(tokens: Sequence[str]) -> List[str]:
    """``tokens`` without leading variable assignments and wrappers that only prefix another command (``env``, ``nohup``, ``time``)."""
    rest = list(tokens)
    while rest and (re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", rest[0]) or rest[0] in ("env", "nohup", "time", "nice", "command", "exec")):
        rest.pop(0)
    return rest


def removes_everything(rest: Sequence[str]) -> bool:
    flags = "".join(t.lstrip("-") for t in rest[1:] if t.startswith("-") and not t.startswith("--"))
    recursive = "r" in flags.lower() or "--recursive" in rest
    targets = [t for t in rest[1:] if not t.startswith("-")]
    return recursive and any(t.rstrip("/") in ("", "~", "$HOME", "${HOME}") or t in WHOLE_DISK for t in targets)


def outside(token: str, root: str, allowed: Iterable[str]) -> bool:
    """Whether the path word ``token`` leads outside ``root`` and the ``allowed`` folders."""
    path = posixpath.normpath(token if token.startswith("/") else posixpath.join(root, token))
    if token in DEVICES:
        return False
    return not any(path == base or path.startswith(base.rstrip("/") + "/") for base in allowed)


def path_part(token: str) -> str:
    """The path inside a word such as ``--out=/x`` or ``>/x``."""
    token = re.sub(r"^[0-9]*[<>]+", "", token)
    return token.split("=", 1)[1] if re.match(r"^-{1,2}[A-Za-z][\w-]*=", token) else token


def sandbox_wrap(working_dir: str, *, program: str = "bwrap", network: bool = True, extra_read_write: Sequence[str] = ()) -> Tuple[str, ...]:
    """The bubblewrap argv prefix that runs a command with the whole filesystem read-only and only ``working_dir``, a private temp folder and
    each ``extra_read_write`` folder writable. ``--unshare-net`` is added only when ``network`` is False. Returns ``()`` when ``program`` is not
    on PATH, so the caller runs unconfined (with ``refusal`` as the only floor)."""
    if shutil.which(program) is None:
        return ()
    folder = os.path.abspath(working_dir)
    argv = [program, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp", "--bind", folder, folder,
            "--chdir", folder, "--die-with-parent"]
    if not network:
        argv.append("--unshare-net")
    for path in extra_read_write:
        place = os.path.abspath(path)
        argv += ["--bind", place, place]
    return tuple(argv)


def refusal(command: str, working_dir: str, *, paths: bool = True) -> str:
    """The reason ``command`` should not run, or '' when it may. A floor, not a sandbox (see the module text): it refuses ``sudo``,
    ``rm -r`` of the disk or the home folder, ``git push``, shutdown or reboot, a download piped into a shell, and (when ``paths``) any
    absolute, home or ``..`` path word that leads outside ``working_dir`` and the temp folder."""
    root = posixpath.normpath(os.path.abspath(working_dir))
    allowed = {root, posixpath.normpath(tempfile.gettempdir())}
    if SHELL_PIPE.search(command) and DOWNLOADER.search(command):
        return "a download piped into a shell is not run"
    for segment in SEGMENT.split(command):
        tokens = words(segment)
        rest = command_words(tokens)
        if not rest:
            continue
        name = posixpath.basename(rest[0])
        if name == "sudo" or name == "doas":
            return "sudo is not run"
        if name in POWER:
            return f"{name} is not run"
        if name == "rm" and removes_everything(rest):
            return "removing everything under the disk root or the home folder is not run"
        if name == "git" and "push" in rest[1:4]:
            return "git push is not run; changes stay in the folder"
        for index, token in enumerate(rest if paths else ()):
            word = path_part(token)
            if not word:
                continue
            if word.startswith("~") or word.startswith("$HOME") or word.startswith("${HOME}"):
                return f"the path {word!r} is outside the working folder"
            if word.startswith("/") and not (index == 0 and word.count("/") >= 2 and re.match(r"^/(?:usr/|usr/local/|opt/)?s?bin/", word)):
                if outside(word, root, allowed):
                    return f"the path {word!r} is outside the working folder"
            elif ".." in word.split("/") and outside(word, root, allowed):
                return f"the path {word!r} is outside the working folder"
    return ""


def run_command(command: str, *, working_dir: str, timeout: float = 60.0, environment: Mapping[str, str] | None = None,
                wrap: Sequence[str] = (), limit: int = 4000) -> CommandResult:
    """Run ``command`` with ``bash -c`` in ``working_dir`` (its own process group, stdin closed). After ``timeout`` seconds the whole
    group is killed and ``timed_out`` is set. Output merges stdout and stderr and is clipped to ``limit`` characters, head and tail kept.
    ``wrap`` is an argv prefix (a sandbox launcher, see ``sandbox_wrap``) put before ``bash``; the sandbox then enforces the folder boundary, so the path checks of ``refusal`` are skipped; ``environment`` replaces the child's environment when given.
    A refused command does not run (``refused`` holds the reason). Never raises."""
    reason = refusal(command, working_dir, paths=not wrap)
    if reason:
        return CommandResult(code=126, output=f"refused: {reason}", refused=reason)
    argv = [*wrap, "bash", "-c", command]
    try:
        proc = subprocess.Popen(argv, cwd=working_dir, env=dict(environment) if environment is not None else None,
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors="replace", start_new_session=True)
    except (OSError, ValueError) as error:
        return CommandResult(code=127, output=clip(f"could not start: {error}", limit))
    timed_out = False
    try:
        out, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_process_group(proc)
        try:
            out, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out = ""
    text = clip(out or "", limit)
    if timed_out:
        text = (text + f"\n[stopped after {timeout:g} seconds]").lstrip("\n")
    return CommandResult(code=-9 if timed_out else int(proc.returncode or 0), output=text, timed_out=timed_out)
