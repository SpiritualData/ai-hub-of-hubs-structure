"""Slash-command registry of the chat input (hub table). Vendored from Mistral Vibe v2.26.1 (https://github.com/mistralai/mistral-vibe, Apache-2.0, file vibe/cli/commands.py); modified from upstream: default command table replaced by the hub's six commands (help, stop, resume, who, structure, quit), platform and clipboard imports and the external-editor and file-mention help lines cut, registry machinery kept."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandContext:
    registry_skills_enabled: bool = False
    experimental_harness: bool = False


CommandAvailability = Callable[[CommandContext], bool]


@dataclass
class Command:
    aliases: frozenset[str]
    description: str
    handler: str
    exits: bool = False
    side_channel: bool = False
    is_available: CommandAvailability | None = None
    forwards_to_model: bool = False


class CommandRegistry:
    def __init__(
        self,
        excluded_commands: list[str] | None = None,
        context: CommandContext | None = None,
    ) -> None:
        if excluded_commands is None:
            excluded_commands = []
        self._disabled_commands = set(excluded_commands)
        self._commands: dict[str, Command] = {}
        self.refresh(context)

    def _build_commands(self) -> dict[str, Command]:
        return {
            "help": Command(
                aliases=frozenset(["/help"]),
                description="Show the keys and the commands",
                handler="_show_help",
                side_channel=True,
            ),
            "stop": Command(
                aliases=frozenset(["/stop"]),
                description="Stop the current turn",
                handler="_stop_turn",
                side_channel=True,
            ),
            "resume": Command(
                aliases=frozenset(["/resume"]),
                description="Resume the stopped turn",
                handler="_resume_turn",
            ),
            "who": Command(
                aliases=frozenset(["/who"]),
                description="Show who the AI acts for",
                handler="_show_who",
                side_channel=True,
            ),
            "structure": Command(
                aliases=frozenset(["/structure"]),
                description="Show the solutions the work serves",
                handler="_show_structure",
                side_channel=True,
            ),
            "quit": Command(
                aliases=frozenset(["/quit"]),
                description="Quit the chat",
                handler="_exit_app",
                exits=True,
                side_channel=True,
            ),
        }

    @property
    def commands(self) -> dict[str, Command]:
        return self._commands

    def refresh(self, context: CommandContext | None = None) -> None:
        self._context = context or CommandContext()
        self._commands = {
            name: command
            for name, command in self._build_commands().items()
            if name not in self._disabled_commands
            and self._is_command_available(command)
        }

    def _is_command_available(self, command: Command) -> bool:
        if command.is_available is None:
            return True
        return command.is_available(self._context)

    def _alias_map(self) -> dict[str, str]:
        return {
            alias: cmd_name
            for cmd_name, cmd in self.commands.items()
            for alias in cmd.aliases
        }

    def get(self, name: str) -> Command | None:
        return self.commands.get(name)

    def has_command(self, name: str) -> bool:
        return name in self.commands

    def get_command_name(self, user_input: str) -> str | None:
        return self._alias_map().get(user_input.lower().strip())

    def parse_command(self, user_input: str) -> tuple[str, Command, str] | None:
        parts = user_input.strip().split(None, 1)
        if not parts:
            return None

        cmd_word = parts[0]
        cmd_args = parts[1] if len(parts) > 1 else ""
        cmd_name = self.get_command_name(cmd_word)
        if cmd_name is None:
            return None

        if not cmd_word.startswith("/") and cmd_args:
            return None

        command = self.commands[cmd_name]
        return cmd_name, command, cmd_args

    def get_help_text(self) -> str:
        lines: list[str] = [
            "### Keyboard Shortcuts",
            "",
            "- `Enter` Submit message",
            "- `Ctrl+J` / `Shift+Enter` Insert newline",
            "- `Escape` Interrupt agent or close dialogs",
            "- `Ctrl+C` Quit (or clear input if text present)",
            "- `Ctrl+O` Toggle tool output view",
            "",
            "### Commands",
            "",
        ]

        for name, cmd in sorted(self.commands.items()):
            canonical_alias = f"/{name}"
            aliases = ", ".join(
                f"`{alias}`"
                for alias in sorted(
                    cmd.aliases, key=lambda alias: (alias != canonical_alias, alias)
                )
            )
            lines.append(f"- {aliases}: {cmd.description}")
        return "\n".join(lines)
