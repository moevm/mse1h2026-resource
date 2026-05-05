"""k8s-watcher: collects K8s cluster state and pushes to mse1h2026-resource API."""
import json
import os
import time
import logging
from datetime import datetime, date

import requests
from kubernetes import client, config


class K8sEncoder(json.JSONEncoder):
    """JSON encoder that handles K8s API objects with datetime and other non-serializable types."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        try:
            return str(obj)
        except Exception:
            return None

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("k8s-watcher")

RESOURCE_API_URL = os.environ.get("RESOURCE_API_URL", "http://localhost:8000")
AGENT_NAME = os.environ.get("AGENT_NAME", "k8s-watcher")
WATCH_NAMESPACE = os.environ.get("WATCH_NAMESPACE", "monitoring-demo")
WATCH_INTERVAL = int(os.environ.get("WATCH_INTERVAL", "30"))
AGENT_TOKEN = os.environ.get("AGENT_TOKEN")


def verify_agent_token():
    """Verify that AGENT_TOKEN is valid by making a test push."""
    if not AGENT_TOKEN:
        log.error("No AGENT_TOKEN set. Register this agent in the UI and set AGENT_TOKEN env var.")
        return False
    try:
        resp = requests.post(
            f"{RESOURCE_API_URL}/api/v1/receiver/raw",
            data=json.dumps({"_health_check": True}),
            headers={"X-Agent-Token": AGENT_TOKEN, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 401:
            log.error("AGENT_TOKEN is invalid or revoked. Re-register agent in UI and update AGENT_TOKEN.")
            return False
        log.info("AGENT_TOKEN verified successfully")
        return True
    except Exception as e:
        log.warning(f"Could not verify AGENT_TOKEN (API may be starting up): {e}")
        return True  # assume ok, will fail later if not


def push_raw(data: dict):
    """Push raw data to mse1h2026-resource."""
    if not AGENT_TOKEN:
        log.error("No AGENT_TOKEN, cannot push data")
        return
    try:
        serialized = json.dumps(data, cls=K8sEncoder)
        resp = requests.post(
            f"{RESOURCE_API_URL}/api/v1/receiver/raw",
            data=serialized,
            headers={"X-Agent-Token": AGENT_TOKEN, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 401:
            log.error("AGENT_TOKEN rejected (401). Token may be revoked. Re-register agent in UI.")
            return
        resp.raise_for_status()
        result = resp.json()
        log.info(
            "Pushed raw payload: nodes=%s, edges=%s",
            result.get("nodes_created", 0),
            result.get("edges_created", 0),
        )
    except Exception as e:
        log.error(f"Failed to push raw payload: {e}")


def collect_and_push():
    """Collect K8s resources and push to resource API."""
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    # Nodes
    nodes = v1.list_node()
    for node in nodes.items:
        push_raw(node.to_dict())

    # Pods
    pods = v1.list_namespaced_pod(WATCH_NAMESPACE)
    for pod in pods.items:
        push_raw(pod.to_dict())

    # Deployments
    deployments = apps_v1.list_namespaced_deployment(WATCH_NAMESPACE)
    for dep in deployments.items:
        push_raw(dep.to_dict())

    # Services
    services = v1.list_namespaced_service(WATCH_NAMESPACE)
    for svc in services.items:
        push_raw(svc.to_dict())

    # ConfigMaps
    configmaps = v1.list_namespaced_config_map(WATCH_NAMESPACE)
    for cm in configmaps.items:
        push_raw(cm.to_dict())

    # Secrets (metadata only, no data values for security)
    secrets = v1.list_namespaced_secret(WATCH_NAMESPACE)
    for secret in secrets.items:
        safe_secret = secret.to_dict()
        # Clear actual secret data, keep metadata + type
        safe_secret["data"] = {}
        push_raw(safe_secret)

    # Endpoints
    endpoints_list = v1.list_namespaced_endpoints(WATCH_NAMESPACE)
    for ep in endpoints_list.items:
        push_raw(ep.to_dict())

    log.info(f"Collected: {len(nodes.items)} nodes, {len(pods.items)} pods, "
             f"{len(deployments.items)} deployments, {len(services.items)} services, "
             f"{len(configmaps.items)} configmaps, {len(secrets.items)} secrets, "
             f"{len(endpoints_list.items)} endpoints")


def main():
    log.info(f"Starting k8s-watcher (ns={WATCH_NAMESPACE}, interval={WATCH_INTERVAL}s)")
    if not AGENT_TOKEN:
        log.error("=" * 60)
        log.error("AGENT_TOKEN is not set!")
        log.error("1. Go to the Resource UI → Agents page")
        log.error("2. Register a new agent (name=%s, type=k8s-agent)", AGENT_NAME)
        log.error("3. Copy the returned token")
        log.error("4. Set AGENT_TOKEN=<copied-token> in environment")
        log.error("=" * 60)
        return
    log.info("Using AGENT_TOKEN=%s...%s", AGENT_TOKEN[:8], AGENT_TOKEN[-4:])
    verify_agent_token()
    while True:
        try:
            collect_and_push()
        except Exception as e:
            log.error(f"Collection cycle failed: {e}")
        time.sleep(WATCH_INTERVAL)


if __name__ == "__main__":
    main()
