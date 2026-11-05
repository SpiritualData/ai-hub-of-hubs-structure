"""ZeroConfig."""
from typing import Any, Mapping, Optional
from esoi import implementation


@implementation("the-assembler", "zero_config")
class ZeroConfig:
    """Every seat from its selected arm, built from the environment it is given (none by default): which seats are built and, for each that is
    not, the line that says exactly what to pass or set."""
    REQUIRES = ()     # nothing: it assembles the hub itself

    def coverage(self, environ: Optional[Mapping[str, str]] = None) -> Mapping[str, Any]:
        from hubofhubs.the_self.assembler.resolution import assemble  # late: the hub assembles itself only when coverage is asked for
        system = assemble(environ=dict(environ or {}))
        built = system.solutions()
        return {"built": built, "pending": dict(system.pending), "share": round(len(built) / max(len(built) + len(system.pending), 1), 3)}
