"""What a Folder View arm returns: the files to show first, each with the reason, and the folders it left out, each with the reason."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class Pick:
    """One file to show. ``named`` is true when the goal or context names it (it is never evicted from the view). ``flagged`` is a short reason
    when the file lies in a risky place and the work named it anyway: it is returned for the caller to decide and is not to be shown unasked."""
    path: str
    reason: str
    size: int = 0
    named: bool = False
    flagged: str = ""


@dataclass(frozen=True)
class LeftOut:
    """A folder (or a risky file) that was not scanned, and why. ``kind`` is the marker row's kind (dependency, build, cache, vcs, generated, risky,
    hidden); ``risky`` is true for credentials, backups and other people's private data."""
    path: str
    reason: str
    kind: str = ""
    risky: bool = False
    is_file: bool = False


@dataclass
class FolderChoice:
    """The answer of ``choose``: ``picks`` best first, ``left_out`` the folders (and risky files) kept out of the scan, ``skipped`` how many files
    of each kind were passed over one by one (lock files, binaries, minified bundles), and ``scanned`` how many readable files were considered."""
    picks: List[Pick] = field(default_factory=list)
    left_out: List[LeftOut] = field(default_factory=list)
    skipped: Dict[str, int] = field(default_factory=dict)
    scanned: int = 0

    def paths(self) -> List[str]:
        return [p.path for p in self.picks if not p.flagged]

    def to_dict(self) -> Dict[str, Any]:
        return {"picks": [vars(p) for p in self.picks], "left_out": [vars(x) for x in self.left_out], "skipped": dict(self.skipped),
                "scanned": self.scanned}
