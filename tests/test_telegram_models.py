"""Tests for Telegram integration data models."""

import pytest
from datetime import datetime

from agentrylab.telegram.models import (
    ConversationState,
    ConversationEvent,
    ConversationError,
    ConversationStatus,
    UserMessage,
)


class TestConversationState:
    """Test ConversationState model."""
    
    def test_conversation_state_creation(self):
        """Test basic conversation state creation."""
        state = ConversationState(
            conversation_id="test-123",
            preset_id="debates",
            topic="Test topic",
            user_id="user-456",
            status=ConversationStatus.ACTIVE,
        )
        
        assert state.conversation_id == "test-123"
        assert state.preset_id == "debates"
        assert state.topic == "Test topic"
        assert state.user_id == "user-456"
        assert state.status == ConversationStatus.ACTIVE
        assert state.current_iteration == 0
        assert isinstance(state.last_activity, datetime)
        assert isinstance(state.created_at, datetime)
        assert state.lab_instance is None
        assert state.metadata == {}
    
    def test_conversation_state_with_metadata(self):
        """Test conversation state with metadata."""
        metadata = {"custom_field": "value", "count": 42}
        state = ConversationState(
            conversation_id="test-123",
            preset_id="debates",
            topic="Test topic",
            user_id="user-456",
            status=ConversationStatus.ACTIVE,
            metadata=metadata,
        )
        
        assert state.metadata == metadata


class TestConversationEvent:
    """Test ConversationEvent model."""
    
    def test_conversation_event_creation(self):
        """Test basic conversation event creation."""
        event = ConversationEvent(
            conversation_id="test-123",
            event_type="agent_message",
            content="Hello world",
            iteration=1,
            agent_id="pro",
            role="agent",
        )
        
        assert event.conversation_id == "test-123"
        assert event.event_type == "agent_message"
        assert event.content == "Hello world"
        assert event.iteration == 1
        assert event.agent_id == "pro"
        assert event.role == "agent"
        assert isinstance(event.timestamp, datetime)
        assert event.metadata == {}
    
    def test_conversation_event_to_dict(self):
        """Test conversation event serialization."""
        event = ConversationEvent(
            conversation_id="test-123",
            event_type="agent_message",
            content="Hello world",
            iteration=1,
            agent_id="pro",
            role="agent",
        )
        
        event_dict = event.to_dict()
        
        assert event_dict["conversation_id"] == "test-123"
        assert event_dict["event_type"] == "agent_message"
        assert event_dict["content"] == "Hello world"
        assert event_dict["iteration"] == 1
        assert event_dict["agent_id"] == "pro"
        assert event_dict["role"] == "agent"
        assert "timestamp" in event_dict


class TestConversationError:
    """Test ConversationError model."""
    
    def test_conversation_error_creation(self):
        """Test basic conversation error creation."""
        error = ConversationError(
            conversation_id="test-123",
            error_type="provider_error",
            message="Provider failed",
            details={"provider": "openai", "status_code": 500},
        )
        
        assert error.conversation_id == "test-123"
        assert error.error_type == "provider_error"
        assert error.message == "Provider failed"
        assert error.details == {"provider": "openai", "status_code": 500}
        assert isinstance(error.timestamp, datetime)
    
    def test_conversation_error_to_dict(self):
        """Test conversation error serialization."""
        error = ConversationError(
            conversation_id="test-123",
            error_type="provider_error",
            message="Provider failed",
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["conversation_id"] == "test-123"
        assert error_dict["error_type"] == "provider_error"
        assert error_dict["message"] == "Provider failed"
        assert "timestamp" in error_dict


class TestUserMessage:
    """Test UserMessage model."""
    
    def test_user_message_creation(self):
        """Test basic user message creation."""
        message = UserMessage(
            conversation_id="test-123",
            user_id="user-456",
            content="Hello agents!",
        )
        
        assert message.conversation_id == "test-123"
        assert message.user_id == "user-456"
        assert message.content == "Hello agents!"
        assert message.processed is False
        assert isinstance(message.timestamp, datetime)
    
    def test_user_message_to_dict(self):
        """Test user message serialization."""
        message = UserMessage(
            conversation_id="test-123",
            user_id="user-456",
            content="Hello agents!",
        )
        
        message_dict = message.to_dict()
        
        assert message_dict["conversation_id"] == "test-123"
        assert message_dict["user_id"] == "user-456"
        assert message_dict["content"] == "Hello agents!"
        assert message_dict["processed"] is False
        assert "timestamp" in message_dict


class TestConversationStatus:
    """Test ConversationStatus enum."""
    
    def test_conversation_status_values(self):
        """Test conversation status enum values."""
        assert ConversationStatus.ACTIVE.value == "active"
        assert ConversationStatus.PAUSED.value == "paused"
        assert ConversationStatus.STOPPED.value == "stopped"
        assert ConversationStatus.ERROR.value == "error"
        assert ConversationStatus.COMPLETED.value == "completed"
