#!/usr/bin/env python3
# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Service waiting utility for integration tests.

This script waits for services from docker-compose.build.yml to be ready before running tests.
Configured to work with the actual service ports and endpoints from the compose file.

For services on the internal network (cvds), health checks are performed via docker exec.
For services exposed to the host, direct HTTP checks are used.
"""

import logging
import os
import subprocess
import sys
import time
from typing import Dict, List, Optional

import requests

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service configuration
# internal=true: service is on cvds network, check via docker exec
# internal=False: service is exposed to host, check via direct HTTP
SERVICES = {
    "milvus": {
        "container_name": "milvus",
        "url": "http://localhost:9091",
        "health_endpoint": "/healthz",
        "timeout": 120,
        "internal": True,
    },
    "cosmos-embed": {
        "container_name": "cosmos-embed",
        "url": "http://localhost:8000",
        "health_endpoint": "/v1/health/ready",
        "timeout": 180,
        "internal": True,
    },
    "visual-search": {
        "container_name": "visual-search",
        "url": "http://localhost:8888",
        "health_endpoint": "/health",
        "timeout": 120,
        "internal": False,
    },
}


def check_http_service(
    service_name: str, url: str, endpoint: str, timeout: int = 60
) -> bool:
    """Check if an HTTP service is ready."""
    full_url = f"{url}{endpoint}"
    start_time = time.time()

    logger.info(f"Checking {service_name} at {full_url}")

    while time.time() - start_time < timeout:
        try:
            response = requests.get(full_url, timeout=5)
            if response.status_code == 200:
                logger.info(f"{service_name} is ready")
                return True
            else:
                logger.debug(f"  {service_name} returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.debug(f"  {service_name} connection failed: {e}")

        time.sleep(2)

    logger.error(f"✗ {service_name} failed to become ready within {timeout}s")
    return False


def check_internal_service(
    service_name: str,
    container_name: str,
    url: str,
    health_endpoint: str,
    timeout: int = 60,
) -> bool:
    """Check if an internal (non-exposed) service is ready via docker exec."""
    full_url = f"{url}{health_endpoint}"
    start_time = time.time()

    logger.info(f"Checking {service_name} at {full_url} (via docker exec)")

    while time.time() - start_time < timeout:
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "curl", "-sf", full_url],
                capture_output=True,
                timeout=10,
            )
            if result.returncode == 0:
                logger.info(f"{service_name} is ready")
                return True
            else:
                logger.debug(
                    f"  {service_name} returned {result.returncode}: {result.stderr.decode().strip()}"
                )
        except subprocess.TimeoutExpired:
            logger.debug(f"  {service_name} check timed out")
        except Exception as e:
            logger.debug(f"  {service_name} check failed: {e}")

        time.sleep(3)

    logger.error(f"✗ {service_name} failed to become ready within {timeout}s")
    return False

def wait_for_services(services: Optional[List[str]] = None) -> bool:
    """Wait for all specified services to be ready."""
    if services is None:
        services = list(SERVICES.keys())

    logger.info(f"Waiting for services: {', '.join(services)}")

    failed_services = []

    for service_name in services:
        if service_name not in SERVICES:
            logger.error(f"Unknown service: {service_name}")
            failed_services.append(service_name)
            continue

        config = SERVICES[service_name]

        if config.get("internal"):
            success = check_internal_service(
                service_name,
                config["container_name"],
                config["url"],
                config["health_endpoint"],
                config["timeout"],
            )
        else:
            success = check_http_service(
                service_name,
                config["url"],
                config["health_endpoint"],
                config["timeout"],
            )

        if not success:
            failed_services.append(service_name)

    if failed_services:
        logger.error(f"Failed to start services: {', '.join(failed_services)}")
        return False

    logger.info("All services are ready!")
    return True

def main():
    """Main function."""
    # Parse command line arguments
    import argparse

    parser = argparse.ArgumentParser(description="Wait for services to be ready")
    parser.add_argument(
        "--services",
        nargs="+",
        default=None,
        help="Services to wait for (default: all services)",
    )
    parser.add_argument(
        "--timeout", type=int, default=300, help="Global timeout in seconds"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--novs", action="store_true", help="Skip visual-search service")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Wait for services
    start_time = time.time()
    success = wait_for_services(args.services)

    elapsed = time.time() - start_time
    logger.info(f"Service check completed in {elapsed:.2f}s")

    if not success:
        logger.error("Some services failed to start")
        sys.exit(1)

    logger.info("All services are ready for testing!")
    sys.exit(0)

if __name__ == "__main__":
    main()
