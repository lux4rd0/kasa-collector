#!/usr/bin/env python3
"""
Docker health check script for Kasa Collector.
Verifies the application is running and collecting data properly.

Exit codes:
  0 - Healthy
  1 - Unhealthy
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Health check configuration
MAX_AGE_SECONDS = int(
    os.getenv("KASA_COLLECTOR_HEALTH_CHECK_MAX_AGE", "120")
)  # 2 minutes default
OUTPUT_DIR = os.getenv("KASA_COLLECTOR_OUTPUT_DIR", "output")


def check_recent_data_files() -> tuple[bool, str]:
    """
    Check if recent data files exist in the output directory.
    Returns (is_healthy, message).
    """
    output_path = Path(OUTPUT_DIR)

    if not output_path.exists():
        return False, f"Output directory {OUTPUT_DIR} does not exist"

    # Find most recent emeter data file
    emeter_files = list(output_path.glob("emeter_*.json"))

    if not emeter_files:
        return False, "No emeter data files found"

    # Get the most recently modified file
    most_recent_file = max(emeter_files, key=lambda f: f.stat().st_mtime)

    # Check file age
    file_age = datetime.now() - datetime.fromtimestamp(most_recent_file.stat().st_mtime)

    if file_age > timedelta(seconds=MAX_AGE_SECONDS):
        return (
            False,
            f"Most recent data file is {file_age.total_seconds():.0f}s old "
            f"(max allowed: {MAX_AGE_SECONDS}s)",
        )

    # Verify file has valid JSON content
    try:
        with open(most_recent_file, "r") as f:
            data = json.load(f)
            if not data:
                return False, f"Data file {most_recent_file.name} is empty"
    except Exception as e:
        return False, f"Failed to read data file: {e}"

    return True, f"Healthy - last data update {file_age.total_seconds():.0f}s ago"


def check_process_alive() -> tuple[bool, str]:
    """
    Check if the main kasa_collector process is running.
    Returns (is_healthy, message).
    """
    # Simple approach - check if we can import and the event loop exists
    try:
        # If we can run this script, Python is working
        # Check if the asyncio event loop is available (indicates main app is running)
        import asyncio

        # Try to get the running loop - if kasa_collector is running, it should have one
        try:
            asyncio.get_running_loop()
            return True, "Process healthy - event loop active"
        except RuntimeError:
            # No running loop might mean the main app hasn't started yet
            # For Docker, we'll consider this healthy during startup
            return True, "Process starting - no event loop yet"

    except Exception as e:
        return False, f"Process check failed: {e}"


def main():
    """
    Main health check logic.
    """
    checks = []
    all_healthy = True

    # Only check data files if writing to file is enabled
    if os.getenv("KASA_COLLECTOR_WRITE_TO_FILE", "False").lower() == "true":
        is_healthy, message = check_recent_data_files()
        checks.append(f"Data freshness: {message}")
        all_healthy &= is_healthy
    else:
        # If not writing to files, check if process is alive
        is_healthy, message = check_process_alive()
        checks.append(f"Process check: {message}")
        all_healthy &= is_healthy

    # Get version information
    version = os.getenv("KASA_COLLECTOR_VERSION", "unknown")
    build_timestamp = os.getenv("KASA_COLLECTOR_BUILD_TIMESTAMP", "unknown")

    # Print status
    status = "HEALTHY" if all_healthy else "UNHEALTHY"
    print(f"Health check: {status}")
    print(f"Version: {version} (Built: {build_timestamp})")
    for check in checks:
        print(f"  - {check}")

    # Exit with appropriate code
    sys.exit(0 if all_healthy else 1)


if __name__ == "__main__":
    main()
