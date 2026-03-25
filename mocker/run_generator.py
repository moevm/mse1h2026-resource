#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
import time

import httpx

from mocker.generator import generate_update

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("mocker")

_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_CYAN = "\033[96m"
_RESET = "\033[0m"


def _color(text: str, code: str) -> str:
    return f"{code}{text}{_RESET}"


def register_agent(client: httpx.Client, base_url: str, name: str) -> str:
    url = f"{base_url}/api/v1/agents/register"
    for attempt in range(1, 11):
        try:
            resp = client.post(url, json={
                "name": name,
                "source_type": "mock",
                "description": "Real-time mock topology generator"
            })
            resp.raise_for_status()
            data = resp.json()
            token = data["token"]
            log.info(_color(f"✓ Registered as agent '{data['name']}' | token: {token[:8]}...", _GREEN))
            return token
        except Exception as exc:
            log.warning(f"Registration attempt {attempt}/10 failed: {exc}. Retrying in 3s...")
            time.sleep(3)
    log.error(_color("✗ Failed to register agent after 10 attempts", _RED))
    sys.exit(1)


def send_update(client: httpx.Client, base_url: str, token: str, payload: dict) -> dict:
    url = f"{base_url}/api/v1/ingest/topology"
    resp = client.post(url, json=payload, headers={"X-Agent-Token": token}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _scenario_banner(t: int) -> str:
    parts = []
    if (t % 60) in range(0, 6):
        parts.append(_color("⚡ LOAD SPIKE", _YELLOW))
    if (t % 90) in range(0, 10):
        phase = t % 90
        label = "payment" if phase < 4 else ("+ orders" if phase < 8 else "recovering")
        parts.append(_color(f"🔴 CASCADE: {label}", _RED))
    if (t % 120) in range(0, 5):
        parts.append(_color("💥 CACHE STAMPEDE", _YELLOW))
    if (t % 80) in range(0, 8):
        parts.append(_color("🔄 ROLLOUT: search-service", _CYAN))
    if not parts:
        parts.append(_color("✅ NOMINAL", _GREEN))
    return " | ".join(parts)


def main():
    parser = argparse.ArgumentParser(description="Old-style topology generator")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--interval", type=float, default=5.0, help="Seconds between ticks")
    parser.add_argument("--max-ticks", type=int, default=0, help="Max ticks (0 = infinite)")
    parser.add_argument("--agent-name", default="mock-generator", help="Agent name")
    parser.add_argument("--once", action="store_true", help="Send one update and exit")
    args = parser.parse_args()

    with httpx.Client(base_url=args.url, timeout=30) as client:
        token = register_agent(client, args.url, args.agent_name)

        t = 0
        while args.max_ticks == 0 or t < args.max_ticks:
            payload = generate_update(t)
            node_count = len(payload["nodes"])
            edge_count = len(payload["edges"])

            try:
                result = send_update(client, args.url, token, payload)
                status_icon = _color("▶", _CYAN)
                log.info(
                    f"{status_icon} tick={t:04d} | "
                    f"nodes={_color(str(node_count), _CYAN)} "
                    f"edges={_color(str(edge_count), _CYAN)} | "
                    f"{_scenario_banner(t)}"
                )
            except Exception as exc:
                log.error(f"Failed to send update: {exc}")

            if args.once:
                break

            t += 1
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
