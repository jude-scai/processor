"""
Processing Engine Exception Classes

Defines the exception hierarchy for processor execution phases:
- Pre-extraction phase exceptions
- Extraction phase exceptions
- Post-extraction phase exceptions
"""


class ProcessorException(Exception):
    """Base exception for all processor-related errors"""

    def __init__(self, message: str, processor_name: str | None = None):
        self.processor_name = processor_name
        super().__init__(message)


# Pre-extraction Phase Exceptions

class PrevalidationError(ProcessorException):
    """
    Raised during input pre-validation when prerequisite checks fail.

    Examples:
    - Required document doesn't exist
    - Document is not of correct stipulation type
    - Missing underwriting_id
    """
    pass


class InputValidationError(ProcessorException):
    """
    Raised when transformed input data fails validation.

    Examples:
    - Invalid input format
    - Missing required fields
    - Data type mismatches
    - Business rule violations in input
    """
    pass


class TransformationError(ProcessorException):
    """
    Raised when input data transformation fails.

    Examples:
    - Data conversion errors
    - Normalization failures
    - Document splicing errors
    - Chunking failures
    """
    pass


# Extraction Phase Exceptions

class FactorExtractionError(ProcessorException):
    """
    Raised when factor extraction from validated inputs fails.

    Examples:
    - Unable to parse document content
    - Missing expected data in inputs
    - Calculation errors
    - Data processing failures
    """
    pass


class DataTransformationError(ProcessorException):
    """
    Raised during extraction when data manipulation fails.

    Examples:
    - Data splicing errors during extraction
    - Chunking failures
    - Normalization errors
    """
    pass


class ApiError(ProcessorException):
    """
    Raised when external API calls fail.

    Examples:
    - Network timeouts
    - Authentication failures
    - Rate limiting exceeded
    - Invalid API responses
    - Service unavailability
    """

    def __init__(
        self,
        message: str,
        processor_name: str | None = None,
        api_name: str | None = None,
        status_code: int | None = None,
        is_retryable: bool = False
    ):
        self.api_name = api_name
        self.status_code = status_code
        self.is_retryable = is_retryable
        super().__init__(message, processor_name)


# Post-extraction Phase Exceptions

class ResultValidationError(ProcessorException):
    """
    Raised when extraction output validation fails.

    Examples:
    - Missing required output fields
    - Invalid output format
    - Output doesn't meet processor-specific requirements
    - Inconsistent or incomplete results
    """
    pass


# Database and Persistence Exceptions

class PersistenceError(ProcessorException):
    """
    Raised when saving execution results to database fails.

    Examples:
    - Database connection failures
    - Transaction rollback errors
    - Constraint violations
    """
    pass


# Configuration Exceptions

class ConfigurationError(ProcessorException):
    """
    Raised when processor configuration is invalid or missing.

    Examples:
    - Missing required configuration
    - Invalid configuration values
    - Configuration type mismatches
    """
    pass

