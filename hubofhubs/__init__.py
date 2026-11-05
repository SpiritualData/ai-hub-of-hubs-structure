"""hubofhubs: the registry of AI-intelligence hubs, the seats (Protocols) and the assembly that wires them, and the scorer
that reads the registry together with a consumer's code.

Import it like the esoi library: with a checkout of this repository on ``PYTHONPATH`` (``../ai-hub-of-hubs-structure``), or
``pip install -e`` it, or install it from its git URL. Importing it reads nothing and runs nothing. The user-facing entry
functions (``run``, ``needs`` and ``assemble``) read the process environment when you give no ``environ``; every other
module takes a mapping and reads none.

    import hubofhubs
    result = hubofhubs.run("hub-of-hubs", "what is the latest Rust release?")   # best-measured arm of every part, no wiring
    from hubofhubs import Binding, evaluate, AssemblyConfig, assemble, register, resolve
"""
from hubofhubs.the_self.integrity.binding import Binding
from hubofhubs.the_self.integrity.measure import evaluate, evaluate_seats, check, metrics
from esoi.assemble import Assembly, AssemblyConfig, AssemblyError
from hubofhubs.the_self.assembler.oneline import Result, needs
from hubofhubs.the_self.assembler.resolution import HUB, assemble, assembler, choice, names, register, resolve
from esoi import entry

run = entry.runner(HUB)   # run(id, input): any solution or intent of the hub, the same call at every level (esoi.entry)

__all__ = ["Binding", "evaluate", "evaluate_seats", "check", "metrics", "AssemblyConfig", "AssemblyError", "choice", "names", "resolve", "register", "assemble", "assembler", "Assembly", "run", "needs", "Result"]
