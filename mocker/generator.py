from __future__ import annotations

import copy
import math
import random
from datetime import datetime, timezone
from typing import Any

from mocker.topology import STATIC_NODES, STATIC_EDGES, U


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _wave(base: float, amplitude: float, t: int,
          noise_frac: float = 0.05, period: float = 20.0) -> float:
    val = base + amplitude * math.sin(2 * math.pi * t / period)
    val += random.gauss(0, base * noise_frac)
    return round(max(0.0, val), 2)


def _int_vary(base: int, spread: int) -> int:
    return max(0, base + random.randint(-spread, spread))


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


SERVICE_PROFILES: dict[str, tuple[float, float, float, float, int]] = {
    U["api-gateway"]:           (2500.0, 35.0,  0.02,  0.80, 400),
    U["auth-service"]:          ( 800.0, 25.0,  0.05,  0.30, 180),
    U["user-service"]:          ( 600.0, 45.0,  0.03,  0.40, 350),
    U["cart-service"]:          ( 900.0, 30.0,  0.04,  0.20, 200),
    U["order-service"]:         ( 400.0, 120.0, 0.10,  0.70, 700),
    U["payment-service"]:       ( 200.0, 250.0, 0.08,  0.50, 500),
    U["notification-service"]:  ( 150.0, 60.0,  0.02,  0.15, 180),
    U["product-service"]:       (1200.0, 20.0,  0.01,  0.35, 350),
    U["inventory-service"]:     ( 300.0, 40.0,  0.03,  0.30, 200),
    U["search-service"]:        (1800.0, 15.0,  0.01,  0.40, 400),
    U["recommendation-service"]:( 100.0, 80.0,  0.05,  0.60, 700),
}
_DEFAULT_PROFILE = (100.0, 50.0, 0.1, 0.3, 256)


class _Scenarios:
    @staticmethod
    def is_load_spike(t: int) -> bool:
        return (t % 60) in range(0, 6)

    @staticmethod
    def is_cascading_failure(t: int) -> tuple[bool, int]:
        phase = t % 90
        if 0 <= phase < 10:
            return True, phase
        return False, -1

    @staticmethod
    def is_cache_stampede(t: int) -> bool:
        return (t % 120) in range(0, 5)

    @staticmethod
    def is_deployment_rollout(t: int) -> tuple[bool, str]:
        if (t % 80) in range(0, 8):
            return True, U["search-service"]
        return False, ""


S = _Scenarios


def _generate_nodes(t: int) -> list[dict[str, Any]]:
    spike = S.is_load_spike(t)
    cascading, c_phase = S.is_cascading_failure(t)
    stampede = S.is_cache_stampede(t)
    rolling, rolling_svc = S.is_deployment_rollout(t)
    nodes: list[dict[str, Any]] = []

    for base in STATIC_NODES:
        n = copy.deepcopy(base)

        match n["type"]:
            case "Service":
                prof = SERVICE_PROFILES.get(n["id"], _DEFAULT_PROFILE)
                rps_base, lat_base, err_base, cpu_base, mem_base = prof

                # Determine status
                status = "active"
                if cascading and n["id"] == U["payment-service"] and c_phase < 7:
                    status = "degraded"
                elif cascading and n["id"] == U["order-service"] and 4 <= c_phase < 9:
                    status = "degraded"
                elif rolling and n["id"] == rolling_svc:
                    status = "updating"

                n["status"] = status
                spike_mult = 3.5 if spike else 1.0
                degraded_mult = 1.8 if status == "degraded" else 1.0

                n["rps"] = round(_wave(rps_base * spike_mult, rps_base * 0.15, t, period=25), 1)
                n["latency_p99_ms"] = round(
                    _wave(lat_base * degraded_mult, lat_base * 0.2, t, period=18), 1
                )
                n["error_rate_percent"] = round(
                    _clamp(
                        _wave(err_base * (12.0 if status == "degraded" else 1.0), 0.02, t, noise_frac=0.3),
                        0.0, 100.0
                    ), 3
                )
                n["cpu_allocated_cores"] = round(_wave(cpu_base * degraded_mult, 0.1, t), 3)
                n["memory_allocated_mb"] = _int_vary(int(mem_base * degraded_mult), 32)
                n["active_connections"] = _int_vary(int(rps_base * spike_mult * 0.05), 10)

            case "Deployment":
                desired = 2
                if spike:
                    desired = 4
                elif rolling and n["name"] == rolling_svc.split(":")[-1]:
                    desired = 3

                ready = desired
                if cascading and "payment" in n["name"] and c_phase < 5:
                    ready = random.randint(0, 1)
                elif rolling and n["name"] == rolling_svc.split(":")[-1]:
                    ready = max(1, desired - 1)

                n["replicas_desired"] = desired
                n["replicas_ready"] = ready
                n["replicas_available"] = ready
                n["replicas_unavailable"] = max(0, desired - ready)

            case "Pod":
                # Determine pod health based on its service
                is_payment_pod = "payment" in n["id"]
                is_search_pod = "search" in n["id"]

                n["phase"] = "Running"
                cpu_base_m = 200 if spike else 80
                n["cpu_usage_m"] = _int_vary(cpu_base_m, 40)
                n["memory_usage_mi"] = _int_vary(300, 50)
                n["restart_count"] = 0

                if cascading and is_payment_pod and c_phase < 5:
                    n["phase"] = "CrashLoopBackOff" if c_phase < 3 else "Running"
                    n["restart_count"] = random.randint(2, 8)
                    n["cpu_usage_m"] = _int_vary(50, 20)
                elif rolling and is_search_pod:
                    if random.random() < 0.3:
                        n["phase"] = "ContainerCreating"
                        n["cpu_usage_m"] = 0
                        n["memory_usage_mi"] = 0

            case "Node":
                # Worker node utilization
                base_cpu_pct = 45.0 if spike else 25.0
                n["cpu_usage_percent"] = round(_wave(base_cpu_pct, 10, t), 1)
                n["memory_usage_percent"] = round(_wave(55, 8, t, period=30), 1)
                n["disk_pressure"] = False
                n["network_unavailable"] = False
                n["status"] = "active"

            case "QueueTopic":
                base_rate = 500 if spike else 150
                # Kafka queues back up during cascading failure
                if cascading and "order" in n["id"] and c_phase >= 4:
                    base_rate *= 0.3  # consumers are slow/dead
                n["message_rate"] = round(_wave(base_rate, 80, t, period=15), 1)
                n["consumer_lag"] = _int_vary(
                    5000 if (cascading and "order" in n["id"]) else 200, 100
                )
                n["bytes_per_second"] = _int_vary(base_rate * 1024, 5000)

            case "Cache":
                # Cache stampede drops hit rate for product cache
                hit_base = 95.0
                if stampede and "product" in n["id"]:
                    hit_base = 40.0  # mass eviction
                elif stampede and "search" in n["id"]:
                    hit_base = 60.0  # correlated miss

                n["hit_rate"] = round(_wave(hit_base, 3, t, noise_frac=0.01), 1)
                n["keys_count"] = _int_vary(50000, 5000)
                n["connected_clients"] = _int_vary(30 if not spike else 80, 5)
                n["memory_usage_mb"] = _int_vary(
                    int(n.get("max_memory_mb", 2048) * 0.65), 100
                )
                n["evictions_per_sec"] = _int_vary(5 if not stampede else 2000, 2)

            case "Database":
                conn_base = 40 if not spike else 120
                if stampede and "products" in n["id"]:
                    conn_base = 180  # cache miss  DB storm
                n["active_connections"] = _int_vary(conn_base, 10)
                n["queries_per_second"] = round(_wave(conn_base * 3, 20, t), 1)
                n["replication_lag_ms"] = round(_wave(2, 1, t, noise_frac=0.2), 1)
                n["disk_usage_percent"] = round(_wave(45, 5, t, period=50), 1)

            case "Table":
                n["rows_inserted_per_min"] = _int_vary(200 if spike else 50, 20)
                n["rows_updated_per_min"] = _int_vary(80 if spike else 20, 10)
                n["avg_query_time_ms"] = round(_wave(2, 0.5, t), 2)
                n["dead_tuples_pct"] = round(_wave(0.5, 0.2, t, period=50), 2)

            case "Endpoint":
                rps_mult = 3.5 if spike else 1.0
                n["current_rps"] = round(
                    _wave(n.get("rps_limit", 500) * 0.3 * rps_mult, 20, t), 1
                )
                n["latency_p50_ms"] = round(_wave(15, 5, t), 1)
                n["latency_p99_ms"] = round(_wave(80, 20, t), 1)
                n["error_count_1h"] = _int_vary(5 if not spike else 30, 3)

            case "ExternalAPI":
                n["response_time_ms"] = round(_wave(120, 30, t), 1)
                n["availability_percent"] = round(_wave(99.98, 0.01, t, noise_frac=0.001), 4)
                n["rate_limit_remaining"] = _int_vary(4500, 200)

            case "SecretConfig":
                n["last_rotated_days_ago"] = random.randint(1, n.get("rotation_interval_days", 30))
                n["access_count_1h"] = _int_vary(50, 10)

            case "Library":
                n["is_latest"] = random.random() > 0.2
                n["vulnerabilities_found"] = n.get("cve_count", 0)

            case "TeamOwner":
                n["active_incidents"] = 1 if (cascading and n["id"] == U["team-payments"]) else 0
                n["services_owned_count"] = sum(
                    1 for e in STATIC_EDGES
                    if e["type"] == "ownedby" and e["target_id"] == n["id"]
                )

            case "SLASLO":
                if n["metric_name"] == "availability":
                    base_val = 99.97
                    if cascading and "payment" in n["id"]:
                        base_val = 99.80  # SLO at risk
                    n["current_value"] = round(_wave(base_val, 0.02, t, noise_frac=0.001), 4)
                elif n["metric_name"] == "latency_p99":
                    base_val = 95.0 if not spike else 180.0
                    if cascading and ("payment" in n["id"] or "order" in n["id"]):
                        base_val *= 3.0
                    n["current_value"] = round(_wave(base_val, 30, t), 1)

                target = n.get("target_percentage", 0)
                metric = n["metric_name"]
                val = n.get("current_value", 0)
                if metric == "availability":
                    n["violation_count"] = 0 if val >= target else 1
                    n["error_budget_remaining_pct"] = round(
                        max(0, (val - (100 - (100 - target))) / (100 - target) * 100), 2
                    )
                else:
                    n["violation_count"] = 0 if val <= target else 1

            case "RegionCluster":
                n["node_count"] = 5
                n["pods_running"] = _int_vary(18, 2)
                n["pods_pending"] = 1 if rolling else 0
                n["cluster_cpu_usage_pct"] = round(_wave(35 if not spike else 65, 8, t), 1)
                n["cluster_memory_usage_pct"] = round(_wave(50, 6, t, period=30), 1)

        nodes.append(n)

    return nodes


_EDGE_BASES: dict[tuple, dict[str, float]] = {}


def _get_edge_base(src: str, tgt: str, etype: str) -> dict[str, float]:
    key = (src, tgt, etype)
    if key not in _EDGE_BASES:
        _EDGE_BASES[key] = {
            "rps": random.uniform(10, 400),
            "latency": random.uniform(5, 80),
            "error": random.uniform(0.01, 0.3),
        }
    return _EDGE_BASES[key]


def _generate_edges(t: int) -> list[dict[str, Any]]:
    spike = S.is_load_spike(t)
    cascading, c_phase = S.is_cascading_failure(t)
    stampede = S.is_cache_stampede(t)
    rolling, rolling_svc = S.is_deployment_rollout(t)
    edges: list[dict[str, Any]] = []

    for base in STATIC_EDGES:
        e = copy.deepcopy(base)
        src, tgt, etype = e["source_id"], e["target_id"], e["type"]
        eb = _get_edge_base(src, tgt, etype)

        # Determine if this edge is affected by cascading failure
        is_cascading_edge = cascading and (
            src == U["payment-service"] or tgt == U["payment-service"]
            or (c_phase >= 4 and (src == U["order-service"] or tgt == U["order-service"]))
        )
        is_stampede_edge = stampede and (
            "product" in src or "product" in tgt or "search" in src
        )

        spike_mult = 3.5 if spike else 1.0
        degrade_lat_mult = 5.0 if is_cascading_edge else (2.0 if is_stampede_edge else 1.0)
        degrade_err_mult = 15.0 if is_cascading_edge else (3.0 if is_stampede_edge else 1.0)

        match etype:
            case "calls":
                e["protocol"] = "grpc" if "gateway" in src else "http"
                e["rps"] = round(_wave(eb["rps"] * spike_mult, eb["rps"] * 0.2, t), 1)
                e["latency_p50_ms"] = round(
                    _wave(eb["latency"] * 0.4 * degrade_lat_mult, 5, t), 1
                )
                e["latency_p99_ms"] = round(
                    _wave(eb["latency"] * degrade_lat_mult, eb["latency"] * 0.3, t), 1
                )
                e["error_rate_percent"] = round(
                    _clamp(
                        _wave(eb["error"] * degrade_err_mult, 0.05, t, noise_frac=0.2),
                        0.0, 100.0
                    ), 3
                )
                e["timeout_ms"] = 5000
                e["circuit_breaker_enabled"] = True
                e["circuit_breaker_state"] = "open" if (is_cascading_edge and c_phase < 5) else "closed"
                e["retry_count"] = 3
                e["request_content_type"] = "application/json"

            case "publishesto":
                e["messages_per_second"] = round(
                    _wave(80 * spike_mult, 20, t), 1
                )
                e["message_size_bytes"] = _int_vary(1024, 256)
                e["batch_size"] = 100 if spike else 50
                e["compression"] = "snappy"
                e["partition_key"] = "order_id"
                e["ack_mode"] = "all"

            case "consumesfrom":
                e["consumer_group"] = f"{src.split(':')[-1]}-cg"
                base_lag = 50
                if is_cascading_edge:
                    base_lag = 15000  # massive backlog
                elif spike:
                    base_lag = 500
                e["lag_messages"] = _int_vary(base_lag, int(base_lag * 0.2))
                e["processing_time_ms"] = round(
                    _wave(12 * degrade_lat_mult, 5, t), 1
                )
                e["concurrent_consumers"] = 4 if spike else 2
                e["messages_per_second"] = round(_wave(40 * spike_mult, 10, t), 1)

            case "reads":
                lat_mult = degrade_lat_mult
                if stampede and "product" in tgt:
                    lat_mult = 8.0  # cache miss storm hits DB
                e["query_type"] = "select"
                e["latency_ms"] = round(_wave(eb["latency"] * 0.3 * lat_mult, 2, t), 2)
                e["queries_per_second"] = round(_wave(eb["rps"] * spike_mult * 0.5, 10, t), 1)
                e["index_used"] = True
                e["rows_examined"] = _int_vary(50, 20)
                e["rows_returned"] = _int_vary(10, 5)
                e["cache_hit_ratio"] = round(
                    _wave(0.85 if not stampede else 0.20, 0.05, t, noise_frac=0.02), 3
                )

            case "writes":
                e["query_type"] = "upsert"
                e["latency_ms"] = round(_wave(eb["latency"] * 0.5 * degrade_lat_mult, 3, t), 2)
                e["writes_per_second"] = round(_wave(eb["rps"] * spike_mult * 0.2, 5, t), 1)
                e["bytes_written"] = _int_vary(2048, 512)
                e["is_upsert"] = True
                e["transaction_isolation"] = "read_committed"

            case "dependson":
                is_hard = src in (U["order-service"], U["api-gateway"], U["cart-service"])
                e["criticality"] = "hard" if is_hard else "soft"
                e["fallback_available"] = not is_cascading_edge
                e["circuit_breaker_state"] = "open" if is_cascading_edge else "closed"
                e["health_check_status"] = "unhealthy" if is_cascading_edge else "healthy"
                e["impact_score"] = round(9.0 if is_cascading_edge else _wave(5, 1.5, t), 1)

            case "deployedon":
                e["isolation_level"] = "container"
                e["resource_requests_cpu_m"] = 250
                e["resource_requests_mem_mb"] = 256
                e["resource_limits_cpu_m"] = 1000
                e["resource_limits_mem_mb"] = 512

            case "ownedby":
                e["ownership_type"] = "primary"
                e["escalation_level"] = 1

            case "authenticatesvia":
                is_jwt = "jwt" in tgt
                e["auth_method"] = "jwt_rs256" if is_jwt else "api_key"
                e["token_expiry_seconds"] = 3600 if is_jwt else 0
                e["last_rotated_days_ago"] = random.randint(1, 60)
                e["mfa_required"] = False

            case "ratelimitedby":
                e["algorithm"] = "sliding_window"
                e["window_seconds"] = 60
                e["max_requests"] = 1000
                e["current_usage_pct"] = round(
                    _wave(40 * (3.0 if spike else 1.0), 10, t), 1
                )
                e["throttled_count_1h"] = _int_vary(5 if spike else 0, 3)

            case "fails_over_to":
                e["trigger_condition"] = "5xx_rate > 10%"
                e["is_active_active"] = False
                e["failover_time_seconds"] = _int_vary(30, 5)
                e["last_tested_days_ago"] = random.randint(1, 30)

        edges.append(e)

    return edges


#  Public API 

def generate_update(t: int) -> dict[str, Any]:
    return {
        "source": "mock-generator",
        "timestamp": _now(),
        "nodes": _generate_nodes(t),
        "edges": _generate_edges(t),
    }