SHELL := /usr/bin/env bash

MSE_COMPOSE := docker-compose.yml
MONITORING_COMPOSE := monitoring-microservices-demo/docker-compose.yaml
BACKEND_CONTAINER := resource-backend
BACKEND_WAIT_SECONDS ?= 120

.PHONY: up down build build-up

up:
	@echo "Starting MSE stack..."
	@docker compose -f $(MSE_COMPOSE) up -d
	@echo "Waiting for $(BACKEND_CONTAINER)..."
	@elapsed=0; \
	status=""; \
	while (( elapsed < $(BACKEND_WAIT_SECONDS) )); do \
		if status="$$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' $(BACKEND_CONTAINER) 2>/dev/null)"; then \
			if [[ "$$status" == "healthy" ]]; then \
				break; \
			fi; \
		fi; \
		sleep 2; \
		elapsed=$$((elapsed + 2)); \
	done; \
	if [[ "$$status" != "healthy" ]]; then \
		echo "Timed out waiting for $(BACKEND_CONTAINER). Last status: $${status:-missing}" >&2; \
		exit 1; \
	fi
	@echo "Starting monitoring-demo stack..."
	@docker compose -f $(MONITORING_COMPOSE) up -d
	@echo "All stacks are up."

down:
	@echo "Stopping monitoring-demo stack..."
	@docker compose -f $(MONITORING_COMPOSE) down -v
	@echo "Stopping MSE stack..."
	@docker compose -f $(MSE_COMPOSE) down -v

build:
	@echo "Building MSE stack..."
	@docker compose -f $(MSE_COMPOSE) build
	@echo "Building monitoring-demo stack..."
	@docker compose -f $(MONITORING_COMPOSE) build

build-up: build up
