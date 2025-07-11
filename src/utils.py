"""
Utility functions for the Kasa Collector application.
Includes retry decorators, device helpers, and Python 3.13 modern patterns.
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Optional, TypeVar, ParamSpec, Coroutine
from dns_cache import get_hostname_cached
from config import Config

# Modern Python 3.13 type hints
P = ParamSpec("P")
T = TypeVar("T")

logger = logging.getLogger(__name__)


def get_device_name(device) -> str:
    """
    Consolidated device name resolution function.
    Returns device alias or host as fallback, with proper error handling.
    """
    try:
        if hasattr(device, "alias") and device.alias:
            return device.alias
        elif hasattr(device, "host") and device.host:
            return device.host
        elif hasattr(device, "model") and device.model:
            return device.model
        else:
            return "Unknown Device"
    except Exception:
        return "Unknown Device"


def async_retry(
    max_retries: int = Config.KASA_COLLECTOR_FETCH_MAX_RETRIES,
    base_delay: float = Config.KASA_COLLECTOR_FETCH_RETRY_DELAY,
    exponential_backoff: bool = True,
    operation_name: str = "operation",
) -> Callable[
    [Callable[P, Coroutine[Any, Any, T]]], Callable[P, Coroutine[Any, Any, T]]
]:
    """
    Modern async retry decorator with exponential backoff and error handling.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        exponential_backoff: Whether to use exponential backoff
        operation_name: Name of the operation for logging

    Returns:
        Decorated async function with retry logic
    """

    def decorator(
        func: Callable[P, Coroutine[Any, Any, T]],
    ) -> Callable[P, Coroutine[Any, Any, T]]:
        @wraps(func)
        async def wrapper(  # type: ignore[misc,return]
            *args: P.args, **kwargs: P.kwargs
        ) -> T:
            retries = 0

            # Extract device info for better logging if available
            device_info = ""
            if len(args) >= 3:  # Assuming (self, ip, device) pattern
                try:
                    ip = str(args[1])
                    device = args[2]
                    device_name = get_device_name(device)
                    hostname = await get_hostname_cached(ip)
                    device_info = f" for {device_name} (IP: {ip}, Hostname: {hostname})"
                except Exception:
                    device_info = (
                        f" for device at {args[1] if len(args) > 1 else 'unknown'}"
                    )

            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)

                except (ConnectionError, TimeoutError, OSError) as e:
                    logger.error(
                        f"Network error during {operation_name}{device_info}: {e}"
                    )

                except (AttributeError, KeyError, ValueError) as e:
                    logger.error(
                        f"Data error during {operation_name}{device_info}: {e}"
                    )

                except Exception as e:
                    logger.error(
                        f"Unexpected error during {operation_name}{device_info}: {e}"
                    )

                retries += 1
                if retries < max_retries:
                    delay = base_delay * (2**retries if exponential_backoff else 1)
                    # Cap delay at maximum configured value to prevent excessive waits
                    delay = min(delay, Config.KASA_COLLECTOR_MAX_RETRY_DELAY)
                    logger.debug(
                        f"Retrying {operation_name}{device_info} in {delay:.2f}s "
                        f"(attempt {retries}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.warning(
                        f"Max retries ({max_retries}) reached for "
                        f"{operation_name}{device_info}"
                    )
                    raise

            # This should never be reached, but satisfies type checkers
            raise RuntimeError(
                f"Unexpected end of retry loop in {operation_name}{device_info}"
            )

        return wrapper

    return decorator


class DeviceContext:
    """
    Context manager for device operations using Python 3.13 features.
    Provides structured error handling and resource management.
    """

    def __init__(self, device, ip: str, operation: str):
        self.device = device
        self.ip = ip
        self.operation = operation
        self.device_name = get_device_name(device)
        self.hostname = None

    async def __aenter__(self):
        """Async context manager entry with device preparation."""
        self.hostname = await get_hostname_cached(self.ip)
        logger.debug(
            f"Starting {self.operation} for {self.device_name} (IP: {self.ip})"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with error logging."""
        if exc_type is not None:
            logger.error(
                f"Error during {self.operation} for {self.device_name} "
                f"(IP: {self.ip}): {exc_val}"
            )
        else:
            logger.debug(
                f"Successfully completed {self.operation} for "
                f"{self.device_name} (IP: {self.ip})"
            )
        return False  # Don't suppress exceptions


def format_duration(seconds: float) -> str:
    """
    Format a duration given in seconds into a human-readable string.
    Uses modern string formatting and better readability.
    """
    if seconds < 60:
        return f"{seconds:.2f} seconds"

    minutes, secs = divmod(seconds, 60)
    if minutes < 60:
        return f"{int(minutes)} minutes, {secs:.1f} seconds"

    hours, mins = divmod(minutes, 60)
    return f"{int(hours)} hours, {int(mins)} minutes, {secs:.1f} seconds"


# Python 3.13 feature: Enhanced error handling with exception groups
# Import ExceptionGroup from Python 3.11+
try:
    from builtins import ExceptionGroup
except ImportError:
    # Fallback for older Python versions
    ExceptionGroup = Exception  # type: ignore[misc,assignment]


class DeviceOperationError(ExceptionGroup):  # type: ignore[misc]
    """
    Custom exception group for device operations.
    Leverages Python 3.13's enhanced exception handling.
    """

    def __init__(self, message: str, exceptions: list[Exception]):
        super().__init__(message, exceptions)

    @classmethod
    def from_task_failures(
        cls, operation: str, exceptions: list[Exception]
    ) -> "DeviceOperationError":
        """Create a DeviceOperationError from failed tasks."""
        return cls(f"Multiple failures during {operation}", exceptions)


# Python 3.13 feature: Improved performance with better string formatting
def format_device_info(device, ip: str, hostname: Optional[str] = None) -> str:
    """
    Format device information using Python 3.13's improved f-string performance.
    """
    device_name = get_device_name(device)
    if hostname:
        return f"{device_name} (IP: {ip}, Hostname: {hostname})"
    return f"{device_name} (IP: {ip})"


# Python 3.13 feature: Enhanced type annotations with generic type aliases
type DeviceMap = dict[str, Any]  # Modern type alias syntax
type IPAddress = str
type DeviceName = str
