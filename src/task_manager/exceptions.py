"""Domain-specific exceptions for the task management application."""


class TaskManagerError(Exception):
    """Base exception for expected application errors."""


class TaskValidationError(TaskManagerError, ValueError):
    """Raised when task or user data violates domain rules."""


class TaskNotFoundError(TaskManagerError, LookupError):
    """Raised when a requested task does not exist."""


class UserNotFoundError(TaskManagerError, LookupError):
    """Raised when a requested user does not exist."""


class InvalidStatusTransitionError(TaskManagerError):
    """Raised when a task status transition is not allowed."""


class ImportFormatError(TaskManagerError):
    """Raised when an input file cannot be parsed in strict mode."""


class ConfigurationError(TaskManagerError):
    """Raised when application configuration is invalid or unavailable."""
