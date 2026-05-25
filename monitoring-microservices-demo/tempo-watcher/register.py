"""Auto-registration module for watchers.
Registers as an agent with the resource graph app on startup.
"""
import os
import time
import logging

import requests

log = logging.getLogger("register")

RESOURCE_API_URL = os.environ.get("RESOURCE_API_URL", "http://localhost:8000")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")
APP_NAME = os.environ.get("APP_NAME")


def _wait_for_api(base_url: str, timeout: int = 120, interval: float = 3.0):
    """Block until the API /health endpoint responds 200."""
    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        try:
            resp = requests.get(f"{base_url}/health", timeout=5)
            if resp.status_code == 200:
                log.info("API at %s is available", base_url)
                return
        except Exception:
            pass
        attempt += 1
        if attempt % 10 == 0:
            log.warning("Still waiting for API at %s (%d attempts)", base_url, attempt)
        time.sleep(interval)
    raise RuntimeError(f"API at {base_url} not available after {timeout}s")


def _login(base_url: str, email: str, password: str) -> str:
    """POST /api/v1/auth/login, return access_token."""
    resp = requests.post(
        f"{base_url}/api/v1/auth/login",
        json={"email": email, "password": password},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def _register_app(base_url: str, jwt: str, app_name: str) -> str:
    """POST /api/v1/apps/register, return app_token."""
    resp = requests.post(
        f"{base_url}/api/v1/apps/register",
        json={"name": app_name, "description": f"Application: {app_name}"},
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )
    resp.raise_for_status()
    app_token = resp.json()["app_token"]
    log.info("Registered app: %s", app_name)
    return app_token


def _register_agent(base_url: str, jwt: str, name: str,
                    source_type: str, app_token: str = None) -> str:
    """POST /api/v1/agents/register, return agent token."""
    body = {"name": name, "source_type": source_type}
    if app_token:
        body["app_token"] = app_token
    resp = requests.post(
        f"{base_url}/api/v1/agents/register",
        json=body,
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def register_agent(agent_name: str, agent_type: str) -> str:
    """Full registration flow: wait for API, login, register app (optional), register agent.
    Returns the agent token string.
    """
    base_url = RESOURCE_API_URL.rstrip("/")
    _wait_for_api(base_url)

    jwt = _login(base_url, ADMIN_EMAIL, ADMIN_PASSWORD)
    log.info("Logged in as %s", ADMIN_EMAIL)

    app_token = None
    if APP_NAME:
        app_token = _register_app(base_url, jwt, APP_NAME)

    agent_token = _register_agent(base_url, jwt, agent_name, agent_type, app_token)
    log.info("Registered agent: %s (token=%s...%s)", agent_name, agent_token[:8], agent_token[-4:])
    return agent_token


def _activate_mapping_template(base_url: str, jwt: str, template_id: str,
                              mapping_name: str, source_type: str):
    """Delete old mapping and instantiate fresh from template."""
    headers = {"Authorization": f"Bearer {jwt}"}

    # Delete existing mappings with the same name to force re-creation
    try:
        resp = requests.get(
            f"{base_url}/api/v1/mapper/",
            params={"source_type": source_type},
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 200:
            for m in resp.json().get("mappings", []):
                mid = m.get("mapping_id") or m.get("id")
                if mid:
                    requests.delete(
                        f"{base_url}/api/v1/mapper/{mid}",
                        headers=headers,
                        timeout=15,
                    )
                    log.info("Deleted old mapping '%s' (%s)", m.get("name"), mid)
    except Exception as e:
        log.warning("Could not delete old mappings: %s", e)

    try:
        resp = requests.post(
            f"{base_url}/api/v1/mapper/templates/{template_id}/instantiate",
            json={"name": mapping_name, "activate": True},
            headers=headers,
            timeout=15,
        )
        if resp.status_code in (200, 201):
            resp.json()
            log.info("Instantiated mapping template '%s' as '%s' (active)", template_id, mapping_name)
        elif resp.status_code == 404:
            log.warning("Mapping template '%s' not found — skip activation", template_id)
        else:
            log.warning("Failed to instantiate template '%s': %s", template_id, resp.text)
    except Exception as e:
        log.warning("Failed to instantiate mapping template: %s", e)


def setup_default_mappings():
    """Ensure default mapping templates are instantiated and active."""
    base_url = RESOURCE_API_URL.rstrip("/")
    _wait_for_api(base_url)
    jwt = _login(base_url, ADMIN_EMAIL, ADMIN_PASSWORD)

    _activate_mapping_template(
        base_url, jwt,
        template_id="watcher-otel-traces-v1",
        mapping_name="Watcher OTel Traces",
        source_type="watcher-otel-traces",
    )
