"""
Retry Handler with exponential backoff for AI Employee.

Provides decorators and utilities for resilient error recovery.
"""

import logging
import time
from functools import wraps

logger = logging.getLogger("RetryHandler")


class TransientError(Exception):
    """Error that may succeed on retry (network, rate limit, timeout)."""
    pass


class PermanentError(Exception):
    """Error that will NOT succeed on retry (auth, permission, bad data)."""
    pass


def with_retry(max_attempts: int = 3, base_delay: float = 1.0, max_delay: float = 60.0, retryable_exceptions: tuple = (TransientError, ConnectionError, TimeoutError)):
    """Decorator that retries a function with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"[{func.__name__}] All {max_attempts} attempts failed: {e}")
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    logger.warning(f"[{func.__name__}] Attempt {attempt + 1}/{max_attempts} failed: {e}. Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                except Exception as e:
                    logger.error(f"[{func.__name__}] Non-retryable error: {e}")
                    raise
        return wrapper
    return decorator


def classify_error(error: Exception) -> str:
    """Classify an error into a recovery category."""
    error_str = str(error).lower()

    # Transient errors
    if any(kw in error_str for kw in ["timeout", "rate limit", "429", "503", "502", "connection reset", "temporary"]):
        return "transient"

    # Authentication errors
    if any(kw in error_str for kw in ["401", "403", "unauthorized", "forbidden", "token expired", "invalid credentials"]):
        return "authentication"

    # Data errors
    if any(kw in error_str for kw in ["decode", "parse", "corrupt", "missing field", "invalid json", "malformed"]):
        return "data"

    # System errors
    if any(kw in error_str for kw in ["disk full", "no space", "memory", "permission denied", "file not found"]):
        return "system"

    return "unknown"
