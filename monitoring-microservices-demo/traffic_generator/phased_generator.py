"""Phased traffic generator for monitoring demo.

Generates traffic progressively in 6 phases so the graph topology
evolves over time instead of appearing all at once.
"""
import logging
import os
import random
import time

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("traffic-gen")

FASTAPI_URL = os.environ.get("FASTAPI_URL", "http://fastapi-app:8000")
FLASK_URL = os.environ.get("FLASK_URL", "http://flask-app:8001")
GOLANG_URL = os.environ.get("GOLANG_URL", "http://golang-app:8002")

PHASES = [
    {
        "name": "Phase 1: FastAPI basic queries",
        "start": 0,
        "end": 30,
        "targets": [
            ("GET", f"{FASTAPI_URL}/users"),
            ("GET", f"{FASTAPI_URL}/"),
        ],
        "rate": (1, 3),
    },
    {
        "name": "Phase 2: Flask gateway joins",
        "start": 30,
        "end": 60,
        "targets": [
            ("GET", f"{FLASK_URL}/api/v1/users"),
            ("GET", f"{FLASK_URL}/api/v1/users/testuser"),
            ("GET", f"{FASTAPI_URL}/users"),
        ],
        "rate": (2, 4),
    },
    {
        "name": "Phase 3: Golang products",
        "start": 60,
        "end": 90,
        "targets": [
            ("GET", f"{FLASK_URL}/api/v1/products"),
            ("GET", f"{FLASK_URL}/api/v1/products/1"),
            ("GET", f"{GOLANG_URL}/albums"),
            ("GET", f"{GOLANG_URL}/categories"),
            ("GET", f"{FLASK_URL}/api/v1/users"),
        ],
        "rate": (3, 6),
    },
    {
        "name": "Phase 4: External APIs + payments",
        "start": 90,
        "end": 120,
        "targets": [
            ("GET", f"{FLASK_URL}/api/v1/analytics"),
            ("POST", f"{FLASK_URL}/api/v1/payments"),
            ("GET", f"{FLASK_URL}/api/v1/payments/health"),
            ("GET", f"{FLASK_URL}/api/v1/products"),
            ("GET", f"{FLASK_URL}/api/v1/users"),
        ],
        "rate": (4, 7),
    },
    {
        "name": "Phase 5: Orders + notifications (queues)",
        "start": 120,
        "end": 150,
        "targets": [
            ("POST", f"{FLASK_URL}/api/v1/orders"),
            ("POST", f"{FLASK_URL}/api/v1/notifications"),
            ("GET", f"{FLASK_URL}/api/v1/analytics"),
            ("GET", f"{FLASK_URL}/api/v1/users"),
            ("GET", f"{FLASK_URL}/api/v1/products"),
        ],
        "rate": (4, 8),
    },
    {
        "name": "Phase 6: Full traffic with recommendations",
        "start": 150,
        "end": None,
        "targets": [
            ("GET", f"{FLASK_URL}/api/v1/users"),
            ("GET", f"{FLASK_URL}/api/v1/users/testuser"),
            ("POST", f"{FLASK_URL}/api/v1/users"),
            ("GET", f"{FLASK_URL}/api/v1/products"),
            ("GET", f"{FLASK_URL}/api/v1/products/1"),
            ("POST", f"{FLASK_URL}/api/v1/orders"),
            ("GET", f"{FLASK_URL}/api/v1/analytics"),
            ("GET", f"{FLASK_URL}/api/v1/recommendations"),
            ("POST", f"{FLASK_URL}/api/v1/notifications"),
            ("POST", f"{FLASK_URL}/api/v1/payments"),
            ("GET", f"{FLASK_URL}/api/v1/payments/health"),
            ("GET", f"{FLASK_URL}/health"),
            ("GET", f"{FASTAPI_URL}/"),
            ("GET", f"{FASTAPI_URL}/users"),
            ("GET", f"{GOLANG_URL}/albums"),
            ("GET", f"{GOLANG_URL}/categories"),
            ("GET", f"{GOLANG_URL}/stats"),
        ],
        "rate": (5, 12),
    },
]


def get_active_phase(elapsed: float) -> list:
    """Return list of (method, url) targets active at given elapsed time."""
    active = []
    for phase in PHASES:
        start = phase["start"]
        end = phase["end"]
        if elapsed >= start and (end is None or elapsed < end):
            active.extend(phase["targets"])
            if elapsed < start + 5:
                log.info("Started %s", phase["name"])
    return active


def get_current_rate(elapsed: float) -> tuple:
    """Return (min_delay, max_delay) for current phase."""
    for phase in reversed(PHASES):
        if elapsed >= phase["start"]:
            return phase["rate"]
    return (3, 8)


def wait_for_service(url: str, timeout: int = 120):
    """Wait until a service responds, polling every 3 seconds."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(url, timeout=3)
            if resp.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(3)
    return False


def main():
    log.info("Phased traffic generator starting...")
    log.info("Waiting for Flask app at %s", FLASK_URL)
    wait_for_service(f"{FLASK_URL}/health")
    log.info("Flask app is up. Waiting for FastAPI at %s", FASTAPI_URL)
    wait_for_service(f"{FASTAPI_URL}/")
    log.info("FastAPI is up. Waiting for Golang at %s", GOLANG_URL)
    wait_for_service(f"{GOLANG_URL}/albums")

    log.info("All services are up. Starting phased traffic generation.")
    start_time = time.time()

    while True:
        elapsed = time.time() - start_time
        targets = get_active_phase(elapsed)

        if not targets:
            time.sleep(1)
            continue

        min_delay, max_delay = get_current_rate(elapsed)
        delay = random.uniform(min_delay, max_delay)

        method, url = random.choice(targets)
        try:
            if method == "POST":
                resp = requests.post(url, json={}, timeout=5)
            else:
                resp = requests.get(url, timeout=5)
            log.info("%s %s -> %d (%.0fs elapsed)", method, url.replace(FLASK_URL, "flask").replace(FASTAPI_URL, "fastapi").replace(GOLANG_URL, "golang"), resp.status_code, elapsed)
        except Exception as e:
            log.debug("Request failed: %s %s -> %s", method, url, e)

        time.sleep(delay)


if __name__ == "__main__":
    main()
