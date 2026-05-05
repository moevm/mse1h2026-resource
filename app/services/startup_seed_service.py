from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from pathlib import Path
from typing import Sequence

import httpx

from app.config import settings
from app.core.security import create_access_token
from app.repositories import user_repo

log = logging.getLogger(__name__)

ADMIN_EMAIL = "admin@example.com"
ADMIN_USERNAME = "admin"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


async def seed_admin_demo_data_on_startup() -> None:
    """Seed demo graph data and mappings for the built-in admin user only."""

    if not settings.seed_demo_on_startup:
        log.info("Startup demo seed is disabled")
        return

    admin = user_repo.get_by_email(ADMIN_EMAIL)
    if not admin or admin.get("username") != ADMIN_USERNAME:
        log.warning(
            "Skipping startup demo seed: expected admin user %s / %s was not found",
            ADMIN_EMAIL,
            ADMIN_USERNAME,
        )
        return

    token = create_access_token(admin["user_id"])
    base_url = settings.seed_demo_base_url.rstrip("/")

    if not await _wait_for_backend(base_url):
        log.warning("Skipping startup demo seed: backend did not become ready at %s", base_url)
        return

    commands = [
        (
            "create test data",
            ["-m", "mocker.run", "--full", "--url", base_url, "--auth-token", token],
        ),
        (
            "create test mappings",
            ["-m", "mocker.create_mappings", "--url", base_url, "--auth-token", token],
        ),
    ]

    for label, args in commands:
        result = await _run_python_module(args)
        if result.returncode == 0:
            log.info("Startup demo seed step succeeded: %s", label)
            if result.stdout:
                log.debug("%s stdout:\n%s", label, result.stdout)
        else:
            log.warning(
                "Startup demo seed step failed: %s (exit_code=%s)\nstdout:\n%s\nstderr:\n%s",
                label,
                result.returncode,
                result.stdout,
                result.stderr,
            )


async def _wait_for_backend(base_url: str, attempts: int = 30, delay_seconds: float = 1.0) -> bool:
    async with httpx.AsyncClient(timeout=2) as client:
        for _ in range(attempts):
            try:
                response = await client.get(f"{base_url}/health")
                if response.status_code == 200:
                    return True
            except httpx.RequestError:
                pass
            await asyncio.sleep(delay_seconds)
    return False


async def _run_python_module(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, *args]
    return await asyncio.to_thread(
        subprocess.run,
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=900,
        check=False,
    )
