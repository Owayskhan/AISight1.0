"""
Rate limiting utilities for managing API request rates and preventing quota exhaustion.
"""
import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Callable
from enum import Enum
import logging
import functools

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_minute: int = 60
    requests_per_hour: Optional[int] = None
    requests_per_day: Optional[int] = None
    burst_size: Optional[int] = None  # For token bucket
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET


class TokenBucket:
    """
    Token bucket implementation for rate limiting.
    Allows burst traffic while maintaining average rate.
    """
    
    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens added per second
            capacity: Maximum bucket capacity (burst size)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens from the bucket. Blocks until tokens are available.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            Time waited in seconds
        """
        async with self._lock:
            wait_time = self._acquire_sync(tokens)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            return wait_time
    
    def _acquire_sync(self, tokens: int = 1) -> float:
        """Synchronous version of acquire."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return 0
        
        # Calculate wait time
        deficit = tokens - self.tokens
        wait_time = deficit / self.rate
        
        # Reserve the tokens for future
        self.tokens = 0
        self.last_update = now + wait_time
        
        return wait_time
    
    def try_acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens without blocking."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class SlidingWindowCounter:
    """
    Sliding window counter for rate limiting.
    Provides accurate rate limiting over time windows.
    """
    
    def __init__(self, window_size: int, max_requests: int):
        """
        Args:
            window_size: Window size in seconds
            max_requests: Maximum requests allowed in the window
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = deque()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> float:
        """
        Try to make a request. Blocks if rate limit exceeded.
        
        Returns:
            Time waited in seconds
        """
        async with self._lock:
            wait_time = self._acquire_sync()
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                # Retry after waiting
                return await self.acquire()
            return 0
    
    def _acquire_sync(self) -> float:
        """Synchronous version of acquire."""
        now = time.time()
        
        # Remove old requests outside the window
        cutoff = now - self.window_size
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        # Check if we can make a request
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return 0
        
        # Calculate wait time until the oldest request expires
        oldest_request = self.requests[0]
        wait_time = oldest_request + self.window_size - now
        return max(0, wait_time)
    
    def try_acquire(self) -> bool:
        """Try to make a request without blocking."""
        now = time.time()
        
        # Remove old requests
        cutoff = now - self.window_size
        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()
        
        # Check if we can make a request
        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True
        return False


class APIRateLimiter:
    """
    Comprehensive rate limiter for multiple APIs with different limits.
    """
    
    def __init__(self):
        self.limiters: Dict[str, Dict[str, Any]] = {}
        self.stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
    def configure_api(self, api_name: str, config: RateLimitConfig):
        """Configure rate limits for an API."""
        limiters = {}
        
        # Create appropriate rate limiter based on strategy
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            # Requests per minute limiter
            if config.requests_per_minute:
                rate = config.requests_per_minute / 60.0  # tokens per second
                capacity = config.burst_size or config.requests_per_minute
                limiters['minute'] = TokenBucket(rate, capacity)
            
            # Requests per hour limiter
            if config.requests_per_hour:
                rate = config.requests_per_hour / 3600.0
                capacity = config.burst_size or min(config.requests_per_hour // 10, 100)
                limiters['hour'] = TokenBucket(rate, capacity)
            
            # Requests per day limiter
            if config.requests_per_day:
                rate = config.requests_per_day / 86400.0
                capacity = config.burst_size or min(config.requests_per_day // 100, 100)
                limiters['day'] = TokenBucket(rate, capacity)
                
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            if config.requests_per_minute:
                limiters['minute'] = SlidingWindowCounter(60, config.requests_per_minute)
            if config.requests_per_hour:
                limiters['hour'] = SlidingWindowCounter(3600, config.requests_per_hour)
            if config.requests_per_day:
                limiters['day'] = SlidingWindowCounter(86400, config.requests_per_day)
        
        self.limiters[api_name] = {
            'limiters': limiters,
            'config': config
        }
        
        logger.info(f"Configured rate limits for {api_name}: {config}")
    
    async def acquire(self, api_name: str, tokens: int = 1) -> float:
        """
        Acquire permission to make API request(s).
        Blocks until rate limit allows.
        
        Args:
            api_name: Name of the API
            tokens: Number of requests/tokens to acquire
            
        Returns:
            Total time waited in seconds
        """
        if api_name not in self.limiters:
            logger.warning(f"No rate limits configured for {api_name}")
            return 0
        
        total_wait = 0
        limiters = self.limiters[api_name]['limiters']
        
        # Check all rate limiters (minute, hour, day)
        for period, limiter in limiters.items():
            if isinstance(limiter, TokenBucket):
                wait_time = await limiter.acquire(tokens)
            else:  # SlidingWindowCounter
                wait_time = 0
                for _ in range(tokens):
                    wait_time += await limiter.acquire()
            
            total_wait = max(total_wait, wait_time)
            
            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached for {api_name} ({period}). "
                    f"Waited {wait_time:.2f}s"
                )
        
        # Update statistics
        self.stats[api_name]['requests'] += tokens
        self.stats[api_name]['total_wait_time'] += total_wait
        
        return total_wait
    
    def try_acquire(self, api_name: str, tokens: int = 1) -> bool:
        """
        Try to acquire permission without blocking.
        
        Returns:
            True if acquired, False if would block
        """
        if api_name not in self.limiters:
            return True
        
        limiters = self.limiters[api_name]['limiters']
        
        # Check all limiters - all must allow
        for limiter in limiters.values():
            if isinstance(limiter, TokenBucket):
                if not limiter.try_acquire(tokens):
                    return False
            else:  # SlidingWindowCounter
                # For sliding window, we need to check each token
                for _ in range(tokens):
                    if not limiter.try_acquire():
                        return False
        
        self.stats[api_name]['requests'] += tokens
        return True
    
    def get_wait_time(self, api_name: str, tokens: int = 1) -> float:
        """
        Get estimated wait time without acquiring.
        
        Returns:
            Estimated wait time in seconds
        """
        if api_name not in self.limiters:
            return 0
        
        max_wait = 0
        limiters = self.limiters[api_name]['limiters']
        
        for limiter in limiters.values():
            if isinstance(limiter, TokenBucket):
                # Estimate based on current tokens
                if limiter.tokens < tokens:
                    deficit = tokens - limiter.tokens
                    wait = deficit / limiter.rate
                    max_wait = max(max_wait, wait)
            else:  # SlidingWindowCounter
                wait = limiter._acquire_sync()
                max_wait = max(max_wait, wait)
        
        return max_wait
    
    def get_stats(self, api_name: Optional[str] = None) -> Dict[str, Any]:
        """Get rate limiting statistics."""
        if api_name:
            return dict(self.stats.get(api_name, {}))
        return {api: dict(stats) for api, stats in self.stats.items()}


# Global rate limiter instance
_global_rate_limiter = APIRateLimiter()


def configure_rate_limits():
    """Configure rate limits for all APIs."""
    # OpenAI rate limits (GPT-4 tier)
    _global_rate_limiter.configure_api('openai', RateLimitConfig(
        requests_per_minute=500,
        requests_per_day=10000,
        burst_size=100,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    ))
    
    # Google Gemini rate limits
    _global_rate_limiter.configure_api('gemini', RateLimitConfig(
        requests_per_minute=60,
        requests_per_day=1500,
        burst_size=20,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    ))
    
    # Perplexity rate limits (tier-specific, configurable via env)
    import os
    from core.config import BatchConfig
    perplexity_rpm = int(os.getenv('PERPLEXITY_RPM', BatchConfig.PERPLEXITY_RPM))

    _global_rate_limiter.configure_api('perplexity', RateLimitConfig(
        requests_per_minute=perplexity_rpm,  # Tier-specific (default: 50 for tier 0)
        requests_per_hour=None,  # No hourly limit (only minute limit matters)
        burst_size=min(perplexity_rpm // 5, 10),  # Conservative burst: 20% of RPM, max 10
        strategy=RateLimitStrategy.TOKEN_BUCKET
    ))
    
    # Web scraping rate limits (reasonable for sitemap discovery and content loading)
    _global_rate_limiter.configure_api('web_scraping', RateLimitConfig(
        requests_per_minute=100,  # Increased for faster sitemap discovery
        burst_size=15,  # Allow burst for checking multiple sitemap paths
        strategy=RateLimitStrategy.TOKEN_BUCKET
    ))
    
    # Pinecone rate limits
    _global_rate_limiter.configure_api('pinecone', RateLimitConfig(
        requests_per_minute=100,
        burst_size=50,
        strategy=RateLimitStrategy.TOKEN_BUCKET
    ))


def rate_limit(api_name: str, tokens: int = 1):
    """
    Decorator for rate limiting async functions.
    
    Args:
        api_name: Name of the API to rate limit
        tokens: Number of tokens/requests this operation consumes
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Wait for rate limit
            wait_time = await _global_rate_limiter.acquire(api_name, tokens)
            
            if wait_time > 0:
                logger.debug(f"Rate limited {func.__name__} for {wait_time:.2f}s")
            
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # On error, potentially adjust rate limits
                logger.error(f"Error in rate-limited function {func.__name__}: {e}")
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, try non-blocking acquire
            if not _global_rate_limiter.try_acquire(api_name, tokens):
                wait_time = _global_rate_limiter.get_wait_time(api_name, tokens)
                raise RateLimitError(
                    f"Rate limit exceeded for {api_name}. Try again in {wait_time:.1f}s",
                    wait_time=wait_time
                )
            
            return func(*args, **kwargs)
        
        # Return appropriate wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


class RateLimitError(Exception):
    """Raised when rate limit is exceeded."""
    def __init__(self, message: str, wait_time: float = 0):
        self.message = message
        self.wait_time = wait_time
        super().__init__(message)


class AdaptiveRateLimiter:
    """
    Adaptive rate limiter that adjusts based on API responses.
    Monitors response headers and errors to dynamically adjust limits.
    """
    
    def __init__(self, api_name: str, initial_config: RateLimitConfig):
        self.api_name = api_name
        self.base_config = initial_config
        self.current_multiplier = 1.0
        self.error_count = 0
        self.success_count = 0
        self.last_adjustment = time.time()
        self.adjustment_interval = 300  # 5 minutes
        
        # Apply initial config
        self._apply_config()
    
    def _apply_config(self):
        """Apply current configuration with multiplier."""
        adjusted_config = RateLimitConfig(
            requests_per_minute=int(self.base_config.requests_per_minute * self.current_multiplier),
            requests_per_hour=int(self.base_config.requests_per_hour * self.current_multiplier) if self.base_config.requests_per_hour else None,
            requests_per_day=int(self.base_config.requests_per_day * self.current_multiplier) if self.base_config.requests_per_day else None,
            burst_size=self.base_config.burst_size,
            strategy=self.base_config.strategy
        )
        _global_rate_limiter.configure_api(self.api_name, adjusted_config)
    
    def on_response(self, headers: Dict[str, str], status_code: int):
        """
        Process API response to adjust rate limits.
        
        Args:
            headers: Response headers
            status_code: HTTP status code
        """
        # Check for rate limit headers
        remaining = headers.get('x-ratelimit-remaining') or headers.get('x-rate-limit-remaining')
        reset_time = headers.get('x-ratelimit-reset') or headers.get('x-rate-limit-reset')
        retry_after = headers.get('retry-after')
        
        if status_code == 429:  # Rate limited
            self.error_count += 1
            
            # Reduce rate by 20%
            self.current_multiplier = max(0.1, self.current_multiplier * 0.8)
            self._apply_config()
            
            logger.warning(
                f"Rate limit hit for {self.api_name}. "
                f"Reducing rate to {self.current_multiplier * 100:.0f}%"
            )
            
            # If we have retry-after, wait that long
            if retry_after:
                wait_time = int(retry_after) if retry_after.isdigit() else 60
                time.sleep(wait_time)
                
        elif status_code < 400:  # Success
            self.success_count += 1
            
            # Consider increasing rate after sustained success
            if self.success_count > 100 and self.error_count == 0:
                now = time.time()
                if now - self.last_adjustment > self.adjustment_interval:
                    self.current_multiplier = min(1.0, self.current_multiplier * 1.1)
                    self._apply_config()
                    self.last_adjustment = now
                    self.success_count = 0
                    logger.info(
                        f"Increasing rate for {self.api_name} to "
                        f"{self.current_multiplier * 100:.0f}%"
                    )
        
        # Check remaining quota
        if remaining is not None:
            remaining_count = int(remaining)
            if remaining_count < 10:
                logger.warning(
                    f"Low rate limit remaining for {self.api_name}: {remaining_count}"
                )


# Initialize rate limits on module import
configure_rate_limits()


# Convenience functions
async def wait_for_rate_limit(api_name: str, tokens: int = 1) -> float:
    """Wait for rate limit and return wait time."""
    return await _global_rate_limiter.acquire(api_name, tokens)


def check_rate_limit(api_name: str, tokens: int = 1) -> bool:
    """Check if request would be rate limited."""
    return _global_rate_limiter.try_acquire(api_name, tokens)


def get_rate_limit_stats(api_name: Optional[str] = None) -> Dict[str, Any]:
    """Get rate limiting statistics."""
    return _global_rate_limiter.get_stats(api_name)


def get_rate_limit_manager() -> 'APIRateLimiter':
    """Get the global rate limit manager instance."""
    return _global_rate_limiter