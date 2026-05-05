#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DH_REPO="rectid/general"

# Tag name -> build context directory
declare -A BUILD_DIRS=(
  ["flask-app"]="flask_app"
  ["fastapi-app"]="fastapi_app"
  ["golang-app"]="golang_app"
  ["k8s-watcher"]="k8s-watcher"
  ["otel-watcher"]="otel-watcher"
)

echo "=== Building images ==="
for TAG in "${!BUILD_DIRS[@]}"; do
  echo "Building ${TAG}..."
  docker build -t "${DH_REPO}:${TAG}" "${PROJECT_DIR}/${BUILD_DIRS[$TAG]}"
done

echo "=== Pushing images to Docker Hub ==="
for TAG in "${!BUILD_DIRS[@]}"; do
  echo "Pushing ${TAG}..."
  docker push "${DH_REPO}:${TAG}"
done

echo "=== Done ==="
