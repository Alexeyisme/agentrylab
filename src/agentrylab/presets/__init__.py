from __future__ import annotations

"""Packaged example presets.

Use `path("debates.yaml")` to get a filesystem path to a preset shipped with
the package. Intended for quick demos; for production use, maintain your own
presets in your repository.
"""

from importlib.resources import files


def path(name: str) -> str:
    """Return a filesystem path to the packaged preset (best effort)."""
    return str(files(__package__) / name)

