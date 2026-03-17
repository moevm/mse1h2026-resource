#!/usr/bin/env python3
"""
Resource Graph Mocker - Multi-agent log producer.

Simulates multiple monitoring agents sending logs from different sources:
- Kubernetes API (pods, deployments, services, nodes)
- OpenTelemetry traces
- Istio access logs
- Prometheus metrics
- etc.

Usage:
    python -m mocker.run                    # Run all agents with default config
    python -m mocker.run --agents k8s,otel  # Run specific agents
    python -m mocker.run --list             # List available agents
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import signal
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal

import httpx

from mocker.shared_state import SharedState
from mocker.raw_generator import generate_raw_data, RAW_GENERATORS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("mocker")

# Colors for terminal output
_COLORS = {
    "green": "\033[92m",
    "yellow": "\033[93m",
    "red": "\033[91m",
    "cyan": "\033[96m",
    "purple": "\033[95m",
    "blue": "\033[94m",
    "reset": "\033[0m",
}


def _color(text: str, color: str) -> str:
    return f"{_COLORS.get(color, '')}{text}{_COLORS['reset']}"


@dataclass
class AgentConfig:
    """Configuration for a simulated agent."""
    name: str
    source_type: str
    interval_min: float = 2.0
    interval_max: float = 10.0
    batch_size_min: int = 1
    batch_size_max: int = 5
    enabled: bool = True
    color: str = "cyan"
    description: str = ""


# Default agent configurations - realistic monitoring agents
DEFAULT_AGENTS: List[AgentConfig] = [
    AgentConfig(
        name="k8s-api-watcher",
        source_type="kubernetes-api",
        interval_min=5.0,
        interval_max=15.0,
        batch_size_min=2,
        batch_size_max=8,
        color="cyan",
        description="Kubernetes API - pods, deployments, services",
    ),
    AgentConfig(
        name="otel-collector",
        source_type="opentelemetry-traces",
        interval_min=1.0,
        interval_max=3.0,
        batch_size_min=5,
        batch_size_max=20,
        color="purple",
        description="OpenTelemetry traces from microservices",
    ),
    AgentConfig(
        name="otel-metrics",
        source_type="opentelemetry-metrics",
        interval_min=10.0,
        interval_max=30.0,
        batch_size_min=1,
        batch_size_max=3,
        color="blue",
        description="OpenTelemetry metrics",
    ),
    AgentConfig(
        name="istio-proxy-logs",
        source_type="istio-access-logs",
        interval_min=0.5,
        interval_max=2.0,
        batch_size_min=10,
        batch_size_max=50,
        color="yellow",
        description="Istio sidecar proxy access logs",
    ),
    AgentConfig(
        name="istio-metrics",
        source_type="istio-metrics",
        interval_min=5.0,
        interval_max=15.0,
        batch_size_min=1,
        batch_size_max=5,
        color="green",
        description="Istio/Prometheus metrics from mesh",
    ),
    AgentConfig(
        name="prometheus-scrape",
        source_type="prometheus",
        interval_min=15.0,
        interval_max=60.0,
        batch_size_min=1,
        batch_size_max=3,
        color="red",
        description="Prometheus metrics scrape",
    ),
    AgentConfig(
        name="prometheus-slo",
        source_type="prometheus-slo",
        interval_min=30.0,
        interval_max=60.0,
        batch_size_min=1,
        batch_size_max=2,
        color="yellow",
        description="Prometheus SLO metrics",
    ),
    AgentConfig(
        name="terraform-state",
        source_type="terraform-state",
        interval_min=60.0,
        interval_max=300.0,
        batch_size_min=1,
        batch_size_max=1,
        color="yellow",
        description="Terraform state changes (infrastructure)",
    ),
    AgentConfig(
        name="argocd-sync",
        source_type="argocd",
        interval_min=10.0,
        interval_max=30.0,
        batch_size_min=1,
        batch_size_max=5,
        color="cyan",
        description="ArgoCD application sync status",
    ),
    AgentConfig(
        name="api-gateway-routes",
        source_type="api-gateway",
        interval_min=30.0,
        interval_max=120.0,
        batch_size_min=1,
        batch_size_max=3,
        color="blue",
        description="API Gateway routes and endpoints",
    ),
]


class LogProducer:
    """Simulates a single monitoring agent producing logs."""

    def __init__(
        self,
        config: AgentConfig,
        base_url: str,
        client: httpx.AsyncClient,
        app_token: str | None = None,
        once: bool = False,
        shared_state: SharedState | None = None,
    ):
        self.config = config
        self.base_url = base_url
        self.client = client
        self.token: str | None = None
        self.app_token = app_token
        self.once = once
        self.shared_state = shared_state
        self.running = False
        self.stats = {"sent": 0, "errors": 0, "bytes": 0}

    async def register(self) -> bool:
        """Register this agent with the backend."""
        url = f"{self.base_url}/api/v1/agents/register"
        payload = {
            "name": self.config.name,
            "source_type": self.config.source_type,
            "description": self.config.description,
        }
        if self.app_token:
            payload["app_token"] = self.app_token

        for attempt in range(1, 6):
            try:
                resp = await self.client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                self.token = data["token"]
                log.info(
                    _color(f"✓ [{self.config.name}] Registered (token: {self.token[:8]}...)", self.config.color)
                )
                return True
            except Exception as exc:
                log.warning(
                    f"[{self.config.name}] Registration attempt {attempt}/5 failed: {exc}"
                )
                await asyncio.sleep(2)

        log.error(_color(f"✗ [{self.config.name}] Failed to register", "red"))
        return False

    async def send_batch(self, items: List[Dict[str, Any]]) -> bool:
        """Send a batch of raw data items."""
        if not self.token:
            return False

        url = f"{self.base_url}/api/v1/receiver/raw"
        results = []

        for item in items:
            try:
                resp = await self.client.post(
                    url,
                    json=item,
                    params={"source_type": self.config.source_type},
                    headers={"X-Agent-Token": self.token},
                    timeout=15,
                )
                resp.raise_for_status()
                results.append(resp.json())
                self.stats["sent"] += 1
                self.stats["bytes"] += len(json.dumps(item))
            except Exception as exc:
                self.stats["errors"] += 1
                log.debug(f"[{self.config.name}] Error sending item: {exc}")

        return len(results) > 0

    async def run(self, stop_event: asyncio.Event) -> None:
        """Main loop for this producer."""
        if not await self.register():
            return

        self.running = True
        tick = 0

        # If once mode, send one batch and exit
        if self.once:
            batch_size = random.randint(self.config.batch_size_min, self.config.batch_size_max)
            items = []
            for _ in range(batch_size):
                item = generate_raw_data(self.shared_state, self.config.source_type, tick)
                items.append(item)

            start_time = time.time()
            success = await self.send_batch(items)
            elapsed = time.time() - start_time

            status = _color("▶", self.config.color)
            log.info(
                f"{status} [{self.config.name:20s}] "
                f"sent={_color(str(len(items)), self.config.color):3s} "
                f"elapsed={elapsed*1000:6.1f}ms"
            )
            self.running = False
            return

        while not stop_event.is_set():
            # Random interval
            interval = random.uniform(self.config.interval_min, self.config.interval_max)

            # Random batch size
            batch_size = random.randint(self.config.batch_size_min, self.config.batch_size_max)

            # Generate batch
            items = []
            for _ in range(batch_size):
                item = generate_raw_data(self.shared_state, self.config.source_type, tick)
                items.append(item)

            # Send
            start_time = time.time()
            success = await self.send_batch(items)
            elapsed = time.time() - start_time

            # Log
            status = _color("▶", self.config.color)
            log.info(
                f"{status} [{self.config.name:20s}] "
                f"sent={_color(str(len(items)), self.config.color):3s} "
                f"interval={interval:5.1f}s "
                f"elapsed={elapsed*1000:6.1f}ms "
                f"total={self.stats['sent']:5d}"
            )

            tick += 1

            # Wait for next interval (or stop)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
                break  # Stop event was set
            except asyncio.TimeoutError:
                pass  # Interval passed, continue

        self.running = False
        log.info(
            _color(f"⏹ [{self.config.name}] Stopped (sent={self.stats['sent']}, errors={self.stats['errors']})", "yellow")
        )


class MockerOrchestrator:
    """Manages multiple log producers."""

    def __init__(self, base_url: str, agents: List[AgentConfig], app_name: str | None = None, once: bool = False):
        self.base_url = base_url
        self.agents = agents
        self.producers: List[LogProducer] = []
        self.stop_event = asyncio.Event()
        self.app_name = app_name
        self.app_token: str | None = None
        self.once = once
        # Create shared state for consistent data across all producers
        self.shared_state = SharedState()

    async def register_application(self, client: httpx.AsyncClient) -> bool:
        """Register application and get app_token."""
        if not self.app_name:
            return True  # No application registration needed

        url = f"{self.base_url}/api/v1/apps/register"
        try:
            resp = await client.post(
                url,
                json={
                    "name": self.app_name,
                    "description": f"Mock application for testing",
                    "owner": "mocker",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            self.app_token = data["app_token"]
            log.info(_color(f"✓ Application registered: {self.app_name} (token: {self.app_token[:8]}...)", "green"))
            return True
        except Exception as exc:
            log.error(f"Failed to register application: {exc}")
            return False

    async def run(self) -> None:
        """Start all producers."""
        log.info(f"Starting mocker with {len(self.agents)} agents → {self.base_url}")
        if self.app_name:
            log.info(f"Application: {self.app_name}")

        # Print shared state stats
        stats = self.shared_state.get_stats()
        log.info(f"Shared state: {stats['services']} services, {stats['nodes']} nodes, {stats['pods']} pods")
        log.info("=" * 70)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            # Register application first
            if self.app_name and not await self.register_application(client):
                return

            # Create producers with app_token and shared_state
            self.producers = [
                LogProducer(config, self.base_url, client, self.app_token, self.once, self.shared_state)
                for config in self.agents
            ]

            # Run all producers concurrently
            tasks = [
                asyncio.create_task(producer.run(self.stop_event))
                for producer in self.producers
            ]

            # Wait for all tasks (they run until stop_event)
            try:
                await asyncio.gather(*tasks)
            except asyncio.CancelledError:
                pass

        # Print summary
        self._print_summary()

    def stop(self) -> None:
        """Signal all producers to stop."""
        log.info("Stopping all agents...")
        self.stop_event.set()

    def _print_summary(self) -> None:
        """Print final statistics."""
        log.info("=" * 70)
        log.info("Mocker Summary:")

        total_sent = 0
        total_errors = 0
        total_bytes = 0

        for producer in self.producers:
            total_sent += producer.stats["sent"]
            total_errors += producer.stats["errors"]
            total_bytes += producer.stats["bytes"]

            log.info(
                f"  [{producer.config.name:20s}] "
                f"sent={producer.stats['sent']:5d} "
                f"errors={producer.stats['errors']:3d} "
                f"size={producer.stats['bytes'] / 1024:7.1f}KB"
            )

        log.info("-" * 70)
        log.info(
            f"  {'TOTAL':20s} "
            f"sent={total_sent:5d} "
            f"errors={total_errors:3d} "
            f"size={total_bytes / 1024:7.1f}KB"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resource Graph Mocker - Multi-agent log producer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python -m mocker.run                     # Run all agents
    python -m mocker.run --agents k8s,otel   # Run specific agents
    python -m mocker.run --list              # List available agents
    python -m mocker.run --url http://prod-server:8000  # Custom URL
        """,
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Backend base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--agents",
        type=str,
        default="all",
        help="Comma-separated agent names or source types to run (default: all)",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available agents and exit",
    )
    parser.add_argument(
        "--interval-multiplier",
        type=float,
        default=1.0,
        help="Multiply all intervals by this factor (e.g., 0.5 for faster)",
    )
    parser.add_argument(
        "--app-name",
        type=str,
        default=None,
        help="Register agents under this application name",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Send one batch per agent and exit",
    )

    args = parser.parse_args()

    # List mode
    if args.list:
        print("\nAvailable agents:")
        print("=" * 70)
        for i, agent in enumerate(DEFAULT_AGENTS, 1):
            print(f"{i:2d}. {agent.name:20s} [{agent.source_type}]")
            print(f"    {agent.description}")
            print(f"    interval: {agent.interval_min:.1f}s - {agent.interval_max:.1f}s, "
                  f"batch: {agent.batch_size_min}-{agent.batch_size_max}")
        print()
        return

    # Filter agents
    if args.agents.lower() == "all":
        selected_agents = DEFAULT_AGENTS.copy()
    else:
        # Parse agent specifiers (can be name or source_type or partial match)
        specifiers = [s.strip().lower() for s in args.agents.split(",")]
        selected_agents = []

        for agent in DEFAULT_AGENTS:
            # Match by full name, full source_type, or partial (k8s -> kubernetes-api)
            agent_name_lower = agent.name.lower()
            source_type_lower = agent.source_type.lower()

            for spec in specifiers:
                if (spec == agent_name_lower or
                    spec == source_type_lower or
                    spec in agent_name_lower or
                    spec in source_type_lower or
                    source_type_lower.startswith(spec) or
                    agent_name_lower.startswith(spec)):
                    selected_agents.append(agent)
                    break

        if not selected_agents:
            log.error(f"No agents matched: {args.agents}")
            log.info("Use --list to see available agents")
            sys.exit(1)

    # Apply interval multiplier
    if args.interval_multiplier != 1.0:
        for agent in selected_agents:
            agent.interval_min *= args.interval_multiplier
            agent.interval_max *= args.interval_multiplier

    # Print banner
    log.info("╔════════════════════════════════════════════════════════════════════╗")
    log.info("║          Resource Graph Mocker - Multi-Agent Log Producer          ║")
    log.info("╚════════════════════════════════════════════════════════════════════╝")
    log.info(f"Target: {args.url}")
    log.info(f"Agents: {', '.join(a.name for a in selected_agents)}")
    log.info(f"Speed: {args.interval_multiplier}x")
    if args.app_name:
        log.info(f"App: {args.app_name}")
    log.info("")

    # Run orchestrator
    orchestrator = MockerOrchestrator(args.url, selected_agents, app_name=args.app_name, once=args.once)

    # Handle signals
    def signal_handler(sig, frame):
        orchestrator.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Run
    asyncio.run(orchestrator.run())


if __name__ == "__main__":
    main()
