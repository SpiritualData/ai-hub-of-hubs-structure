"""The hub's binding of the generic ``esoi.assemble``: one ``Assembler`` for scope ``hubofhubs``, and the public names a consumer
imports. Name validation, safe loading, the cascade, needs from typed parameters, build order and startup failure are the
library's (``esoi/docs/explanation/what-belongs-where.md``); the seats are in ``hubofhubs.seats``.
"""
import os
from pathlib import Path

from esoi.assemble import Assembler, AssemblyConfig

SCOPE = "hubofhubs"
HUB = Assembler(SCOPE, Path(__file__).resolve().parent, modules=(f"{SCOPE}.seats",))
choice, names, register, resolve = HUB.choice, HUB.names, HUB.register, HUB.resolve


def process_environment():
    """The process environment, as a mapping. The only place in the hub that reads it: the user-facing entry functions
    (``assemble``, ``run``, ``stream``, ``needs``) call this when the caller gave no ``environ``; every core module takes a mapping."""
    return os.environ


def assembler() -> Assembler:
    """The hub's own ``Assembler``, for a package that builds on the hub: ``Assembler(scope, dir, parent=hubofhubs.assembler())``
    inherits every seat and default, and states only the arms and choices that differ. ``assemble()`` below is unchanged."""
    return HUB


def assemble(config=None, provided=None, *, arms=None, options=None, environ=None, lock=None):
    """The hub's one-line assembly.

    ``assemble()`` builds every seat whose selected arm needs nothing from the consumer and lists the others in
    ``result.pending`` (one line each saying what to pass); it raises only for a name that does not exist or a cycle. A consumer
    names only what differs: ``arms={seat: arm name}``, ``options={seat: {argument: value}}``, ``provided={seat: object}``.
    ``environ`` defaults to the process environment (``environ={...}`` replaces it, ``environ={}`` means none; the sandbox and
    test form): an arm that declares ``ENVIRON = {option: variable}`` has those options filled from it, ``options`` always win, and a selected arm whose
    required variable is absent stays in ``pending`` with a line naming the variable. Reasons name variables, never values.
    ``lock`` is a lock file path or mapping (``esoi lock``) that keeps the arms you locked until you update it.
    Passing an ``AssemblyConfig`` as ``config`` is the strict form: exactly its ``solutions`` are built and an unmet need raises.
    """
    if config is not None:
        if arms or options or environ or lock:
            raise TypeError("pass either an AssemblyConfig or arms/options/environ/lock, not both")
        return HUB.assemble(config, provided)
    return HUB.assemble_defaults(AssemblyConfig(selections=dict(arms or {}), options=dict(options or {}), consumer_environ=dict(process_environment() if environ is None else environ), lock=lock), provided)
