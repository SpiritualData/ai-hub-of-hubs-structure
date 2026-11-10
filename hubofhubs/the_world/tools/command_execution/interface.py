"""The interface of CommandExecution: a Protocol declared with ``@solution``. Importing this module runs nothing."""
import typing
from typing import Mapping, Optional, runtime_checkable
from esoi import solution
from hubofhubs.the_world.tools.command_running import CommandResult


@solution("command-execution", kind="event", entry="run", example={"command": "echo hello", "working_dir": "."})
@runtime_checkable
class CommandExecution(typing.Protocol):
    """Runs one shell command for an agent in a folder and says what happened: bounded in time and output, refusing the few commands that should not run
    unattended, and (in the arms that confine) unable to write outside the folder it was given and a scratch folder that lasts the session."""

    def run(self, command: str, working_dir: str, timeout: float = 60.0, environment: Optional[Mapping[str, str]] = None, scratch: str = "",
            limit: int = 4000) -> CommandResult: ...
