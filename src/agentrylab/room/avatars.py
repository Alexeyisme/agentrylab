"""Catalog of android parts the web UI knows how to draw.

The frontend owns the actual SVG; the backend only validates that a persona
refers to parts that exist so a room never contains an avatar the UI cannot
render. Keep the ids in sync with ``web/src/avatars``.
"""

from __future__ import annotations

from typing import Dict, List, TypedDict


class Part(TypedDict):
    id: str
    label: str


FACES: List[Part] = [
    {"id": "visor", "label": "Visor"},
    {"id": "duo", "label": "Duo"},
    {"id": "cyclops", "label": "Cyclops"},
    {"id": "pixel", "label": "Pixel"},
    {"id": "feline", "label": "Feline"},
    {"id": "crt", "label": "CRT"},
]

BODIES: List[Part] = [
    {"id": "capsule", "label": "Capsule"},
    {"id": "boxy", "label": "Boxy"},
    {"id": "hover", "label": "Hover"},
    {"id": "slim", "label": "Slim"},
    {"id": "orb", "label": "Orb"},
    {"id": "tank", "label": "Tank"},
]

# Accent colours; the UI derives glows and gradients from the accent.
PALETTES: List[Dict[str, str]] = [
    {"id": "cyan", "label": "Cyan", "accent": "#22d3ee"},
    {"id": "magenta", "label": "Magenta", "accent": "#e879f9"},
    {"id": "lime", "label": "Lime", "accent": "#a3e635"},
    {"id": "amber", "label": "Amber", "accent": "#fbbf24"},
    {"id": "coral", "label": "Coral", "accent": "#fb7185"},
    {"id": "violet", "label": "Violet", "accent": "#a78bfa"},
    {"id": "mint", "label": "Mint", "accent": "#34d399"},
    {"id": "ice", "label": "Ice", "accent": "#93c5fd"},
]

FACE_IDS = {p["id"] for p in FACES}
BODY_IDS = {p["id"] for p in BODIES}
PALETTE_IDS = {p["id"] for p in PALETTES}

AVATAR_CATALOG = {"faces": FACES, "bodies": BODIES, "palettes": PALETTES}
