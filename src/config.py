import os
import sys
from typing import Optional

type ConfigValue = int | str | bool
type ConfigDict = dict[str, ConfigValue]

# Valid log levels for validation
VALID_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


def _get_bool_config(env_var: str, default: bool = False) -> bool:
    """
    Safely get boolean configuration from environment variable.
    Accepts: true/false, yes/no, 1/0, on/off (case insensitive)
    """
    value = os.getenv(env_var, str(default)).lower()
    return value in {"true", "yes", "1", "on"}


def _get_int_config(env_var: str, default: int, min_value: Optional[int] = None) -> int:
    """
    Safely get integer configuration from environment variable with validation.
    """
    value = os.getenv(env_var, str(default))
    try:
        result = int(value)
        if min_value is not None and result < min_value:
            print(f"ERROR: {env_var} value {result} is below minimum {min_value}")
            sys.exit(1)
        return result
    except ValueError:
        print(f"ERROR: Invalid integer value '{value}' for {env_var}")
        sys.exit(1)


def _get_log_level(env_var: str, default: str = "INFO") -> str:
    """
    Safely get log level from environment variable with validation.
    """
    value = os.getenv(env_var, default).upper()
    if value not in VALID_LOG_LEVELS:
        print(f"ERROR: Invalid log level '{value}' for {env_var}. ")
        print(f"Valid levels: {', '.join(sorted(VALID_LOG_LEVELS))}")
        sys.exit(1)
    return value


class Config:
    """Configuration settings for Kasa Collector loaded from environment variables."""

    # File output settings
    KASA_COLLECTOR_WRITE_TO_FILE = _get_bool_config(
        "KASA_COLLECTOR_WRITE_TO_FILE", default=False
    )

    # Directory where output files will be saved. Default is "output".
    KASA_COLLECTOR_OUTPUT_DIR = os.getenv("KASA_COLLECTOR_OUTPUT_DIR", "output")

    # Retry and timeout settings
    KASA_COLLECTOR_FETCH_MAX_RETRIES = _get_int_config(
        "KASA_COLLECTOR_FETCH_MAX_RETRIES", default=5, min_value=1
    )

    KASA_COLLECTOR_FETCH_RETRY_DELAY = _get_int_config(
        "KASA_COLLECTOR_FETCH_RETRY_DELAY", default=1, min_value=1
    )

    # Discovery settings
    KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL = _get_int_config(
        "KASA_COLLECTOR_DEVICE_DISCOVERY_INTERVAL", default=300, min_value=1
    )

    KASA_COLLECTOR_DISCOVERY_TIMEOUT = _get_int_config(
        "KASA_COLLECTOR_DISCOVERY_TIMEOUT", default=5, min_value=1
    )

    KASA_COLLECTOR_DISCOVERY_PACKETS = _get_int_config(
        "KASA_COLLECTOR_DISCOVERY_PACKETS", default=3, min_value=1
    )

    # Data collection intervals
    KASA_COLLECTOR_DATA_FETCH_INTERVAL = _get_int_config(
        "KASA_COLLECTOR_DATA_FETCH_INTERVAL", default=15, min_value=1
    )

    KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL = _get_int_config(
        "KASA_COLLECTOR_SYSINFO_FETCH_INTERVAL", default=60, min_value=1
    )

    # Device management
    KASA_COLLECTOR_KEEP_MISSING_DEVICES = _get_bool_config(
        "KASA_COLLECTOR_KEEP_MISSING_DEVICES", default=True
    )

    # URL for the InfluxDB instance.
    KASA_COLLECTOR_INFLUXDB_URL = os.getenv("KASA_COLLECTOR_INFLUXDB_URL")

    # Token for authenticating with InfluxDB.
    KASA_COLLECTOR_INFLUXDB_TOKEN = os.getenv("KASA_COLLECTOR_INFLUXDB_TOKEN")

    # Organization name for InfluxDB.
    KASA_COLLECTOR_INFLUXDB_ORG = os.getenv("KASA_COLLECTOR_INFLUXDB_ORG")

    # Bucket name for storing data in InfluxDB.
    KASA_COLLECTOR_INFLUXDB_BUCKET = os.getenv("KASA_COLLECTOR_INFLUXDB_BUCKET")

    # InfluxDB write options
    KASA_COLLECTOR_INFLUXDB_BATCH_SIZE = _get_int_config(
        "KASA_COLLECTOR_INFLUXDB_BATCH_SIZE", default=1, min_value=1
    )

    KASA_COLLECTOR_INFLUXDB_FLUSH_INTERVAL = _get_int_config(
        "KASA_COLLECTOR_INFLUXDB_FLUSH_INTERVAL", default=10, min_value=1
    )

    # Logging configuration
    KASA_COLLECTOR_LOG_LEVEL_KASA_API = _get_log_level(
        "KASA_COLLECTOR_LOG_LEVEL_KASA_API", default="INFO"
    )

    KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE = _get_log_level(
        "KASA_COLLECTOR_LOG_LEVEL_INFLUXDB_STORAGE", default="INFO"
    )

    KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECTOR = _get_log_level(
        "KASA_COLLECTOR_LOG_LEVEL_KASA_COLLECTOR", default="INFO"
    )

    # Comma-separated list of device hosts (IPs) for manual configuration.
    KASA_COLLECTOR_DEVICE_HOSTS = os.getenv("KASA_COLLECTOR_DEVICE_HOSTS", None)

    # TP-Link account credentials for devices that require login. Default is None.
    KASA_COLLECTOR_TPLINK_USERNAME = os.getenv("KASA_COLLECTOR_TPLINK_USERNAME", None)
    KASA_COLLECTOR_TPLINK_PASSWORD = os.getenv("KASA_COLLECTOR_TPLINK_PASSWORD", None)

    KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY = _get_bool_config(
        "KASA_COLLECTOR_ENABLE_AUTO_DISCOVERY", default=True
    )

    # Authentication settings
    KASA_COLLECTOR_AUTH_MAX_RETRIES = _get_int_config(
        "KASA_COLLECTOR_AUTH_MAX_RETRIES", default=3, min_value=1
    )

    KASA_COLLECTOR_AUTH_TIMEOUT = _get_int_config(
        "KASA_COLLECTOR_AUTH_TIMEOUT", default=10, min_value=1
    )

    # Operational timeouts
    KASA_COLLECTOR_TRANSPORT_CLEANUP_TIMEOUT = _get_int_config(
        "KASA_COLLECTOR_TRANSPORT_CLEANUP_TIMEOUT", default=5, min_value=1
    )

    KASA_COLLECTOR_SHUTDOWN_TIMEOUT = _get_int_config(
        "KASA_COLLECTOR_SHUTDOWN_TIMEOUT", default=10, min_value=1
    )

    KASA_COLLECTOR_DNS_CACHE_TTL = _get_int_config(
        "KASA_COLLECTOR_DNS_CACHE_TTL", default=300, min_value=0
    )

    KASA_COLLECTOR_MAX_RETRY_DELAY = _get_int_config(
        "KASA_COLLECTOR_MAX_RETRY_DELAY", default=60, min_value=1
    )

    # Health check settings
    KASA_COLLECTOR_HEALTH_CHECK_MAX_AGE = _get_int_config(
        "KASA_COLLECTOR_HEALTH_CHECK_MAX_AGE", default=120, min_value=1
    )
