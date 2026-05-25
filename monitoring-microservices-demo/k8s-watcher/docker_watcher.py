"""k8s-watcher (Docker): collects K8s cluster state and pushes to mse1h2026-resource API.
Auto-registers as an agent on startup.
"""
import json
import os
import time
import logging
from datetime import datetime, date

import requests
from kubernetes import client, config


class K8sEncoder(json.JSONEncoder):
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
    if not AGENT_TOKEN:
        log.error("No AGENT_TOKEN set.")
        return False
    try:
        resp = requests.post(
            f"{RESOURCE_API_URL}/api/v1/receiver/raw",
            data=json.dumps({"_health_check": True}),
            headers={"X-Agent-Token": AGENT_TOKEN, "Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code == 401:
            log.error("AGENT_TOKEN is invalid or revoked.")
            return False
        log.info("AGENT_TOKEN verified successfully")
        return True
    except Exception as e:
        log.warning(f"Could not verify AGENT_TOKEN (API may be starting up): {e}")
        return True


def push_raw(data: dict):
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
            log.error("AGENT_TOKEN rejected (401).")
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
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()

    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    nodes = v1.list_node()
    for node in nodes.items:
        push_raw(node.to_dict())

    pods = v1.list_namespaced_pod(WATCH_NAMESPACE)
    for pod in pods.items:
        push_raw(pod.to_dict())

    deployments = apps_v1.list_namespaced_deployment(WATCH_NAMESPACE)
    for dep in deployments.items:
        push_raw(dep.to_dict())

    services = v1.list_namespaced_service(WATCH_NAMESPACE)
    for svc in services.items:
        push_raw(svc.to_dict())

    configmaps = v1.list_namespaced_config_map(WATCH_NAMESPACE)
    for cm in configmaps.items:
        push_raw(cm.to_dict())

    secrets = v1.list_namespaced_secret(WATCH_NAMESPACE)
    for secret in secrets.items:
        safe_secret = secret.to_dict()
        safe_secret["data"] = {}
        push_raw(safe_secret)

    endpoints_list = v1.list_namespaced_endpoints(WATCH_NAMESPACE)
    for ep in endpoints_list.items:
        push_raw(ep.to_dict())

    log.info(f"Collected: {len(nodes.items)} nodes, {len(pods.items)} pods, "
             f"{len(deployments.items)} deployments, {len(services.items)} services, "
             f"{len(configmaps.items)} configmaps, {len(secrets.items)} secrets, "
             f"{len(endpoints_list.items)} endpoints")


def main():
    global AGENT_TOKEN
    log.info(f"Starting k8s-watcher (ns={WATCH_NAMESPACE}, interval={WATCH_INTERVAL}s)")
    if not AGENT_TOKEN:
        from register import register_agent
        try:
            AGENT_TOKEN = register_agent(AGENT_NAME, "watcher-kubernetes-objects")
            log.info("Auto-registered agent, token: %s...%s", AGENT_TOKEN[:8], AGENT_TOKEN[-4:])
        except Exception as e:
            log.error("Auto-registration failed: %s", e)
            return
    else:
        log.info("Using pre-set AGENT_TOKEN=%s...%s", AGENT_TOKEN[:8], AGENT_TOKEN[-4:])

    verify_agent_token()
    while True:
        try:
            collect_and_push()
        except Exception as e:
            log.error(f"Collection cycle failed: {e}")
        time.sleep(WATCH_INTERVAL)


if __name__ == "__main__":
    main()
