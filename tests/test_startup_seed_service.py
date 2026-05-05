from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import startup_seed_service


@pytest.mark.anyio
async def test_seed_admin_demo_data_runs_for_default_admin(monkeypatch):
    calls = []

    monkeypatch.setattr(startup_seed_service.settings, "seed_demo_on_startup", True)
    monkeypatch.setattr(startup_seed_service.settings, "seed_demo_base_url", "http://backend:8000")
    monkeypatch.setattr(
        startup_seed_service.user_repo,
        "get_by_email",
        lambda email: {"user_id": "admin-id", "email": email, "username": "admin"},
    )
    monkeypatch.setattr(startup_seed_service, "create_access_token", lambda user_id: f"token-for-{user_id}")
    monkeypatch.setattr(startup_seed_service, "_wait_for_backend", lambda base_url: _async_return(True))

    async def fake_run(args):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(startup_seed_service, "_run_python_module", fake_run)

    await startup_seed_service.seed_admin_demo_data_on_startup()

    assert calls == [
        [
            "-m",
            "mocker.run",
            "--full",
            "--url",
            "http://backend:8000",
            "--auth-token",
            "token-for-admin-id",
        ],
        [
            "-m",
            "mocker.create_mappings",
            "--url",
            "http://backend:8000",
            "--auth-token",
            "token-for-admin-id",
        ],
    ]


@pytest.mark.anyio
async def test_seed_admin_demo_data_skips_non_admin_user(monkeypatch):
    monkeypatch.setattr(startup_seed_service.settings, "seed_demo_on_startup", True)
    monkeypatch.setattr(
        startup_seed_service.user_repo,
        "get_by_email",
        lambda email: {"user_id": "user-id", "email": email, "username": "not-admin"},
    )

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("mocker commands should not run for non-admin user")

    monkeypatch.setattr(startup_seed_service, "_wait_for_backend", fail_if_called)
    monkeypatch.setattr(startup_seed_service, "_run_python_module", fail_if_called)

    await startup_seed_service.seed_admin_demo_data_on_startup()


@pytest.mark.anyio
async def test_seed_admin_demo_data_can_be_disabled(monkeypatch):
    monkeypatch.setattr(startup_seed_service.settings, "seed_demo_on_startup", False)

    async def fail_if_called(*args, **kwargs):
        raise AssertionError("mocker commands should not run when seed is disabled")

    monkeypatch.setattr(startup_seed_service, "_wait_for_backend", fail_if_called)
    monkeypatch.setattr(startup_seed_service, "_run_python_module", fail_if_called)

    await startup_seed_service.seed_admin_demo_data_on_startup()


async def _async_return(value):
    return value
