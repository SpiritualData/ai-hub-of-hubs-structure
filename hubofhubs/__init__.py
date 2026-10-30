"""hubofhubs: the registry of AI-intelligence hubs, the seats (Protocols) and the assembly that wires them, and the scorer
that reads the registry together with a consumer's code.

Import it like the esoi library: with a checkout of this repository on ``PYTHONPATH`` (``../ai-hub-of-hubs-structure``), or
``pip install -e`` it, or install it from its git URL. It reads only files, makes no model call, no network request and no
environment read.

    from hubofhubs import Binding, evaluate, AssemblyConfig, assemble, register, resolve
"""
from .binding import Binding
from .measure import evaluate, check, metrics
from esoi.assemble import Assembly, AssemblyConfig, AssemblyError
from .resolution import assemble, choice, names, register, resolve

__all__ = ["Binding", "evaluate", "check", "metrics", "AssemblyConfig", "AssemblyError", "choice", "names", "resolve", "register", "assemble", "Assembly"]
