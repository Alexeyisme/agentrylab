"""Main Telegram adapter for AgentryLab integration."""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from agentrylab import init
from agentrylab.lab import Lab

from .exceptions import (
    ConversationAlreadyExistsError,
    ConversationNotFoundError,
    ConversationNotActiveError,
    InvalidPresetError,
    StreamingError,
)
from .models import (
    ConversationEvent,
    ConversationState,
    ConversationStatus,
    UserMessage,
)

logger = logging.getLogger(__name__)


class TelegramAdapter:
    """Adapter for integrating AgentryLab with external interfaces like Telegram.
    
    This class provides a clean API for managing conversations, streaming events,
    and handling user input in real-time.
    """
    
    def __init__(self, *, max_concurrent_conversations: int = 100):
        """Initialize the Telegram adapter.
        
        Args:
            max_concurrent_conversations: Maximum number of concurrent conversations
        """
        self.max_concurrent_conversations = max_concurrent_conversations
        self._conversations: Dict[str, ConversationState] = {}
        self._event_streams: Dict[str, asyncio.Queue] = {}
        self._user_message_queues: Dict[str, asyncio.Queue] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        
    def start_conversation(
        self, 
        preset_id: str, 
        topic: str, 
        user_id: str,
        conversation_id: Optional[str] = None,
        resume: bool = True
    ) -> str:
        """Start a new conversation.
        
        Args:
            preset_id: ID of the preset to use
            topic: Topic for the conversation
            user_id: ID of the user starting the conversation
            conversation_id: Optional custom conversation ID
            resume: Whether to resume from existing checkpoint if available
            
        Returns:
            The conversation ID
            
        Raises:
            ConversationAlreadyExistsError: If conversation ID already exists
            InvalidPresetError: If preset is not found or invalid
        """
        if conversation_id is None:
            conversation_id = str(uuid.uuid4())
            
        if conversation_id in self._conversations:
            raise ConversationAlreadyExistsError(f"Conversation {conversation_id} already exists")
            
        if len(self._conversations) >= self.max_concurrent_conversations:
            raise RuntimeError("Maximum concurrent conversations reached")
            
        try:
            # Initialize the lab with the preset
            lab = init(
                preset_id,
                experiment_id=conversation_id,
                prompt=topic,
                resume=resume
            )
            
            # Create conversation state
            state = ConversationState(
                conversation_id=conversation_id,
                preset_id=preset_id,
                topic=topic,
                user_id=user_id,
                status=ConversationStatus.ACTIVE,
                lab_instance=lab,
            )
            
            # Store conversation
            self._conversations[conversation_id] = state
            
            # Create event stream and user message queue
            self._event_streams[conversation_id] = asyncio.Queue()
            self._user_message_queues[conversation_id] = asyncio.Queue()
            
            # Note: Conversation task will be started when first accessed via async methods
            
            logger.info(f"Started conversation {conversation_id} with preset {preset_id}")
            return conversation_id
            
        except Exception as e:
            logger.error(f"Failed to start conversation {conversation_id}: {e}")
            raise InvalidPresetError(f"Failed to initialize preset {preset_id}: {e}")
    
    def get_conversation_state(self, conversation_id: str) -> ConversationState:
        """Get the state of a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            The conversation state
            
        Raises:
            ConversationNotFoundError: If conversation is not found
        """
        if conversation_id not in self._conversations:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            
        return self._conversations[conversation_id]
    
    def can_resume_conversation(self, conversation_id: str) -> bool:
        """Check if a conversation can be resumed from checkpoint.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            True if conversation can be resumed, False otherwise
        """
        try:
            # Try to load checkpoint to see if it exists
            from agentrylab.persistence.store import Store
            store = Store()
            snapshot = store.load_checkpoint(conversation_id)
            return isinstance(snapshot, dict) and snapshot and "_pickled" not in snapshot
        except Exception:
            return False
    
    def post_user_message(self, conversation_id: str, message: str, user_id: str) -> None:
        """Post a user message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            message: The user message
            user_id: ID of the user
            
        Raises:
            ConversationNotFoundError: If conversation is not found
            ConversationNotActiveError: If conversation is not active
        """
        if conversation_id not in self._conversations:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            
        state = self._conversations[conversation_id]
        if state.status != ConversationStatus.ACTIVE:
            raise ConversationNotActiveError(f"Conversation {conversation_id} is not active")
            
        # Create user message
        user_msg = UserMessage(
            conversation_id=conversation_id,
            user_id=user_id,
            content=message,
        )
        
        # Ensure conversation task is started
        self._ensure_conversation_task_started(conversation_id)
        
        # Add to queue
        try:
            self._user_message_queues[conversation_id].put_nowait(user_msg)
            logger.info(f"Posted user message to conversation {conversation_id}")
        except asyncio.QueueFull:
            logger.warning(f"User message queue full for conversation {conversation_id}")
            raise RuntimeError("User message queue is full")
    
    def _ensure_conversation_task_started(self, conversation_id: str) -> None:
        """Ensure the conversation task is started.
        
        Args:
            conversation_id: ID of the conversation
        """
        if conversation_id not in self._running_tasks:
            try:
                task = asyncio.create_task(self._run_conversation(conversation_id))
                self._running_tasks[conversation_id] = task
            except RuntimeError:
                # No event loop running, task will be started later
                pass

    async def stream_events(self, conversation_id: str) -> AsyncIterator[ConversationEvent]:
        """Stream events from a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Yields:
            Conversation events
            
        Raises:
            ConversationNotFoundError: If conversation is not found
            StreamingError: If streaming fails
        """
        if conversation_id not in self._conversations:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            
        if conversation_id not in self._event_streams:
            raise StreamingError(f"No event stream for conversation {conversation_id}")
            
        # Ensure conversation task is started
        self._ensure_conversation_task_started(conversation_id)
            
        event_queue = self._event_streams[conversation_id]
        
        try:
            while True:
                # Check if conversation is still active
                state = self._conversations.get(conversation_id)
                if not state or state.status in [ConversationStatus.STOPPED, ConversationStatus.ERROR]:
                    break
                    
                try:
                    # Wait for next event with timeout
                    event = await asyncio.wait_for(event_queue.get(), timeout=1.0)
                    yield event
                    
                    # Mark task as done
                    event_queue.task_done()
                    
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive
                    continue
                    
        except Exception as e:
            logger.error(f"Error streaming events for conversation {conversation_id}: {e}")
            raise StreamingError(f"Failed to stream events: {e}")
    
    def pause_conversation(self, conversation_id: str) -> None:
        """Pause a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Raises:
            ConversationNotFoundError: If conversation is not found
        """
        if conversation_id not in self._conversations:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            
        state = self._conversations[conversation_id]
        if state.status == ConversationStatus.ACTIVE:
            state.status = ConversationStatus.PAUSED
            logger.info(f"Paused conversation {conversation_id}")
    
    def resume_conversation(self, conversation_id: str) -> None:
        """Resume a paused conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Raises:
            ConversationNotFoundError: If conversation is not found
        """
        if conversation_id not in self._conversations:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            
        state = self._conversations[conversation_id]
        if state.status == ConversationStatus.PAUSED:
            state.status = ConversationStatus.ACTIVE
            logger.info(f"Resumed conversation {conversation_id}")
    
    def stop_conversation(self, conversation_id: str) -> None:
        """Stop a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Raises:
            ConversationNotFoundError: If conversation is not found
        """
        if conversation_id not in self._conversations:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            
        state = self._conversations[conversation_id]
        state.status = ConversationStatus.STOPPED
        
        # Cancel running task
        if conversation_id in self._running_tasks:
            task = self._running_tasks[conversation_id]
            if not task.done():
                task.cancel()
            del self._running_tasks[conversation_id]
            
        logger.info(f"Stopped conversation {conversation_id}")
    
    def list_user_conversations(self, user_id: str) -> List[ConversationState]:
        """List all conversations for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            List of conversation states
        """
        return [
            state for state in self._conversations.values()
            if state.user_id == user_id
        ]
    
    def get_conversation_history(self, conversation_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get conversation history from the lab instance.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of history entries to return
            
        Returns:
            List of conversation history entries
            
        Raises:
            ConversationNotFoundError: If conversation is not found
        """
        if conversation_id not in self._conversations:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            
        state = self._conversations[conversation_id]
        lab = state.lab_instance
        
        # Get history from lab state
        history = getattr(lab.state, 'history', [])
        return history[-limit:] if limit > 0 else history
    
    def get_conversation_transcript(self, conversation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get conversation transcript from persistence store.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of transcript entries to return
            
        Returns:
            List of transcript entries
            
        Raises:
            ConversationNotFoundError: If conversation is not found
        """
        if conversation_id not in self._conversations:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            
        try:
            # Get transcript from store
            from agentrylab.persistence.store import Store
            store = Store()
            transcript = store.read_transcript(conversation_id, limit=limit)
            return transcript
        except Exception as e:
            logger.error(f"Failed to read transcript for conversation {conversation_id}: {e}")
            return []
    
    def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """Get conversation summary if available.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Conversation summary or None if not available
            
        Raises:
            ConversationNotFoundError: If conversation is not found
        """
        if conversation_id not in self._conversations:
            raise ConversationNotFoundError(f"Conversation {conversation_id} not found")
            
        state = self._conversations[conversation_id]
        lab = state.lab_instance
        
        # Get running summary from lab state
        return getattr(lab.state, 'running_summary', None)
    
    async def _run_conversation(self, conversation_id: str) -> None:
        """Run a conversation in the background.
        
        Args:
            conversation_id: ID of the conversation
        """
        try:
            state = self._conversations[conversation_id]
            lab = state.lab_instance
            event_queue = self._event_streams[conversation_id]
            user_queue = self._user_message_queues[conversation_id]
            
            # Send conversation started event
            await self._emit_event(conversation_id, "conversation_started", "Conversation started")
            
            # Run the lab with streaming
            async for event in lab.stream(rounds=10):  # Default to 10 rounds
                # Check if conversation is still active
                if state.status != ConversationStatus.ACTIVE:
                    break
                    
                # Convert lab event to conversation event
                conv_event = ConversationEvent(
                    conversation_id=conversation_id,
                    event_type="agent_message",
                    content=str(event.get("content", "")),
                    metadata=event.get("metadata", {}),
                    iteration=event.get("iter", 0),
                    agent_id=event.get("agent_id"),
                    role=event.get("role"),
                )
                
                await event_queue.put(conv_event)
                
                # Check for user input
                try:
                    user_msg = user_queue.get_nowait()
                    if not user_msg.processed:
                        # Post user message to lab
                        lab.post_user_message(user_msg.content, user_id=user_msg.user_id)
                        user_msg.processed = True
                        
                        # Emit user message event
                        await self._emit_event(
                            conversation_id, 
                            "user_message", 
                            user_msg.content,
                            metadata={"user_id": user_msg.user_id}
                        )
                except asyncio.QueueEmpty:
                    pass
                    
            # Send conversation completed event
            await self._emit_event(conversation_id, "conversation_completed", "Conversation completed")
            state.status = ConversationStatus.COMPLETED
            
        except asyncio.CancelledError:
            logger.info(f"Conversation {conversation_id} was cancelled")
            state.status = ConversationStatus.STOPPED
        except Exception as e:
            logger.error(f"Error running conversation {conversation_id}: {e}")
            state.status = ConversationStatus.ERROR
            await self._emit_event(conversation_id, "error", f"Error: {e}")
        finally:
            # Cleanup
            if conversation_id in self._running_tasks:
                del self._running_tasks[conversation_id]
    
    async def _emit_event(
        self, 
        conversation_id: str, 
        event_type: str, 
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Emit an event to a conversation's event stream.
        
        Args:
            conversation_id: ID of the conversation
            event_type: Type of the event
            content: Event content
            metadata: Optional event metadata
        """
        if conversation_id not in self._event_streams:
            return
            
        event = ConversationEvent(
            conversation_id=conversation_id,
            event_type=event_type,
            content=content,
            metadata=metadata or {},
        )
        
        try:
            await self._event_streams[conversation_id].put(event)
        except Exception as e:
            logger.error(f"Failed to emit event for conversation {conversation_id}: {e}")
    
    def cleanup_conversation(self, conversation_id: str) -> None:
        """Clean up resources for a conversation.
        
        Args:
            conversation_id: ID of the conversation
        """
        # Stop conversation if still running
        if conversation_id in self._conversations:
            self.stop_conversation(conversation_id)
            
        # Clean up queues
        if conversation_id in self._event_streams:
            del self._event_streams[conversation_id]
        if conversation_id in self._user_message_queues:
            del self._user_message_queues[conversation_id]
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            
        logger.info(f"Cleaned up conversation {conversation_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics.
        
        Returns:
            Dictionary with adapter statistics
        """
        active_conversations = sum(
            1 for state in self._conversations.values()
            if state.status == ConversationStatus.ACTIVE
        )
        
        return {
            "total_conversations": len(self._conversations),
            "active_conversations": active_conversations,
            "paused_conversations": sum(
                1 for state in self._conversations.values()
                if state.status == ConversationStatus.PAUSED
            ),
            "stopped_conversations": sum(
                1 for state in self._conversations.values()
                if state.status == ConversationStatus.STOPPED
            ),
            "error_conversations": sum(
                1 for state in self._conversations.values()
                if state.status == ConversationStatus.ERROR
            ),
            "max_concurrent": self.max_concurrent_conversations,
        }
