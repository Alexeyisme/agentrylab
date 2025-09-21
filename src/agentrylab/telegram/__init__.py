"""Telegram integration module for AgentryLab.

This module provides a clean API adapter for integrating AgentryLab with
external interfaces like Telegram bots, web applications, and other chat platforms.
"""

from .adapter import TelegramAdapter
from .models import (
    ConversationState,
    ConversationEvent,
    ConversationStatus,
    ConversationError,
)
from .exceptions import (
    ConversationNotFoundError,
    ConversationAlreadyExistsError,
    ConversationNotActiveError,
    InvalidPresetError,
)

__all__ = [
    "TelegramAdapter",
    "ConversationState",
    "ConversationEvent", 
    "ConversationStatus",
    "ConversationError",
    "ConversationNotFoundError",
    "ConversationAlreadyExistsError",
    "ConversationNotActiveError",
    "InvalidPresetError",
]
