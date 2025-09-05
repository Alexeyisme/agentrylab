from __future__ import annotations

# Public package metadata
from .version import __version__  # re-export

# Public API
from .lab import Lab, LabStatus
from .api import init, run, list_threads
from .types import Event

__all__ = [
    "__version__",
    "Lab",
    "LabStatus",
    "Event",
    "init",
    "init_lab",
    "list_threads",
    "run",
]

# Back-compat alias
init_lab = init
