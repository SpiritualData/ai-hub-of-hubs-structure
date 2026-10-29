"""What a consumer supplies so the hub can read it: where its code is, which of its modules fill which area, and how to
prove that a hub can be added by configuration. The hub never imports the consumer; it is handed these."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Tuple


@dataclass
class Binding:
    consumer: str                         # the consumer's name, as it appears in the ``consumer`` column of the registry
    root: Path                            # the consumer repository: evidence paths in the registry are relative to it
    seats: List[Dict[str, str]]           # per area: area, seam_solution_id (";" separated), vendor_terms, code_paths
    core_dir: Path                        # the code scanned for vendor-specific branches
    records_dir: Path                     # the consumer's ESOI records (solutions.csv, implementations.csv)
    names_of: Callable[[str], List[str]]  # solution id -> the implementation names its code declares
    probes: Dict[str, Callable[[], Tuple[bool, str]]] = field(default_factory=dict)   # area -> prove a fake hub by config
