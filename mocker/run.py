#!/usr/bin/env python3
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
from mocker.full_generator import FullGraphGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("mocker")

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
    name: str
    source_type: str
    interval_min: float = 2.0
    interval_max: float = 10.0
    batch_size_min: int = 1
    batch_size_max: int = 5
    enabled: bool = True
    color: str = "cyan"
    description: str = ""


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
        if not await self.register():
            return

        self.running = True
        tick = 0

        if self.once:
            items = []
            generators = RAW_GENERATORS.get(self.config.source_type, {})

            if self.shared_state is None:
                log.error(f"[{self.config.name}] No shared state available")
                self.running = False
                return

            state = self.shared_state

            if generators:
                for gen_name, generator in generators.items():
                    num_items = random.randint(2, 5)
                    for _ in range(num_items):
                        try:
                            item = generator(state, tick)
                            items.append(item)
                        except Exception as e:
                            log.debug(f"[{self.config.name}] Generator {gen_name} failed: {e}")
            else:
                batch_size = random.randint(self.config.batch_size_min, self.config.batch_size_max)
                for _ in range(batch_size):
                    item = generate_raw_data(state, self.config.source_type, tick)
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

        if self.shared_state is None:
            log.error(f"[{self.config.name}] No shared state available")
            self.running = False
            return

        state = self.shared_state

        while not stop_event.is_set():
            interval = random.uniform(self.config.interval_min, self.config.interval_max)

            batch_size = random.randint(self.config.batch_size_min, self.config.batch_size_max)

            items = []
            for _ in range(batch_size):
                item = generate_raw_data(state, self.config.source_type, tick)
                items.append(item)

            start_time = time.time()
            success = await self.send_batch(items)
            elapsed = time.time() - start_time

            status = _color("▶", self.config.color)
            log.info(
                f"{status} [{self.config.name:20s}] "
                f"sent={_color(str(len(items)), self.config.color):3s} "
                f"interval={interval:5.1f}s "
                f"elapsed={elapsed*1000:6.1f}ms "
                f"total={self.stats['sent']:5d}"
            )

            tick += 1

            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                pass

        self.running = False
        log.info(
            _color(f"⏹ [{self.config.name}] Stopped (sent={self.stats['sent']}, errors={self.stats['errors']})", "yellow")
        )


class MockerOrchestrator:
    def __init__(self, base_url: str, agents: List[AgentConfig], app_name: str | None = None, once: bool = False, full: bool = False):
        self.base_url = base_url
        self.agents = agents
        self.producers: List[LogProducer] = []
        self.stop_event = asyncio.Event()
        self.app_name = app_name
        self.app_token: str | None = None
        self.once = once
        self.full = full
        self.shared_state = SharedState()

    async def register_application(self, client: httpx.AsyncClient) -> bool:
        if not self.app_name:
            return True

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
        log.info(f"Starting mocker with {len(self.agents)} agents → {self.base_url}")
        if self.app_name:
            log.info(f"Application: {self.app_name}")

        stats = self.shared_state.get_stats()
        log.info(f"Shared state: {stats['services']} services, {stats['nodes']} nodes, {stats['pods']} pods")
        log.info("=" * 70)

        async with httpx.AsyncClient(base_url=self.base_url, timeout=30) as client:
            if self.app_name and not await self.register_application(client):
                return

            if self.full:
                await self._run_full_mode(client)
            elif self.once:
                is_initialized = await self._check_graph_initialized(client)
                if not is_initialized:
                    log.info(_color("Graph not initialized, creating minimal connected graph...", "yellow"))
                    await self._run_minimal_graph(client)
                else:
                    log.info(_color("Graph already initialized, sending incremental update...", "green"))
                    self.producers = [
                        LogProducer(config, self.base_url, client, self.app_token, self.once, self.shared_state)
                        for config in self.agents
                    ]
                    tasks = [
                        asyncio.create_task(producer.run(self.stop_event))
                        for producer in self.producers
                    ]
                    try:
                        await asyncio.gather(*tasks)
                    except asyncio.CancelledError:
                        pass
            else:
                self.producers = [
                    LogProducer(config, self.base_url, client, self.app_token, self.once, self.shared_state)
                    for config in self.agents
                ]

                tasks = [
                    asyncio.create_task(producer.run(self.stop_event))
                    for producer in self.producers
                ]

                try:
                    await asyncio.gather(*tasks)
                except asyncio.CancelledError:
                    pass

        self._print_summary()

    async def _check_graph_initialized(self, client: httpx.AsyncClient) -> bool:
        try:
            resp = await client.get(f"{self.base_url}/api/v1/graph/stats")
            resp.raise_for_status()
            stats = resp.json()

            required_nodes = {
                "Service", "Deployment", "Pod", "Node", "Database",
                "Table", "QueueTopic", "Cache", "ExternalAPI",
                "SecretConfig", "Library", "TeamOwner", "SLASLO",
                "RegionCluster", "Endpoint"
            }

            required_edges = {
                "calls", "publishesto", "consumesfrom", "reads",
                "writes", "dependson", "deployedon", "ownedby",
                "authenticatesvia", "ratelimitedby", "fails_over_to"
            }

            node_types = stats.get("node_types", {})
            edge_types = stats.get("edge_types", {})

            nodes_ok = all(node_types.get(t, 0) > 0 for t in required_nodes)
            edges_ok = all(edge_types.get(e, 0) > 0 for e in required_edges)

            log.debug(f"Graph check: nodes_ok={nodes_ok}, edges_ok={edges_ok}")
            log.debug(f"Node types: {node_types}")
            log.debug(f"Edge types: {edge_types}")

            return nodes_ok and edges_ok
        except Exception as e:
            log.debug(f"Error checking graph status: {e}")
            return False

    async def _run_full_mode(self, client: httpx.AsyncClient) -> None:
        log.info(_color("🔷 FULL MODE: Generating complete connected graph", "green"))

        generator = FullGraphGenerator(self.shared_state)
        all_data = generator.generate_all()

        total_items = sum(len(items) for items in all_data.values())
        log.info(f"Generated {total_items} items across {len(all_data)} source types")

        source_type_agents = {
            "kubernetes-api": ("k8s-api-full", "kubernetes-api"),
            "opentelemetry-traces": ("otel-traces-full", "opentelemetry-traces"),
            "opentelemetry-metrics": ("otel-metrics-full", "opentelemetry-metrics"),
            "istio-access-logs": ("istio-logs-full", "istio-access-logs"),
            "istio-metrics": ("istio-metrics-full", "istio-metrics"),
            "prometheus": ("prometheus-full", "prometheus"),
            "prometheus-slo": ("prometheus-slo-full", "prometheus-slo"),
            "terraform-state": ("terraform-full", "terraform-state"),
            "argocd": ("argocd-full", "argocd"),
            "api-gateway": ("api-gateway-full", "api-gateway"),
        }

        total_sent = 0
        total_errors = 0

        for source_type, items in all_data.items():
            if not items:
                continue

            agent_name, source_type_str = source_type_agents.get(source_type, (f"agent-{source_type}", source_type))

            url = f"{self.base_url}/api/v1/agents/register"
            payload = {
                "name": agent_name,
                "source_type": source_type_str,
                "description": f"Full graph generator for {source_type}",
            }
            if self.app_token:
                payload["app_token"] = self.app_token

            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                token = resp.json()["token"]
            except Exception as exc:
                log.error(f"Failed to register {agent_name}: {exc}")
                total_errors += len(items)
                continue

            url = f"{self.base_url}/api/v1/receiver/raw"
            sent = 0
            errors = 0

            for item in items:
                try:
                    resp = await client.post(
                        url,
                        json=item,
                        params={"source_type": source_type_str},
                        headers={"X-Agent-Token": token},
                        timeout=15,
                    )
                    resp.raise_for_status()
                    sent += 1
                except Exception as exc:
                    errors += 1
                    log.debug(f"[{agent_name}] Error sending item: {exc}")

            total_sent += sent
            total_errors += errors

            color = "green" if sent > 0 else "red"
            log.info(
                f"{_color('▶', color)} [{agent_name:25s}] "
                f"sent={_color(str(sent), color):4s} errors={errors}"
            )

        log.info("=" * 70)
        log.info(_color(f"✓ Full graph generation complete: {total_sent} items sent, {total_errors} errors", "green" if total_errors == 0 else "yellow"))


        self.producers = []

    async def _run_minimal_graph(self, client: httpx.AsyncClient) -> None:
        log.info(_color("🔷 MINIMAL MODE: Creating minimal connected graph", "cyan"))

        generator = FullGraphGenerator(self.shared_state)
        minimal_data = generator.generate_minimal()

        total_items = sum(len(items) for items in minimal_data.values())
        log.info(f"Generated {total_items} items across {len(minimal_data)} source types")

        source_type_agents = {
            "kubernetes-api": ("k8s-api-minimal", "kubernetes-api"),
            "terraform-state": ("terraform-minimal", "terraform-state"),
            "opentelemetry-traces": ("otel-traces-minimal", "opentelemetry-traces"),
            "prometheus-slo": ("prometheus-slo-minimal", "prometheus-slo"),
            "argocd": ("argocd-minimal", "argocd"),
        }

        total_sent = 0
        total_errors = 0

        for source_type, items in minimal_data.items():
            if not items:
                continue

            agent_name, source_type_str = source_type_agents.get(source_type, (f"agent-{source_type}", source_type))

            url = f"{self.base_url}/api/v1/agents/register"
            payload = {
                "name": agent_name,
                "source_type": source_type_str,
                "description": f"Minimal graph generator for {source_type}",
            }
            if self.app_token:
                payload["app_token"] = self.app_token

            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                token = resp.json()["token"]
            except Exception as exc:
                log.error(f"Failed to register {agent_name}: {exc}")
                total_errors += len(items)
                continue

            url = f"{self.base_url}/api/v1/receiver/raw"
            sent = 0
            errors = 0

            for item in items:
                try:
                    resp = await client.post(
                        url,
                        json=item,
                        params={"source_type": source_type_str},
                        headers={"X-Agent-Token": token},
                        timeout=15,
                    )
                    resp.raise_for_status()
                    sent += 1
                except Exception as exc:
                    errors += 1
                    log.debug(f"[{agent_name}] Error sending item: {exc}")

            total_sent += sent
            total_errors += errors

            color = "green" if sent > 0 else "red"
            log.info(
                f"{_color('▶', color)} [{agent_name:25s}] "
                f"sent={_color(str(sent), color):4s} errors={errors}"
            )

        log.info("=" * 70)
        log.info(_color(f"✓ Minimal graph generation complete: {total_sent} items sent, {total_errors} errors", "green" if total_errors == 0 else "yellow"))


        self.producers = []

    async def _recreate_all_edges(self, client: httpx.AsyncClient) -> None:
        try:
            log.info("Recreating edges for all nodes...")
            resp = await client.post(
                f"{self.base_url}/api/v1/mapper/recreate-edges",
                json={},
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            log.info(
                _color(
                    f"✓ Edge recreation complete: {data['edges_created']} edges created, "
                    f"{data['unresolved_count']} unresolved references",
                    "green" if data['edges_created'] > 0 else "yellow"
                )
            )
        except Exception as exc:
            log.warning(f"Failed to recreate edges: {exc}")

    def stop(self) -> None:
        log.info("Stopping all agents...")
        self.stop_event.set()

    def _print_summary(self) -> None:
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
    parser.add_argument(
        "--full",
        action="store_true",
        help="Generate complete connected graph with all entities (implies --once)",
    )

    args = parser.parse_args()

    if args.full:
        args.once = True

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

    if args.agents.lower() == "all":
        selected_agents = DEFAULT_AGENTS.copy()
    else:
        specifiers = [s.strip().lower() for s in args.agents.split(",")]
        selected_agents = []

        for agent in DEFAULT_AGENTS:
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

    if args.interval_multiplier != 1.0:
        for agent in selected_agents:
            agent.interval_min *= args.interval_multiplier
            agent.interval_max *= args.interval_multiplier

    log.info("╔════════════════════════════════════════════════════════════════════╗")
    log.info("║          Resource Graph Mocker - Multi-Agent Log Producer          ║")
    log.info("╚════════════════════════════════════════════════════════════════════╝")
    log.info(f"Target: {args.url}")
    log.info(f"Agents: {', '.join(a.name for a in selected_agents)}")
    log.info(f"Speed: {args.interval_multiplier}x")
    if args.full:
        log.info(_color("Mode: FULL (complete connected graph)", "green"))
    elif args.once:
        log.info("Mode: ONCE (single batch per agent)")
    if args.app_name:
        log.info(f"App: {args.app_name}")
    log.info("")

    orchestrator = MockerOrchestrator(args.url, selected_agents, app_name=args.app_name, once=args.once, full=args.full)

    def signal_handler(sig, frame):
        orchestrator.stop()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    asyncio.run(orchestrator.run())


if __name__ == "__main__":
    main()
