"""
API middleware for error handling and request/response processing.
"""
import json
import logging
import time
import traceback
import uuid
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from core.utils.error_handling import APIException, APIErrorResponse, ErrorType

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for consistent error handling across all API endpoints.
    
    - Catches unhandled exceptions and converts them to standard API errors
    - Adds request ID tracking for debugging
    - Logs all errors with context
    - Returns consistent error format
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Add request ID to headers
        start_time = time.time()
        
        try:
            # Process request
            response = await call_next(request)
            
            # Add request ID to successful responses
            response.headers["X-Request-ID"] = request_id
            
            # Log successful requests
            duration = time.time() - start_time
            logger.info(
                f"Request completed successfully",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "status_code": response.status_code,
                    "duration": f"{duration:.3f}s"
                }
            )
            
            return response
            
        except APIException as e:
            # Handle our custom API exceptions
            duration = time.time() - start_time
            
            error_response = e.to_response()
            error_response.request_id = request_id
            
            logger.error(
                f"API error: {e.message}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "error_type": e.error_type.value,
                    "status_code": e.status_code,
                    "duration": f"{duration:.3f}s",
                    "error_details": e.details.model_dump() if e.details else None
                },
                exc_info=e.original_error if e.original_error else None
            )
            
            return JSONResponse(
                status_code=e.status_code,
                content={"error": error_response.model_dump()}
            )
            
        except Exception as e:
            # Handle unexpected exceptions
            duration = time.time() - start_time
            
            # Create generic error response
            error_response = APIErrorResponse(
                type=ErrorType.PROCESSING,
                message="An unexpected error occurred",
                request_id=request_id,
                status_code=500
            )
            
            logger.error(
                f"Unhandled exception: {str(e)}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "url": str(request.url),
                    "duration": f"{duration:.3f}s",
                    "traceback": traceback.format_exc()
                },
                exc_info=True
            )
            
            return JSONResponse(
                status_code=500,
                content={"error": error_response.model_dump()}
            )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for logging all incoming requests.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Log incoming request
        logger.info(
            f"Incoming request: {request.method} {request.url}",
            extra={
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers),
                "client": request.client.host if request.client else None
            }
        )
        
        response = await call_next(request)
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Basic rate limiting middleware (can be enhanced with Redis for distributed systems).
    """
    
    def __init__(self, app, calls_per_minute: int = 100):
        super().__init__(app)
        self.calls_per_minute = calls_per_minute
        self.requests = {}  # In-memory storage (use Redis in production)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Clean old entries
        cutoff_time = current_time - 60  # 1 minute ago
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if req_time > cutoff_time
            ]
        
        # Check rate limit
        if client_ip in self.requests:
            if len(self.requests[client_ip]) >= self.calls_per_minute:
                logger.warning(f"Rate limit exceeded for {client_ip}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": {
                            "type": "rate_limit_error",
                            "message": f"Rate limit exceeded. Maximum {self.calls_per_minute} requests per minute.",
                            "request_id": str(uuid.uuid4()),
                            "timestamp": time.time()
                        }
                    }
                )
        
        # Record request
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)
        
        response = await call_next(request)
        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware for handling cross-origin requests.
    """
    
    def __init__(self, app, allow_origins: list = None, allow_credentials: bool = True):
        super().__init__(app)
        self.allow_origins = allow_origins or ["*"]
        self.allow_credentials = allow_credentials
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
        else:
            response = await call_next(request)
        
        # Add CORS headers
        origin = request.headers.get("origin")
        if origin and (self.allow_origins == ["*"] or origin in self.allow_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
        elif self.allow_origins == ["*"]:
            response.headers["Access-Control-Allow-Origin"] = "*"
        
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-ID"
        
        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response


def get_request_id(request: Request) -> str:
    """Get request ID from request state."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def create_error_response(
    error_type: ErrorType,
    message: str,
    status_code: int = 500,
    details: Optional[dict] = None,
    request_id: Optional[str] = None
) -> JSONResponse:
    """
    Create a standardized error response.
    
    Args:
        error_type: Type of error
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        request_id: Request ID for tracking
        
    Returns:
        JSONResponse with error details
    """
    error_response = APIErrorResponse(
        type=error_type,
        message=message,
        status_code=status_code,
        request_id=request_id or str(uuid.uuid4())
    )
    
    if details:
        from core.utils.error_handling import ErrorDetail
        error_response.details = ErrorDetail(**details)
    
    return JSONResponse(
        status_code=status_code,
        content={"error": error_response.model_dump()}
    )