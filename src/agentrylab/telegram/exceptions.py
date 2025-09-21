"""Custom exceptions for Telegram integration."""


class ConversationError(Exception):
    """Base exception for conversation-related errors."""
    pass


class ConversationNotFoundError(ConversationError):
    """Raised when a conversation is not found."""
    pass


class ConversationAlreadyExistsError(ConversationError):
    """Raised when trying to create a conversation that already exists."""
    pass


class ConversationNotActiveError(ConversationError):
    """Raised when trying to perform an action on an inactive conversation."""
    pass


class InvalidPresetError(ConversationError):
    """Raised when an invalid preset is specified."""
    pass


class UserInputError(ConversationError):
    """Raised when there's an error with user input."""
    pass


class StreamingError(ConversationError):
    """Raised when there's an error with event streaming."""
    pass
