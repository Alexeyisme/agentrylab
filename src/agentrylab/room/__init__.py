"""The Room: a zero-player stage where android personas talk to each other.

This package is a thin, self-contained orchestration layer built on the same
provider adapters as the lab engine. Unlike YAML presets (fixed cast, fixed
schedule), a Room is *live*: personas can join or leave at any moment, humans
can drop messages into the conversation, and every event is streamed to the
web UI over a WebSocket.

Public pieces:
  - ``Persona``            — a character (name, personality, avatar look)
  - ``PERSONA_LIBRARY``    — ready-made characters to drop into a room
  - ``Room`` / ``RoomManager`` — the conversation loop and its registry
  - ``create_app``         — FastAPI application (REST + WebSocket + static UI)
"""

from .avatars import AVATAR_CATALOG
from .personas import PERSONA_LIBRARY, Persona
from .room import Room, RoomManager

__all__ = [
    "AVATAR_CATALOG",
    "PERSONA_LIBRARY",
    "Persona",
    "Room",
    "RoomManager",
]
