"""The arms of Command Execution: the refusal floor alone, and the floor inside a bubblewrap sandbox.

Both run ``bash -c`` through ``command_running.run_command`` (its own process group, a timeout that kills the group, merged and clipped output). They differ in
what holds the folder boundary: the floor scans the command's words and a program that opens a path itself passes it; the sandbox makes the disk read-only
outside the working folder and a scratch folder, so the boundary is enforced by the system and not by reading words. Standard library and the hub only.
"""
from __future__ import annotations

from typing import Mapping, Optional

from esoi import implementation

from hubofhubs.the_self.assembler import arm_needs as needs
from hubofhubs.the_world.tools.command_running import CommandResult, run_command, sandbox_wrap


@implementation("command-execution", "refusal_floor")
class RefusalFloor:
    """Runs the command after the refusal floor, with no confinement."""
    REQUIRES = ()

    def run(self, command: str, working_dir: str, timeout: float = 60.0, environment: Optional[Mapping[str, str]] = None, scratch: str = "",
            limit: int = 4000) -> CommandResult:
        return run_command(command, working_dir=working_dir, timeout=timeout, environment=environment, limit=limit)


@implementation("command-execution", "bubblewrap_wrapper")
class BubblewrapWrapper:
    """Runs the command in a bubblewrap sandbox: the whole disk read-only, the working folder and the session's scratch folder (bound at ``/tmp``) writable.
    Without bubblewrap on the machine the command runs with the floor alone, and ``confined`` says so."""
    REQUIRES = (needs.BUBBLEWRAP,)

    def __init__(self, network: bool = True, program: str = "bwrap"):
        self.network, self.program = network, program

    def confined(self, working_dir: str) -> bool:
        return bool(sandbox_wrap(working_dir, program=self.program, network=self.network))

    def run(self, command: str, working_dir: str, timeout: float = 60.0, environment: Optional[Mapping[str, str]] = None, scratch: str = "",
            limit: int = 4000) -> CommandResult:
        wrap = sandbox_wrap(working_dir, program=self.program, network=self.network, scratch=scratch)
        return run_command(command, working_dir=working_dir, timeout=timeout, environment=environment, wrap=wrap, limit=limit)
