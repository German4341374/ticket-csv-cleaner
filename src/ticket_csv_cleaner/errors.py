"""Application-specific exceptions."""


class CleanerError(Exception):
    """Base error for expected CLI failures."""


class ConfigurationError(CleanerError):
    """Raised when a rules file is invalid."""


class InputError(CleanerError):
    """Raised when a CSV file cannot be safely interpreted."""
