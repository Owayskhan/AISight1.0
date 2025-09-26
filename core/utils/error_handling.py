"""
Centralized error handling utilities for robust API error management.
"""
import asyncio
import functools
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Type, Union
from enum import Enum
import traceback
import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Standardized error types for consistent error handling."""
    RATE_LIMIT = "rate_limit_error"
    QUOTA_EXCEEDED = "quota_exceeded_error"
    AUTHENTICATION = "authentication_error"
    VALIDATION = "validation_error"
    EXTERNAL_SERVICE = "external_service_error"
    TIMEOUT = "timeout_error"
    CONNECTION = "connection_error"
    PROCESSING = "processing_error"
    NOT_FOUND = "not_found_error"
    PERMISSION_DENIED = "permission_denied_error"


class ErrorDetail(BaseModel):
    """Structured error details for API responses."""
    service: Optional[str] = Field(None, description="Service that caused the error")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")
    limit_type: Optional[str] = Field(None, description="Type of limit exceeded")
    remaining_quota: Optional[int] = Field(None, description="Remaining API quota if applicable")
    suggestion: Optional[str] = Field(None, description="Suggestion for resolving the error")
    original_error: Optional[str] = Field(None, description="Original error message from service")


class APIErrorResponse(BaseModel):
    """Standardized API error response format."""
    type: ErrorType
    message: str
    details: Optional[ErrorDetail] = None
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    status_code: int = 500


class APIException(Exception):
    """Base exception for all API errors."""
    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.error_type = error_type
        self.status_code = status_code
        self.details = ErrorDetail(**details) if details else None
        self.original_error = original_error
        super().__init__(message)
    
    def to_response(self) -> APIErrorResponse:
        """Convert exception to API error response."""
        return APIErrorResponse(
            type=self.error_type,
            message=self.message,
            details=self.details,
            status_code=self.status_code
        )


class APIRateLimitError(APIException):
    """Raised when API rate limit is exceeded."""
    def __init__(self, message: str, service: str, retry_after: Optional[int] = None, **kwargs):
        details = {
            "service": service,
            "retry_after": retry_after,
            "limit_type": kwargs.get("limit_type", "requests_per_minute"),
            "suggestion": f"Please wait {retry_after} seconds before retrying" if retry_after else "Please reduce request frequency"
        }
        super().__init__(message, ErrorType.RATE_LIMIT, status_code=429, details=details)


class APIQuotaExceededError(APIException):
    """Raised when API quota/credits are exhausted."""
    def __init__(self, message: str, service: str, remaining_quota: Optional[int] = None, **kwargs):
        details = {
            "service": service,
            "remaining_quota": remaining_quota,
            "suggestion": "Please check your API plan or add more credits"
        }
        super().__init__(message, ErrorType.QUOTA_EXCEEDED, status_code=402, details=details)


class ExternalServiceError(APIException):
    """Raised when external service fails."""
    def __init__(self, message: str, service: str, original_error: Optional[str] = None, **kwargs):
        details = {
            "service": service,
            "original_error": original_error,
            "suggestion": "The external service is experiencing issues. Please try again later."
        }
        super().__init__(message, ErrorType.EXTERNAL_SERVICE, status_code=503, details=details)


class ValidationError(APIException):
    """Raised when input validation fails."""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = {
            "field": field,
            "suggestion": "Please check your input and try again"
        }
        super().__init__(message, ErrorType.VALIDATION, status_code=400, details=details)


class ProcessingError(APIException):
    """Raised when internal processing fails."""
    def __init__(self, message: str, operation: Optional[str] = None, **kwargs):
        details = {
            "operation": operation,
            "suggestion": "An internal error occurred. Please try again or contact support if the issue persists."
        }
        super().__init__(message, ErrorType.PROCESSING, status_code=500, details=details)


class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True


def parse_openai_error(error: Exception) -> APIException:
    """Parse OpenAI specific errors into standardized exceptions."""
    error_message = str(error)
    
    if "rate limit" in error_message.lower():
        retry_after = None
        # Try to extract retry-after from error message
        import re
        match = re.search(r'try again in (\d+)s', error_message)
        if match:
            retry_after = int(match.group(1))
        return APIRateLimitError(
            "OpenAI API rate limit exceeded",
            service="openai",
            retry_after=retry_after,
            original_error=error
        )
    elif "insufficient_quota" in error_message.lower() or "exceeded your current quota" in error_message.lower():
        return APIQuotaExceededError(
            "OpenAI API quota exceeded",
            service="openai",
            original_error=error
        )
    elif "authentication" in error_message.lower() or "api key" in error_message.lower():
        return APIException(
            "OpenAI authentication failed",
            ErrorType.AUTHENTICATION,
            status_code=401,
            details={"service": "openai", "suggestion": "Please check your API key"}
        )
    else:
        return ExternalServiceError(
            "OpenAI API error",
            service="openai",
            original_error=error_message
        )


def parse_gemini_error(error: Exception) -> APIException:
    """Parse Google Gemini specific errors into standardized exceptions."""
    error_message = str(error)
    
    if "resource exhausted" in error_message.lower() or "quota" in error_message.lower():
        return APIQuotaExceededError(
            "Google Gemini API quota exceeded",
            service="gemini",
            original_error=error
        )
    elif "rate limit" in error_message.lower():
        return APIRateLimitError(
            "Google Gemini API rate limit exceeded",
            service="gemini",
            limit_type="requests_per_minute",
            original_error=error
        )
    elif "api key" in error_message.lower() or "authentication" in error_message.lower():
        return APIException(
            "Google Gemini authentication failed",
            ErrorType.AUTHENTICATION,
            status_code=401,
            details={"service": "gemini", "suggestion": "Please check your API key"}
        )
    else:
        return ExternalServiceError(
            "Google Gemini API error",
            service="gemini",
            original_error=error_message
        )


def parse_perplexity_error(error: Exception) -> APIException:
    """Parse Perplexity specific errors into standardized exceptions."""
    error_message = str(error)
    
    if "rate limit" in error_message.lower():
        return APIRateLimitError(
            "Perplexity API rate limit exceeded",
            service="perplexity",
            original_error=error
        )
    elif "unauthorized" in error_message.lower() or "api key" in error_message.lower():
        return APIException(
            "Perplexity authentication failed",
            ErrorType.AUTHENTICATION,
            status_code=401,
            details={"service": "perplexity", "suggestion": "Please check your API key"}
        )
    else:
        return ExternalServiceError(
            "Perplexity API error",
            service="perplexity",
            original_error=error_message
        )


def parse_http_error(error: httpx.HTTPError) -> APIException:
    """Parse HTTP errors into standardized exceptions."""
    if isinstance(error, httpx.TimeoutException):
        return APIException(
            "Request timed out",
            ErrorType.TIMEOUT,
            status_code=408,
            details={"suggestion": "The request took too long. Please try again."}
        )
    elif isinstance(error, httpx.ConnectError):
        return APIException(
            "Connection failed",
            ErrorType.CONNECTION,
            status_code=503,
            details={"suggestion": "Could not connect to the service. Please check your network connection."}
        )
    else:
        return ExternalServiceError(
            "HTTP request failed",
            service="http",
            original_error=str(error)
        )


def async_retry(
    retries: int = 3,
    delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Async retry decorator with exponential backoff.
    
    Args:
        retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == retries:
                        logger.error(f"Failed after {retries + 1} attempts: {str(e)}")
                        raise
                    
                    # Calculate next delay with exponential backoff
                    current_delay = min(current_delay * exponential_base, max_delay)
                    
                    # Add jitter to prevent thundering herd
                    import random
                    jittered_delay = current_delay * (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{retries + 1} failed: {str(e)}. "
                        f"Retrying in {jittered_delay:.2f}s..."
                    )
                    
                    if on_retry:
                        await on_retry(attempt, e, jittered_delay)
                    
                    await asyncio.sleep(jittered_delay)
            
            raise last_exception
        return wrapper
    return decorator


def sync_retry(
    retries: int = 3,
    delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None
):
    """
    Synchronous retry decorator with exponential backoff.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == retries:
                        logger.error(f"Failed after {retries + 1} attempts: {str(e)}")
                        raise
                    
                    # Calculate next delay with exponential backoff
                    current_delay = min(current_delay * exponential_base, max_delay)
                    
                    # Add jitter to prevent thundering herd
                    import random
                    jittered_delay = current_delay * (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{retries + 1} failed: {str(e)}. "
                        f"Retrying in {jittered_delay:.2f}s..."
                    )
                    
                    if on_retry:
                        on_retry(attempt, e, jittered_delay)
                    
                    time.sleep(jittered_delay)
            
            raise last_exception
        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external services.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Failures exceeded threshold, requests fail immediately
    - HALF_OPEN: Testing if service recovered, limited requests allowed
    """
    
    class State(Enum):
        CLOSED = "closed"
        OPEN = "open"
        HALF_OPEN = "half_open"
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_requests: int = 3
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_requests = half_open_requests
        
        self.state = self.State.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_count = 0
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not await self._can_proceed():
                raise ExternalServiceError(
                    "Service temporarily unavailable (circuit breaker open)",
                    service=func.__name__
                )
            
            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not self._can_proceed_sync():
                raise ExternalServiceError(
                    "Service temporarily unavailable (circuit breaker open)",
                    service=func.__name__
                )
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    async def _can_proceed(self) -> bool:
        """Check if request can proceed (async version)."""
        return self._can_proceed_sync()
    
    def _can_proceed_sync(self) -> bool:
        """Check if request can proceed (sync version)."""
        if self.state == self.State.CLOSED:
            return True
        
        if self.state == self.State.OPEN:
            # Check if recovery timeout has passed
            if (time.time() - self.last_failure_time) > self.recovery_timeout:
                logger.info(f"Circuit breaker entering HALF_OPEN state")
                self.state = self.State.HALF_OPEN
                self.half_open_count = 0
                return True
            return False
        
        if self.state == self.State.HALF_OPEN:
            # Allow limited requests in half-open state
            if self.half_open_count < self.half_open_requests:
                self.half_open_count += 1
                return True
            return False
    
    def _on_success(self):
        """Handle successful request."""
        if self.state == self.State.HALF_OPEN:
            logger.info(f"Circuit breaker recovered, entering CLOSED state")
            self.state = self.State.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
    
    def _on_failure(self):
        """Handle failed request."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            logger.warning(f"Circuit breaker threshold exceeded, entering OPEN state")
            self.state = self.State.OPEN


def handle_api_error(error: Exception, service: Optional[str] = None) -> APIException:
    """
    Convert any exception to a standardized APIException.
    
    Args:
        error: The original exception
        service: Optional service name for context
        
    Returns:
        Standardized APIException
    """
    # If it's already an APIException, return it
    if isinstance(error, APIException):
        return error
    
    # Try to parse known service errors
    error_str = str(error).lower()
    
    if service == "openai" or "openai" in error_str:
        return parse_openai_error(error)
    elif service == "gemini" or "gemini" in error_str or "google" in error_str:
        return parse_gemini_error(error)
    elif service == "perplexity" or "perplexity" in error_str:
        return parse_perplexity_error(error)
    elif isinstance(error, httpx.HTTPError):
        return parse_http_error(error)
    else:
        # Generic error handling
        return ProcessingError(
            f"An unexpected error occurred: {str(error)}",
            operation=service
        )