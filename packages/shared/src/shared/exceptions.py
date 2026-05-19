class OperatorAgentError(Exception):
    """Base exception for operator-agent."""


class DocumentParsingError(OperatorAgentError):
    """Raised when a document cannot be parsed."""


class SectionNotFoundError(OperatorAgentError):
    """Raised when an expected section is not found in a document."""


class ConstraintExtractionError(OperatorAgentError):
    """Raised when constraint extraction fails."""


class DatabaseError(OperatorAgentError):
    """Raised when a database operation fails."""
