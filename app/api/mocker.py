from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()
log = logging.getLogger(__name__)


class MockerCommandResponse(BaseModel):
    command: str
    success: bool
    exit_code: int
    summary: str
    stdout: str = ""
    stderr: str = ""


async def _run_mocker_command(args: List[str], command_name: str) -> MockerCommandResponse:
    command = [sys.executable, *args]
    rendered_command = " ".join(command)

    try:
        completed = await asyncio.to_thread(
            subprocess.run,
            command,
            cwd="/opt/app",
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return MockerCommandResponse(
            command=rendered_command,
            success=False,
            exit_code=124,
            summary=f"{command_name} timed out",
            stdout=exc.stdout or "",
            stderr=exc.stderr or "",
        )

    success = completed.returncode == 0
    summary = f"{command_name} completed successfully" if success else f"{command_name} failed"

    return MockerCommandResponse(
        command=rendered_command,
        success=success,
        exit_code=completed.returncode,
        summary=summary,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


@router.post(
    "/run-full",
    response_model=MockerCommandResponse,
    summary="Run full mock data generation",
)
async def run_full_generation() -> MockerCommandResponse:
    log.info("Running mocker full generation via API")
    return await _run_mocker_command(
        ["-m", "mocker.run", "--full", "--url", "http://localhost:8000"],
        command_name="mocker.run --full",
    )


@router.post(
    "/create-mappings",
    response_model=MockerCommandResponse,
    summary="Create mappings via mocker script",
)
async def create_mappings() -> MockerCommandResponse:
    log.info("Running mocker mapping creation via API")
    return await _run_mocker_command(
        ["-m", "mocker.create_mappings", "--url", "http://localhost:8000"],
        command_name="mocker.create_mappings",
    )
