"""Tests for TelegramAdapter."""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from agentrylab.telegram.adapter import TelegramAdapter
from agentrylab.telegram.exceptions import (
    ConversationAlreadyExistsError,
    ConversationNotFoundError,
    ConversationNotActiveError,
    InvalidPresetError,
)
from agentrylab.telegram.models import ConversationStatus


class TestTelegramAdapter:
    """Test TelegramAdapter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = TelegramAdapter(max_concurrent_conversations=10)
    
    def test_adapter_initialization(self):
        """Test adapter initialization."""
        assert self.adapter.max_concurrent_conversations == 10
        assert len(self.adapter._conversations) == 0
        assert len(self.adapter._event_streams) == 0
        assert len(self.adapter._user_message_queues) == 0
        assert len(self.adapter._running_tasks) == 0
    
    @patch('agentrylab.telegram.adapter.init')
    def test_start_conversation_success(self, mock_init):
        """Test successful conversation start."""
        # Mock the lab instance
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        assert conversation_id is not None
        assert conversation_id in self.adapter._conversations
        assert conversation_id in self.adapter._event_streams
        assert conversation_id in self.adapter._user_message_queues
        
        state = self.adapter._conversations[conversation_id]
        assert state.preset_id == "debates"
        assert state.topic == "Test topic"
        assert state.user_id == "user123"
        assert state.status == ConversationStatus.ACTIVE
        assert state.lab_instance == mock_lab
        
        mock_init.assert_called_once_with(
            "debates",
            experiment_id=conversation_id,
            prompt="Test topic",
            resume=True
        )
    
    @patch('agentrylab.telegram.adapter.init')
    def test_start_conversation_with_custom_id(self, mock_init):
        """Test starting conversation with custom ID."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        custom_id = "custom-conversation-123"
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123",
            conversation_id=custom_id
        )
        
        assert conversation_id == custom_id
        assert custom_id in self.adapter._conversations
    
    @patch('agentrylab.telegram.adapter.init')
    def test_start_conversation_duplicate_id(self, mock_init):
        """Test starting conversation with duplicate ID."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        custom_id = "duplicate-test"
        
        # Start first conversation
        self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123",
            conversation_id=custom_id
        )
        
        # Try to start second conversation with same ID
        with pytest.raises(ConversationAlreadyExistsError):
            self.adapter.start_conversation(
                preset_id="debates",
                topic="Another topic",
                user_id="user456",
                conversation_id=custom_id
            )
    
    @patch('agentrylab.telegram.adapter.init')
    def test_start_conversation_invalid_preset(self, mock_init):
        """Test starting conversation with invalid preset."""
        mock_init.side_effect = Exception("Invalid preset")
        
        with pytest.raises(InvalidPresetError):
            self.adapter.start_conversation(
                preset_id="invalid_preset",
                topic="Test topic",
                user_id="user123"
            )
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_state(self, mock_init):
        """Test getting conversation state."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        state = self.adapter.get_conversation_state(conversation_id)
        assert state.conversation_id == conversation_id
        assert state.preset_id == "debates"
        assert state.topic == "Test topic"
        assert state.user_id == "user123"
    
    def test_get_conversation_state_not_found(self):
        """Test getting state for non-existent conversation."""
        with pytest.raises(ConversationNotFoundError):
            self.adapter.get_conversation_state("non-existent")
    
    @patch('agentrylab.telegram.adapter.init')
    def test_post_user_message(self, mock_init):
        """Test posting user message."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Post user message
        self.adapter.post_user_message(
            conversation_id=conversation_id,
            message="Hello agents!",
            user_id="user123"
        )
        
        # Check that message was queued
        user_queue = self.adapter._user_message_queues[conversation_id]
        assert not user_queue.empty()
        
        user_msg = user_queue.get_nowait()
        assert user_msg.conversation_id == conversation_id
        assert user_msg.user_id == "user123"
        assert user_msg.content == "Hello agents!"
        assert not user_msg.processed
    
    @patch('agentrylab.telegram.adapter.init')
    def test_post_user_message_not_found(self, mock_init):
        """Test posting message to non-existent conversation."""
        with pytest.raises(ConversationNotFoundError):
            self.adapter.post_user_message(
                conversation_id="non-existent",
                message="Hello!",
                user_id="user123"
            )
    
    @patch('agentrylab.telegram.adapter.init')
    def test_post_user_message_not_active(self, mock_init):
        """Test posting message to inactive conversation."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Pause conversation
        self.adapter.pause_conversation(conversation_id)
        
        # Try to post message
        with pytest.raises(ConversationNotActiveError):
            self.adapter.post_user_message(
                conversation_id=conversation_id,
                message="Hello!",
                user_id="user123"
            )
    
    @patch('agentrylab.telegram.adapter.init')
    def test_pause_resume_conversation(self, mock_init):
        """Test pausing and resuming conversation."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Check initial status
        state = self.adapter.get_conversation_state(conversation_id)
        assert state.status == ConversationStatus.ACTIVE
        
        # Pause conversation
        self.adapter.pause_conversation(conversation_id)
        state = self.adapter.get_conversation_state(conversation_id)
        assert state.status == ConversationStatus.PAUSED
        
        # Resume conversation
        self.adapter.resume_conversation(conversation_id)
        state = self.adapter.get_conversation_state(conversation_id)
        assert state.status == ConversationStatus.ACTIVE
    
    @patch('agentrylab.telegram.adapter.init')
    def test_stop_conversation(self, mock_init):
        """Test stopping conversation."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Stop conversation
        self.adapter.stop_conversation(conversation_id)
        
        state = self.adapter.get_conversation_state(conversation_id)
        assert state.status == ConversationStatus.STOPPED
    
    @patch('agentrylab.telegram.adapter.init')
    def test_list_user_conversations(self, mock_init):
        """Test listing user conversations."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        # Start conversations for different users
        conv1 = self.adapter.start_conversation(
            preset_id="debates",
            topic="Topic 1",
            user_id="user123"
        )
        
        conv2 = self.adapter.start_conversation(
            preset_id="standup_club",
            topic="Topic 2",
            user_id="user123"
        )
        
        conv3 = self.adapter.start_conversation(
            preset_id="debates",
            topic="Topic 3",
            user_id="user456"
        )
        
        # List conversations for user123
        user_conversations = self.adapter.list_user_conversations("user123")
        assert len(user_conversations) == 2
        assert conv1 in [c.conversation_id for c in user_conversations]
        assert conv2 in [c.conversation_id for c in user_conversations]
        assert conv3 not in [c.conversation_id for c in user_conversations]
        
        # List conversations for user456
        user_conversations = self.adapter.list_user_conversations("user456")
        assert len(user_conversations) == 1
        assert conv3 in [c.conversation_id for c in user_conversations]
    
    @patch('agentrylab.telegram.adapter.init')
    def test_cleanup_conversation(self, mock_init):
        """Test conversation cleanup."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Verify conversation exists
        assert conversation_id in self.adapter._conversations
        assert conversation_id in self.adapter._event_streams
        assert conversation_id in self.adapter._user_message_queues
        
        # Cleanup conversation
        self.adapter.cleanup_conversation(conversation_id)
        
        # Verify conversation is removed
        assert conversation_id not in self.adapter._conversations
        assert conversation_id not in self.adapter._event_streams
        assert conversation_id not in self.adapter._user_message_queues
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_stats(self, mock_init):
        """Test getting adapter statistics."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        # Start some conversations
        conv1 = self.adapter.start_conversation(
            preset_id="debates",
            topic="Topic 1",
            user_id="user123"
        )
        
        conv2 = self.adapter.start_conversation(
            preset_id="standup_club",
            topic="Topic 2",
            user_id="user456"
        )
        
        # Pause one conversation
        self.adapter.pause_conversation(conv2)
        
        # Get stats
        stats = self.adapter.get_stats()
        
        assert stats["total_conversations"] == 2
        assert stats["active_conversations"] == 1
        assert stats["paused_conversations"] == 1
        assert stats["stopped_conversations"] == 0
        assert stats["error_conversations"] == 0
        assert stats["max_concurrent"] == 10
    
    @patch('agentrylab.telegram.adapter.init')
    def test_start_conversation_with_resume_false(self, mock_init):
        """Test starting conversation with resume=False."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123",
            resume=False
        )
        
        assert conversation_id is not None
        mock_init.assert_called_once_with(
            "debates",
            experiment_id=conversation_id,
            prompt="Test topic",
            resume=False
        )
    
    @patch('agentrylab.telegram.adapter.init')
    def test_start_conversation_with_resume_true(self, mock_init):
        """Test starting conversation with resume=True (default)."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123",
            resume=True
        )
        
        assert conversation_id is not None
        mock_init.assert_called_once_with(
            "debates",
            experiment_id=conversation_id,
            prompt="Test topic",
            resume=True
        )
    
    @patch('agentrylab.persistence.store.Store')
    def test_can_resume_conversation_true(self, mock_store_class):
        """Test can_resume_conversation returns True when checkpoint exists."""
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.load_checkpoint.return_value = {
            "thread_id": "test-123",
            "iter": 5,
            "history": []
        }
        
        result = self.adapter.can_resume_conversation("test-123")
        assert result is True
        mock_store.load_checkpoint.assert_called_once_with("test-123")
    
    @patch('agentrylab.persistence.store.Store')
    def test_can_resume_conversation_false_no_checkpoint(self, mock_store_class):
        """Test can_resume_conversation returns False when no checkpoint exists."""
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.load_checkpoint.side_effect = Exception("No checkpoint")
        
        result = self.adapter.can_resume_conversation("test-123")
        assert result is False
    
    @patch('agentrylab.persistence.store.Store')
    def test_can_resume_conversation_false_pickled(self, mock_store_class):
        """Test can_resume_conversation returns False for pickled checkpoints."""
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.load_checkpoint.return_value = {"_pickled": "some_data"}
        
        result = self.adapter.can_resume_conversation("test-123")
        assert result is False


@pytest.mark.asyncio
class TestTelegramAdapterAsync:
    """Test async functionality of TelegramAdapter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = TelegramAdapter(max_concurrent_conversations=10)
    
    @patch('agentrylab.telegram.adapter.init')
    async def test_stream_events(self, mock_init):
        """Test streaming events from conversation."""
        # Mock lab with async stream
        mock_lab = Mock()
        mock_lab.stream = AsyncMock()
        async def mock_stream():
            yield {
                "content": "Hello from agent",
                "iter": 0,
                "agent_id": "pro",
                "role": "agent",
                "metadata": {}
            }
        mock_lab.stream.return_value = mock_stream()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Start streaming
        events = []
        async for event in self.adapter.stream_events(conversation_id):
            events.append(event)
            if len(events) >= 1:  # Limit to prevent infinite loop
                break
        
        assert len(events) >= 1
        assert events[0].event_type == "conversation_started"
    
    @patch('agentrylab.telegram.adapter.init')
    async def test_stream_events_not_found(self, mock_init):
        """Test streaming events from non-existent conversation."""
        with pytest.raises(Exception):  # Should raise ConversationNotFoundError
            async for event in self.adapter.stream_events("non-existent"):
                pass
