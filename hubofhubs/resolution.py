"""The hub's binding of the generic ``esoi.assemble``: one ``Assembler`` for scope ``hubofhubs``, and the public names a consumer
imports. Name validation, safe loading, the cascade, needs from typed parameters, build order and startup failure are the
library's (``esoi/docs/explanation/what-belongs-where.md``); the seats are in ``hubofhubs.seats``.
"""
from pathlib import Path

from esoi.assemble import Assembler

SCOPE = "hubofhubs"
HUB = Assembler(SCOPE, Path(__file__).resolve().parent, modules=(f"{SCOPE}.seats",))
assemble, choice, names, register, resolve = HUB.assemble, HUB.choice, HUB.names, HUB.register, HUB.resolve
