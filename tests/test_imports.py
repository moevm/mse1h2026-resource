from __future__ import annotations

import importlib

import pytest

MODULES = [
    "app.config",
    "app.core.security",
    "app.models.user",
    "app.models.export",
    "app.models.topology",
    "app.models.agent",
    "app.models.application",
    "app.services.export_service",
    "app.services.graph_service",
    "app.api.auth",
    "app.api.export",
    "app.api.graph",
    "app.api.agents",
    "app.api.applications",
    "app.api.mapper_config",
    "app.models.mapper.template",
    "app.repositories.user_repo",
    "app.repositories.agent_repo",
    "app.repositories.application_repo",
    "app.repositories.session_repo",
    "app.repositories.mapping_repo",
    "app.repositories.mapping_template_repo",
]


@pytest.mark.parametrize("module_name", MODULES)
def test_module_imports(module_name):
    importlib.import_module(module_name)


def test_main_app_module_importable():
    importlib.import_module("app.main")


def test_fastapi_app_has_expected_routes():
    from app.main import app

    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert any(p.startswith("/api/v1/auth") for p in paths)
    assert any(p.startswith("/api/v1/graph") for p in paths)
    assert any(p.startswith("/api/v1/export") for p in paths)
    assert any(p.startswith("/api/v1/mapper/templates") for p in paths)
