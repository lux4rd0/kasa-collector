# Use the official Python image as the base image
FROM python:3.13.5-slim AS base

# Set the working directory inside the container
WORKDIR /app/kasa_collector

# Install system dependencies if needed (currently none required)
# This layer rarely changes
RUN apt-get update && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file for better caching
# This layer will be cached unless requirements.txt changes
COPY requirements.txt ./

# Upgrade pip and install required packages
# This layer will be cached unless requirements.txt changes
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy the application source files
# This layer will be rebuilt when source code changes
COPY ./src/*.py ./

# Build arguments for version information (moved after COPY to not break cache)
ARG BUILD_VERSION=unknown
ARG BUILD_TIMESTAMP=unknown

# Set environment variables from build args
ENV KASA_COLLECTOR_VERSION=${BUILD_VERSION} \
    KASA_COLLECTOR_BUILD_TIMESTAMP=${BUILD_TIMESTAMP} \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Create non-root user for security
RUN useradd -m -s /bin/bash appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Docker health check
# Checks every 30s (after initial 30s delay), times out after 10s, retries 3 times before marking unhealthy
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD ["python3", "./health_check.py"]

# Run your Python script
CMD ["python3", "./kasa_collector.py"]
