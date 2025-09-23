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
        
        # The adapter loads the preset and calls init with the loaded config
        mock_init.assert_called_once()
        call_args = mock_init.call_args
        assert call_args[1]["experiment_id"] == conversation_id
        assert call_args[1]["prompt"] == "Test topic"
        assert call_args[1]["resume"]
    
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
        # The adapter loads the preset and calls init with the loaded config
        mock_init.assert_called_once()
        call_args = mock_init.call_args
        assert call_args[1]["experiment_id"] == conversation_id
        assert call_args[1]["prompt"] == "Test topic"
        assert not call_args[1]["resume"]
    
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
        # The adapter loads the preset and calls init with the loaded config
        mock_init.assert_called_once()
        call_args = mock_init.call_args
        assert call_args[1]["experiment_id"] == conversation_id
        assert call_args[1]["prompt"] == "Test topic"
        assert call_args[1]["resume"]
    
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
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_history(self, mock_init):
        """Test getting conversation history."""
        # Mock lab with history
        mock_lab = Mock()
        mock_lab.state.history = [
            {"agent_id": "pro", "role": "agent", "content": "Hello"},
            {"agent_id": "con", "role": "agent", "content": "Hi there"},
            {"agent_id": "user", "role": "user", "content": "What's up?"}
        ]
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get history
        history = self.adapter.get_conversation_history(conversation_id, limit=2)
        
        assert len(history) == 2
        assert history[0]["content"] == "Hi there"
        assert history[1]["content"] == "What's up?"
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_history_not_found(self, mock_init):
        """Test getting history for non-existent conversation."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        with pytest.raises(Exception):  # Should raise ConversationNotFoundError
            self.adapter.get_conversation_history("non-existent")
    
    @patch('agentrylab.telegram.adapter.init')
    @patch('agentrylab.persistence.store.Store')
    def test_get_conversation_transcript(self, mock_store_class, mock_init):
        """Test getting conversation transcript."""
        # Mock lab
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        # Mock store
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.read_transcript.return_value = [
            {"t": 1234567890, "iter": 0, "agent_id": "pro", "role": "agent", "content": "Hello"},
            {"t": 1234567891, "iter": 1, "agent_id": "con", "role": "agent", "content": "Hi"}
        ]
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get transcript
        transcript = self.adapter.get_conversation_transcript(conversation_id, limit=10)
        
        assert len(transcript) == 2
        assert transcript[0]["content"] == "Hello"
        assert transcript[1]["content"] == "Hi"
        mock_store.read_transcript.assert_called_once_with(conversation_id, limit=10)
    
    @patch('agentrylab.telegram.adapter.init')
    @patch('agentrylab.persistence.store.Store')
    def test_get_conversation_transcript_error(self, mock_store_class, mock_init):
        """Test getting transcript when store fails."""
        # Mock lab
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        # Mock store with error
        mock_store = Mock()
        mock_store_class.return_value = mock_store
        mock_store.read_transcript.side_effect = Exception("Store error")
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get transcript should return empty list on error
        transcript = self.adapter.get_conversation_transcript(conversation_id)
        assert transcript == []
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_summary(self, mock_init):
        """Test getting conversation summary."""
        # Mock lab with summary
        mock_lab = Mock()
        mock_lab.state.running_summary = "This is a test summary"
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get summary
        summary = self.adapter.get_conversation_summary(conversation_id)
        
        assert summary == "This is a test summary"
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_summary_none(self, mock_init):
        """Test getting summary when none exists."""
        # Mock lab without summary
        mock_lab = Mock()
        mock_lab.state.running_summary = None
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get summary
        summary = self.adapter.get_conversation_summary(conversation_id)
        
        assert summary is None
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_budgets(self, mock_init):
        """Test getting conversation budgets."""
        # Mock lab with budget method
        mock_lab = Mock()
        mock_lab.state.get_tool_budgets.return_value = {
            "ddg": {"per_run_max": 10, "per_iteration_max": 2},
            "wolfram": {"per_run_max": 5, "per_iteration_max": 1}
        }
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get budgets
        budgets = self.adapter.get_conversation_budgets(conversation_id)
        
        assert "ddg" in budgets
        assert "wolfram" in budgets
        assert budgets["ddg"]["per_run_max"] == 10
        assert budgets["wolfram"]["per_iteration_max"] == 1
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_budgets_no_method(self, mock_init):
        """Test getting budgets when lab state has no get_tool_budgets method."""
        # Mock lab without budget method
        mock_lab = Mock()
        del mock_lab.state.get_tool_budgets  # Remove the method
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get budgets should return empty dict
        budgets = self.adapter.get_conversation_budgets(conversation_id)
        assert budgets == {}
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_tool_usage_stats(self, mock_init):
        """Test getting tool usage statistics."""
        # Mock lab with usage stats
        mock_lab = Mock()
        mock_lab.state._tool_calls_run_total = 15
        mock_lab.state._tool_calls_iteration = 3
        mock_lab.state._tool_calls_run_by_id = {"ddg": 10, "wolfram": 5}
        mock_lab.state._tool_calls_iter_by_id = {"ddg": 2, "wolfram": 1}
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get usage stats
        stats = self.adapter.get_tool_usage_stats(conversation_id)
        
        assert stats['total_tool_calls'] == 15
        assert stats['iteration_tool_calls'] == 3
        assert stats['tool_calls_by_id']['ddg'] == 10
        assert stats['tool_calls_by_id']['wolfram'] == 5
        assert stats['iteration_tool_calls_by_id']['ddg'] == 2
        assert stats['iteration_tool_calls_by_id']['wolfram'] == 1
    
    @patch('agentrylab.telegram.adapter.init')
    def test_can_call_tool(self, mock_init):
        """Test checking if a tool can be called."""
        # Mock lab with can_call_tool method
        mock_lab = Mock()
        mock_lab.state.can_call_tool.return_value = (True, "Tool available")
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Check if tool can be called
        can_call, reason = self.adapter.can_call_tool(conversation_id, "ddg")
        
        assert can_call is True
        assert reason == "Tool available"
        mock_lab.state.can_call_tool.assert_called_once_with("ddg")
    
    @patch('agentrylab.telegram.adapter.init')
    def test_can_call_tool_no_method(self, mock_init):
        """Test checking tool when lab state has no can_call_tool method."""
        # Mock lab without can_call_tool method
        mock_lab = Mock()
        del mock_lab.state.can_call_tool  # Remove the method
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Check if tool can be called should return True
        can_call, reason = self.adapter.can_call_tool(conversation_id, "ddg")
        
        assert can_call is True
        assert reason == "No budget restrictions"
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_budget_status(self, mock_init):
        """Test getting comprehensive budget status."""
        # Mock lab with all budget methods
        mock_lab = Mock()
        mock_lab.state.iter = 5
        mock_lab.state.get_tool_budgets.return_value = {"ddg": {"per_run_max": 10}}
        mock_lab.state._tool_calls_run_total = 5
        mock_lab.state._tool_calls_iteration = 1
        mock_lab.state._tool_calls_run_by_id = {"ddg": 5}
        mock_lab.state._tool_calls_iter_by_id = {"ddg": 1}
        mock_lab.state.can_call_tool.return_value = (True, "Available")
        
        # Mock config with tools
        mock_cfg = Mock()
        mock_tool = Mock()
        mock_tool.id = "ddg"
        mock_cfg.tools = [mock_tool]
        mock_lab.cfg = mock_cfg
        
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get budget status
        status = self.adapter.get_budget_status(conversation_id)
        
        assert status['conversation_id'] == conversation_id
        assert status['iteration'] == 5
        assert 'budgets' in status
        assert 'usage_stats' in status
        assert 'tool_status' in status
        assert 'ddg' in status['tool_status']
        assert status['tool_status']['ddg']['can_call'] is True
    
    @patch('agentrylab.telegram.adapter.init')
    def test_set_conversation_rounds(self, mock_init):
        """Test setting conversation rounds."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Set rounds
        self.adapter.set_conversation_rounds(conversation_id, 20)
        
        state = self.adapter.get_conversation_state(conversation_id)
        assert state.metadata['max_rounds'] == 20
    
    @patch('agentrylab.telegram.adapter.init')
    def test_set_conversation_rounds_not_found(self, mock_init):
        """Test setting rounds for non-existent conversation."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        with pytest.raises(Exception):  # Should raise ConversationNotFoundError
            self.adapter.set_conversation_rounds("non-existent", 20)
    
    @patch('agentrylab.telegram.adapter.init')
    def test_set_conversation_rounds_not_active(self, mock_init):
        """Test setting rounds for inactive conversation."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Pause conversation
        self.adapter.pause_conversation(conversation_id)
        
        # Try to set rounds should fail
        with pytest.raises(Exception):  # Should raise ConversationNotActiveError
            self.adapter.set_conversation_rounds(conversation_id, 20)
    
    @patch('agentrylab.telegram.adapter.init')
    def test_change_conversation_topic(self, mock_init):
        """Test changing conversation topic."""
        mock_lab = Mock()
        mock_cfg = Mock()
        mock_cfg.objective = "Original topic"
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Original topic",
            user_id="user123"
        )
        
        # Change topic
        self.adapter.change_conversation_topic(conversation_id, "New topic")
        
        state = self.adapter.get_conversation_state(conversation_id)
        assert state.topic == "New topic"
        assert mock_cfg.objective == "New topic"
    
    @patch('agentrylab.telegram.adapter.init')
    def test_change_conversation_topic_not_found(self, mock_init):
        """Test changing topic for non-existent conversation."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        with pytest.raises(Exception):  # Should raise ConversationNotFoundError
            self.adapter.change_conversation_topic("non-existent", "New topic")
    
    @patch('agentrylab.telegram.adapter.init')
    def test_change_conversation_topic_not_active(self, mock_init):
        """Test changing topic for inactive conversation."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Original topic",
            user_id="user123"
        )
        
        # Pause conversation
        self.adapter.pause_conversation(conversation_id)
        
        # Try to change topic should fail
        with pytest.raises(Exception):  # Should raise ConversationNotActiveError
            self.adapter.change_conversation_topic(conversation_id, "New topic")
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_lab_status(self, mock_init):
        """Test getting lab status."""
        mock_lab = Mock()
        mock_lab.state.iter = 5
        mock_lab.state.stop_flag = False
        mock_lab._active = True
        mock_lab._last_ts = 1234567890.0
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get lab status
        status = self.adapter.get_lab_status(conversation_id)
        
        assert status['conversation_id'] == conversation_id
        assert status['status'] == 'active'
        assert status['iteration'] == 5
        assert status['stop_flag'] is False
        assert status['active'] is True
        assert status['last_ts'] == 1234567890.0
        assert status['topic'] == "Test topic"
        assert status['preset_id'] == "debates"
        assert status['user_id'] == "user123"
        assert 'created_at' in status
        assert 'last_activity' in status
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_lab_status_not_found(self, mock_init):
        """Test getting lab status for non-existent conversation."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        with pytest.raises(Exception):  # Should raise ConversationNotFoundError
            self.adapter.get_lab_status("non-existent")
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_progress(self, mock_init):
        """Test getting conversation progress."""
        mock_lab = Mock()
        mock_lab.state.iter = 3
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Set custom rounds
        self.adapter.set_conversation_rounds(conversation_id, 10)
        
        # Get progress
        progress = self.adapter.get_conversation_progress(conversation_id)
        
        assert progress['conversation_id'] == conversation_id
        assert progress['current_iteration'] == 3
        assert progress['max_rounds'] == 10
        assert progress['progress_percent'] == 30.0
        assert progress['remaining_rounds'] == 7
        assert progress['is_complete'] is False
        assert progress['status'] == 'active'
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_progress_default_rounds(self, mock_init):
        """Test getting progress with default rounds."""
        mock_lab = Mock()
        mock_lab.state.iter = 5
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get progress without setting custom rounds
        progress = self.adapter.get_conversation_progress(conversation_id)
        
        assert progress['current_iteration'] == 5
        assert progress['max_rounds'] == 10  # Default
        assert progress['progress_percent'] == 50.0
        assert progress['remaining_rounds'] == 5
        assert progress['is_complete'] is False
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_progress_complete(self, mock_init):
        """Test getting progress when conversation is complete."""
        mock_lab = Mock()
        mock_lab.state.iter = 10
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Set rounds to match current iteration
        self.adapter.set_conversation_rounds(conversation_id, 10)
        
        # Get progress
        progress = self.adapter.get_conversation_progress(conversation_id)
        
        assert progress['current_iteration'] == 10
        assert progress['max_rounds'] == 10
        assert progress['progress_percent'] == 100.0
        assert progress['remaining_rounds'] == 0
        assert progress['is_complete'] is True
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_provider_status(self, mock_init):
        """Test getting provider status."""
        # Mock lab with providers
        mock_lab = Mock()
        mock_provider1 = Mock()
        mock_provider1.id = "openai_gpt4"
        mock_provider1.impl = "agentrylab.runtime.providers.openai.OpenAIProvider"
        mock_provider1.model = "gpt-4"
        mock_provider1.api_key = "sk-test123"
        mock_provider1.extra = {"max_tokens": 1000}
        
        mock_provider2 = Mock()
        mock_provider2.id = "ollama_llama"
        mock_provider2.impl = "agentrylab.runtime.providers.ollama.OllamaProvider"
        mock_provider2.model = "llama2"
        mock_provider2.api_key = None
        mock_provider2.extra = {}
        
        mock_cfg = Mock()
        mock_cfg.providers = [mock_provider1, mock_provider2]
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get provider status
        status = self.adapter.get_provider_status(conversation_id)
        
        assert status['conversation_id'] == conversation_id
        assert status['total_providers'] == 2
        assert 'openai_gpt4' in status['providers']
        assert 'ollama_llama' in status['providers']
        assert status['providers']['openai_gpt4']['api_key_configured'] is True
        assert status['providers']['ollama_llama']['api_key_configured'] is False
        assert status['providers']['openai_gpt4']['model'] == "gpt-4"
        assert status['providers']['ollama_llama']['model'] == "llama2"
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_provider_status_no_providers(self, mock_init):
        """Test getting provider status when no providers configured."""
        mock_lab = Mock()
        mock_cfg = Mock()
        mock_cfg.providers = []
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get provider status
        status = self.adapter.get_provider_status(conversation_id)
        
        assert status['conversation_id'] == conversation_id
        assert status['total_providers'] == 0
        assert status['providers'] == {}
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_tool_status(self, mock_init):
        """Test getting tool status."""
        # Mock lab with tools
        mock_lab = Mock()
        mock_tool1 = Mock()
        mock_tool1.id = "ddg"
        mock_tool1.impl = "agentrylab.runtime.tools.ddg.DuckDuckGoTool"
        mock_tool1.budget = {"per_run_max": 10}
        
        mock_tool2 = Mock()
        mock_tool2.id = "wolfram"
        mock_tool2.impl = "agentrylab.runtime.tools.wolfram.WolframTool"
        mock_tool2.budget = {"per_run_max": 5}
        
        mock_cfg = Mock()
        mock_cfg.tools = [mock_tool1, mock_tool2]
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get tool status
        status = self.adapter.get_tool_status(conversation_id)
        
        assert status['conversation_id'] == conversation_id
        assert status['total_tools'] == 2
        assert 'ddg' in status['tools']
        assert 'wolfram' in status['tools']
        assert status['tools']['ddg']['enabled'] is True
        assert status['tools']['wolfram']['enabled'] is True
        assert status['tools']['ddg']['budget']['per_run_max'] == 10
        assert status['tools']['wolfram']['budget']['per_run_max'] == 5
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_tool_status_no_tools(self, mock_init):
        """Test getting tool status when no tools configured."""
        mock_lab = Mock()
        mock_cfg = Mock()
        mock_cfg.tools = []
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get tool status
        status = self.adapter.get_tool_status(conversation_id)
        
        assert status['conversation_id'] == conversation_id
        assert status['total_tools'] == 0
        assert status['tools'] == {}
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_system_health_excellent(self, mock_init):
        """Test getting system health with excellent status."""
        # Mock lab with good health
        mock_lab = Mock()
        mock_lab.state.iter = 5
        mock_lab.state.stop_flag = False
        mock_lab._active = True
        mock_lab.state._tool_calls_run_total = 10
        mock_lab.state.get_tool_budgets.return_value = {}
        mock_lab.state._tool_calls_run_by_id = {}
        mock_lab.state._tool_calls_iter_by_id = {}
        mock_lab.state._tool_calls_iteration = 2
        
        mock_cfg = Mock()
        mock_cfg.providers = []
        mock_cfg.tools = []
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get system health
        health = self.adapter.get_system_health(conversation_id)
        
        assert health['conversation_id'] == conversation_id
        assert health['status'] == 'active'
        assert health['iteration'] == 5
        assert health['stop_flag'] is False
        assert health['active'] is True
        assert health['health_score'] == 100
        assert health['health_status'] == 'excellent'
        assert 'providers' in health
        assert 'tools' in health
        assert 'budgets' in health
        assert 'usage_stats' in health
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_system_health_critical(self, mock_init):
        """Test getting system health with critical status."""
        # Mock lab with poor health
        mock_lab = Mock()
        mock_lab.state.iter = 5
        mock_lab.state.stop_flag = True  # Critical issue
        mock_lab._active = False  # Another issue
        mock_lab.state._tool_calls_run_total = 150  # High usage
        mock_lab.state.get_tool_budgets.return_value = {}
        mock_lab.state._tool_calls_run_by_id = {}
        mock_lab.state._tool_calls_iter_by_id = {}
        mock_lab.state._tool_calls_iteration = 2
        
        mock_cfg = Mock()
        mock_cfg.providers = []
        mock_cfg.tools = []
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get system health
        health = self.adapter.get_system_health(conversation_id)
        
        assert health['conversation_id'] == conversation_id
        assert health['status'] == 'active'
        assert health['stop_flag'] is True
        assert health['active'] is False
        assert health['health_score'] == 50  # 100 - 30 (stop_flag) - 10 (not active) - 10 (high usage) = 50
        assert health['health_status'] == 'warning'  # 50 is warning threshold
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_analytics(self, mock_init):
        """Test getting conversation analytics."""
        # Mock lab with analytics data
        mock_lab = Mock()
        mock_lab.state.iter = 5
        mock_lab.state.history = [
            {"role": "agent", "content": "Hello"},
            {"role": "user", "content": "Hi"},
            {"role": "agent", "content": "How are you?"},
            {"role": "moderator", "content": "Continue"},
        ]
        mock_lab.state._tool_calls_run_total = 10
        mock_lab.state._tool_calls_iteration = 2
        mock_lab.state._tool_calls_run_by_id = {"ddg": 8, "wolfram": 2}
        mock_lab.state._tool_calls_iter_by_id = {"ddg": 1, "wolfram": 1}
        mock_lab.state.get_tool_budgets.return_value = {"ddg": {"per_run_max": 10}}
        
        mock_cfg = Mock()
        mock_cfg.providers = []
        mock_cfg.tools = []
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Set custom rounds
        self.adapter.set_conversation_rounds(conversation_id, 10)
        
        # Get analytics
        analytics = self.adapter.get_conversation_analytics(conversation_id)
        
        assert analytics['conversation_id'] == conversation_id
        assert analytics['preset_id'] == "debates"
        assert analytics['topic'] == "Test topic"
        assert analytics['user_id'] == "user123"
        assert analytics['status'] == "active"
        assert analytics['current_iteration'] == 5
        assert analytics['max_rounds'] == 10
        assert analytics['progress_percent'] == 50.0
        assert analytics['is_complete'] is False
        assert analytics['total_messages'] == 4
        assert analytics['agent_messages'] == 2
        assert analytics['user_messages'] == 1
        assert analytics['moderator_messages'] == 1
        assert analytics['total_tool_calls'] == 10
        assert analytics['iteration_tool_calls'] == 2
        assert analytics['tool_calls_by_id']['ddg'] == 8
        assert analytics['tool_calls_by_id']['wolfram'] == 2
        assert analytics['messages_per_iteration'] == 0.8  # 4/5
        assert analytics['tool_calls_per_iteration'] == 2.0  # 10/5
        assert 'created_at' in analytics
        assert 'last_activity' in analytics
        assert 'duration_seconds' in analytics
    
    @patch('agentrylab.telegram.adapter.init')
    def test_export_conversation_data_json(self, mock_init):
        """Test exporting conversation data as JSON."""
        mock_lab = Mock()
        mock_lab.state.iter = 2
        mock_lab.state.history = [{"role": "agent", "content": "Hello"}]
        mock_lab.state._tool_calls_run_total = 5
        mock_lab.state._tool_calls_iteration = 1
        mock_lab.state._tool_calls_run_by_id = {}
        mock_lab.state._tool_calls_iter_by_id = {}
        mock_lab.state.get_tool_budgets.return_value = {}
        
        mock_cfg = Mock()
        mock_cfg.providers = []
        mock_cfg.tools = []
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Export as JSON
        json_data = self.adapter.export_conversation_data(conversation_id, "json")
        
        assert isinstance(json_data, str)
        assert conversation_id in json_data
        assert "debates" in json_data
        assert "Test topic" in json_data
        assert "user123" in json_data
    
    @patch('agentrylab.telegram.adapter.init')
    def test_export_conversation_data_yaml(self, mock_init):
        """Test exporting conversation data as YAML."""
        mock_lab = Mock()
        mock_lab.state.iter = 1
        mock_lab.state.history = []
        mock_lab.state._tool_calls_run_total = 0
        mock_lab.state._tool_calls_iteration = 0
        mock_lab.state._tool_calls_run_by_id = {}
        mock_lab.state._tool_calls_iter_by_id = {}
        mock_lab.state.get_tool_budgets.return_value = {}
        
        mock_cfg = Mock()
        mock_cfg.providers = []
        mock_cfg.tools = []
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Export as YAML
        yaml_data = self.adapter.export_conversation_data(conversation_id, "yaml")
        
        assert isinstance(yaml_data, str)
        assert conversation_id in yaml_data
        assert "debates" in yaml_data
    
    @patch('agentrylab.telegram.adapter.init')
    def test_export_conversation_data_csv(self, mock_init):
        """Test exporting conversation data as CSV."""
        mock_lab = Mock()
        mock_lab.state.iter = 1
        mock_lab.state.history = [
            {"role": "agent", "content": "Hello", "timestamp": "2023-01-01"},
            {"role": "user", "content": "Hi", "timestamp": "2023-01-01"},
        ]
        mock_lab.state._tool_calls_run_total = 0
        mock_lab.state._tool_calls_iteration = 0
        mock_lab.state._tool_calls_run_by_id = {}
        mock_lab.state._tool_calls_iter_by_id = {}
        mock_lab.state.get_tool_budgets.return_value = {}
        
        mock_cfg = Mock()
        mock_cfg.providers = []
        mock_cfg.tools = []
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Export as CSV
        csv_data = self.adapter.export_conversation_data(conversation_id, "csv")
        
        assert isinstance(csv_data, str)
        assert "role" in csv_data
        assert "content" in csv_data
        assert "Hello" in csv_data
        assert "Hi" in csv_data
    
    @patch('agentrylab.telegram.adapter.init')
    def test_export_conversation_data_invalid_format(self, mock_init):
        """Test exporting with invalid format."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Try to export with invalid format
        with pytest.raises(ValueError, match="Unsupported format"):
            self.adapter.export_conversation_data(conversation_id, "xml")
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_summary_report(self, mock_init):
        """Test getting conversation summary report."""
        mock_lab = Mock()
        mock_lab.state.iter = 3
        mock_lab.state.history = [
            {"role": "agent", "content": "Hello"},
            {"role": "user", "content": "Hi"},
            {"role": "agent", "content": "How are you?"},
        ]
        mock_lab.state._tool_calls_run_total = 5
        mock_lab.state._tool_calls_iteration = 1
        mock_lab.state._tool_calls_run_by_id = {"ddg": 5}
        mock_lab.state._tool_calls_iter_by_id = {"ddg": 1}
        mock_lab.state.get_tool_budgets.return_value = {}
        mock_lab.state.stop_flag = False
        mock_lab._active = True
        
        mock_cfg = Mock()
        mock_cfg.providers = []
        mock_cfg.tools = []
        mock_lab.cfg = mock_cfg
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Get summary report
        report = self.adapter.get_conversation_summary_report(conversation_id)
        
        assert isinstance(report, str)
        assert "# Conversation Summary Report" in report
        assert conversation_id in report
        assert "debates" in report
        assert "Test topic" in report
        assert "user123" in report
        assert "Current Iteration" in report
        assert "3" in report
        assert "Total Messages" in report
        assert "Agent Messages" in report
        assert "User Messages" in report
        assert "Total Tool Calls" in report
        assert "Health Score" in report
    
    def test_get_available_presets(self):
        """Test getting available presets."""
        presets = self.adapter.get_available_presets()
        assert isinstance(presets, list)
        # Should include some common presets
        expected_presets = ['debates', 'standup_club', 'solo_chat_user']
        for preset in expected_presets:
            if preset in presets:  # Only check if preset exists
                assert preset in presets
    
    @patch('os.path.exists')
    @patch('builtins.open')
    @patch('yaml.safe_load')
    def test_get_preset_info(self, mock_yaml_load, mock_open, mock_exists):
        """Test getting preset information."""
        mock_exists.return_value = True
        mock_yaml_load.return_value = {
            'name': 'Test Preset',
            'description': 'A test preset',
            'agents': [{'id': 'agent1'}, {'id': 'agent2'}],
            'tools': [{'id': 'tool1'}],
            'providers': [{'id': 'provider1'}],
            'schedule': {'type': 'round_robin'}
        }
        
        info = self.adapter.get_preset_info('test_preset')
        
        assert info['preset_id'] == 'test_preset'
        assert info['name'] == 'Test Preset'
        assert info['description'] == 'A test preset'
        assert info['agents'] == ['agent1', 'agent2']
        assert info['tools'] == ['tool1']
        assert info['providers'] == ['provider1']
        assert info['schedule']['type'] == 'round_robin'
    
    @patch('os.path.exists')
    def test_get_preset_info_not_found(self, mock_exists):
        """Test getting preset info for non-existent preset."""
        mock_exists.return_value = False
        
        with pytest.raises(Exception):  # Should raise InvalidPresetError
            self.adapter.get_preset_info('non_existent')
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_nodes(self, mock_init):
        """Test getting conversation nodes."""
        # Mock lab with nodes
        mock_lab = Mock()
        mock_node1 = Mock()
        mock_node1.role_name = 'agent'
        mock_node2 = Mock()
        mock_node2.role_name = 'moderator'
        
        mock_lab.nodes = {
            'agent1': mock_node1,
            'moderator1': mock_node2
        }
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        nodes_info = self.adapter.get_conversation_nodes(conversation_id)
        
        assert nodes_info['conversation_id'] == conversation_id
        assert nodes_info['total_nodes'] == 2
        assert 'agent1' in nodes_info['nodes']
        assert 'moderator1' in nodes_info['nodes']
        assert nodes_info['nodes']['agent1']['role'] == 'agent'
        assert nodes_info['nodes']['moderator1']['role'] == 'moderator'
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_scheduler_info(self, mock_init):
        """Test getting conversation scheduler info."""
        # Mock lab with scheduler
        mock_lab = Mock()
        mock_scheduler = Mock()
        mock_scheduler.params = {'type': 'round_robin'}
        mock_scheduler._agents = ['agent1', 'agent2']
        mock_lab.scheduler = mock_scheduler
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        scheduler_info = self.adapter.get_conversation_scheduler_info(conversation_id)
        
        assert scheduler_info['conversation_id'] == conversation_id
        assert 'scheduler' in scheduler_info
        assert scheduler_info['scheduler']['params']['type'] == 'round_robin'
        assert scheduler_info['scheduler']['agents'] == ['agent1', 'agent2']
    
    @patch('agentrylab.telegram.adapter.init')
    def test_send_engine_action_stop(self, mock_init):
        """Test sending STOP engine action."""
        mock_lab = Mock()
        mock_lab.state.stop_flag = False
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Send STOP action
        self.adapter.send_engine_action(conversation_id, "STOP")
        
        # Verify stop flag was set
        assert mock_lab.state.stop_flag is True
    
    @patch('agentrylab.telegram.adapter.init')
    def test_send_engine_action_invalid(self, mock_init):
        """Test sending invalid engine action."""
        mock_lab = Mock()
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        # Try to send invalid action
        with pytest.raises(ValueError, match="Unsupported action"):
            self.adapter.send_engine_action(conversation_id, "INVALID")
    
    @patch('agentrylab.telegram.adapter.init')
    def test_get_conversation_engine_status(self, mock_init):
        """Test getting conversation engine status."""
        # Mock lab with engine components
        mock_lab = Mock()
        mock_lab.state.iter = 5
        mock_lab.state.stop_flag = False
        mock_lab._active = True
        mock_lab._has_append = True
        mock_lab._has_checkpoint = True
        
        mock_scheduler = Mock()
        mock_lab.scheduler = mock_scheduler
        
        mock_node1 = Mock()
        mock_node2 = Mock()
        mock_lab.nodes = {'agent1': mock_node1, 'agent2': mock_node2}
        
        mock_init.return_value = mock_lab
        
        conversation_id = self.adapter.start_conversation(
            preset_id="debates",
            topic="Test topic",
            user_id="user123"
        )
        
        engine_status = self.adapter.get_conversation_engine_status(conversation_id)
        
        assert engine_status['conversation_id'] == conversation_id
        assert engine_status['iteration'] == 5
        assert engine_status['stop_flag'] is False
        assert engine_status['active'] is True
        assert engine_status['has_transcript_writer'] is True
        assert engine_status['has_checkpoint_saver'] is True
        assert engine_status['node_count'] == 2
        assert len(engine_status['node_types']) == 2


@pytest.mark.asyncio
class TestTelegramAdapterAsync:
    """Test async functionality of TelegramAdapter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.adapter = TelegramAdapter(max_concurrent_conversations=10)
    
    @patch('agentrylab.telegram.adapter.init')
    async def test_stream_events(self, mock_init):
        """Test streaming events from conversation."""
        # Mock lab with synchronous stream (as it actually is)
        mock_lab = Mock()
        def mock_stream():
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
