"""Data models for Telegram integration."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from agentrylab.lab import Lab


class ConversationStatus(Enum):
    """Status of a conversation."""
    COLLECTING = "collecting"  # collecting user_inputs before starting
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class ConversationState:
    """State of a conversation."""
    conversation_id: str
    preset_id: str
    topic: str
    user_id: str
    status: ConversationStatus
    current_iteration: int = 0
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lab_instance: Optional[Lab] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Generate conversation ID if not provided."""
        if not self.conversation_id:
            self.conversation_id = str(uuid.uuid4())


@dataclass
class ConversationEvent:
    """Event in a conversation."""
    conversation_id: str
    event_type: str  # agent_message, user_turn, error, status_change, iteration_complete
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    iteration: int = 0
    agent_id: Optional[str] = None
    role: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conversation_id": self.conversation_id,
            "event_type": self.event_type,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "iteration": self.iteration,
            "agent_id": self.agent_id,
            "role": self.role,
        }


@dataclass
class ConversationError:
    """Error in a conversation."""
    conversation_id: str
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conversation_id": self.conversation_id,
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class UserMessage:
    """User message to be queued for a conversation."""
    conversation_id: str
    user_id: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "processed": self.processed,
        }
