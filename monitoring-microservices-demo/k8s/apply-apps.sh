#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Use SSH config from k8s environment
SSH_CONFIG="$HOME/envs/k8s/ssh/ssh.config"
SSH_KEY="$HOME/envs/k8s/ssh/id_rsa"
SERVER="vpa-k8s-server-1.l.postgrespro.ru"
SSH_OPTS=(-o "StrictHostKeyChecking=no" -i "$SSH_KEY" -F "$SSH_CONFIG")
SCP_OPTS=(-o "StrictHostKeyChecking=no" -i "$SSH_KEY" -F "$SSH_CONFIG")
REMOTE_DIR="/tmp/k8s-manifests"

echo "=== Copying manifests to server node ==="
ssh "${SSH_OPTS[@]}" "$SERVER" "rm -rf $REMOTE_DIR && mkdir -p $REMOTE_DIR"
scp "${SCP_OPTS[@]}" -r "${SCRIPT_DIR}/"* "$SERVER:$REMOTE_DIR/"

echo "=== Deploying apps and observability stack ==="
ssh "${SSH_OPTS[@]}" "$SERVER" bash -s <<'REMOTE_SCRIPT'
set -e
NS="monitoring-demo"
DIR="/tmp/k8s-manifests"

echo "=== Creating Docker Hub secret ==="
if ! kubectl get secret dockerhub-secret -n "$NS" &>/dev/null; then
  echo "WARNING: dockerhub-secret not found. Create it first:"
  echo "  kubectl create secret docker-registry dockerhub-secret \\"
  echo "    --docker-server=docker.io \\"
  echo "    --docker-username=rectid \\"
  echo "    --docker-password=<TOKEN> \\"
  echo "    -n monitoring-demo"
  exit 1
fi

echo "=== Deploying database ==="
kubectl apply -f "$DIR/04-database/"
kubectl rollout status deployment/postgres-db -n "$NS" --timeout=120s

echo "=== Deploying app services ==="
kubectl apply -f "$DIR/05-app-services/"
kubectl rollout status deployment/fastapi-app -n "$NS" --timeout=120s
kubectl rollout status deployment/flask-app -n "$NS" --timeout=120s
kubectl rollout status deployment/golang-app -n "$NS" --timeout=120s

echo "=== Deploying observability stack ==="
kubectl apply -f "$DIR/06-observability/"

echo "=== Deploying Beyla DaemonSet ==="
kubectl apply -f "$DIR/07-daemonsets/"

echo "=== Deploying k8s-watcher ==="
if [ -d "$DIR/09-k8s-watcher" ]; then
  kubectl apply -f "$DIR/09-k8s-watcher/"
fi

echo "=== Deploying otel-watcher ==="
if [ -d "$DIR/10-otel-watcher" ]; then
  kubectl apply -f "$DIR/10-otel-watcher/"
fi

echo ""
echo "=== Deployment complete ==="
echo ""
echo "Check status:"
echo "  kubectl get all -n ${NS}"
echo "  kubectl get pvc -n ${NS}"
echo "  kubectl get svc -n ${NS}"
REMOTE_SCRIPT
