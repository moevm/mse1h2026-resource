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

# Copy dashboards for ConfigMap creation
ssh "${SSH_OPTS[@]}" "$SERVER" "mkdir -p $REMOTE_DIR/dashboards"
scp "${SCP_OPTS[@]}" -r "${PROJECT_DIR}/etc/dashboards/"* "$SERVER:$REMOTE_DIR/dashboards/"

echo "=== Running kubectl on server node ==="
ssh "${SSH_OPTS[@]}" "$SERVER" bash -s <<'REMOTE_SCRIPT'
set -e
NS="monitoring-demo"
DIR="/tmp/k8s-manifests"

echo "=== Creating namespace ==="
kubectl apply -f "$DIR/00-namespace.yaml"

echo "=== Creating ConfigMaps ==="
kubectl apply -f "$DIR/01-configmaps/"

echo "=== Creating dashboard ConfigMap ==="
kubectl create configmap grafana-dashboards \
  --from-file="$DIR/dashboards/" \
  -n "$NS" --dry-run=client -o yaml | kubectl apply -f -

echo "=== Creating Secrets ==="
kubectl apply -f "$DIR/02-secrets/"

echo "=== Creating PVCs ==="
kubectl apply -f "$DIR/03-storage/"

echo "=== Installing local-path-provisioner ==="
kubectl apply -f https://raw.githubusercontent.com/rancher/local-path-provisioner/v0.0.28/deploy/local-path-storage.yaml
echo "Waiting for local-path-provisioner..."
kubectl rollout status deployment/local-path-provisioner -n local-path-storage --timeout=120s || true

echo "=== Installing MetalLB ==="
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.14.8/config/manifests/metallb-native.yaml
echo "Waiting for MetalLB controller..."
kubectl rollout status deployment/controller -n metallb-system --timeout=180s || true

echo "=== Configuring MetalLB IP pool ==="
kubectl apply -f "$DIR/08-metallb/" || true

echo ""
echo "=== Infrastructure ready. Now push images and deploy apps. ==="
echo "1. Push images:   ./k8s/build-and-load-images.sh"
echo "2. Deploy apps:   ./k8s/apply-apps.sh"
REMOTE_SCRIPT
