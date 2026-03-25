# Resource Graph Mocker

Мульти-агентный генератор данных для тестирования Data Mapper системы.

## Быстрый старт

```bash
# 1. Запустить backend
docker-compose up neo4j backend

# 2. Сгенерировать данные
python -m mocker.run --full --url http://localhost:8000

# 3. Создать маппинги (один раз)
python -m mocker.create_mappings --url http://localhost:8000

# 4. Проверить граф
curl -s "http://localhost:8000/api/v1/graph/stats" | jq
```

## Создание маппингов

Маппинги преобразуют raw данные в узлы и рёбра графа. Создаются один раз:

```bash
# Создать все маппинги
python -m mocker.create_mappings --url http://localhost:8000

# Dry-run (показать что будет создано)
python -m mocker.create_mappings --dry-run -v

# Только для конкретного source type
python -m mocker.create_mappings --source-type kubernetes-api

# Не активировать после создания
python -m mocker.create_mappings --no-activate
```

**Доступные source types:** `kubernetes-api`, `opentelemetry-traces`, `opentelemetry-metrics`, `istio-access-logs`, `istio-metrics`, `prometheus`, `terraform-state`, `argocd`, `api-gateway`

## Генерация данных

### Непрерывная генерация (run.py)

```bash
# Запустить все агенты
python -m mocker.run --url http://localhost:8000

# Отправить один batch и выйти (полезно для тестирования)
python -m mocker.run --once --url http://localhost:8000

# Запустить конкретные агенты
python -m mocker.run --agents k8s,otel,prometheus --url http://localhost:8000

# Ускорить отправку (для быстрого тестирования)
python -m mocker.run --interval-multiplier 0.1 --url http://localhost:8000

# Список доступных агентов
python -m mocker.run --list
```

### Генерация данных в файлы (run_generator.py)

```bash
# Сгенерировать данные в mocker/data/
python -m mocker.run_generator --count 100

# Указать выходную директорию
python -m mocker.run_generator --count 50 --output ./output

# Только конкретные source types
python -m mocker.run_generator --count 100 --source-types kubernetes-api,prometheus
```

Данные сохраняются в JSON файлах по структуре:
```
mocker/data/
├── kubernetes-api/
│   ├── pod_001.json
│   ├── node_001.json
│   └── ...
├── opentelemetry-traces/
│   └── trace_001.json
└── ...
```

## Доступные агенты

| Агент | Source Type | Описание |
|-------|-------------|----------|
| `k8s-api-watcher` | `kubernetes-api` | Pods, Deployments, Services, Nodes |
| `otel-collector` | `opentelemetry-traces` | Traces с Library, ExternalAPI, Table атрибутами |
| `otel-metrics` | `opentelemetry-metrics` | Метрики сервисов |
| `istio-proxy-logs` | `istio-access-logs` | Access logs с ExternalAPI inference |
| `istio-metrics` | `istio-metrics` | Istio/Prometheus метрики mesh |
| `prometheus-scrape` | `prometheus` | Метрики + SLO метрики |
| `terraform-state` | `terraform-state` | Database, Cache, Queue, SecretConfig |
| `argocd-sync` | `argocd` | Application manifests с team labels |
| `api-gateway-routes` | `api-gateway` | Ingress routes и endpoints |

## Соответствие типов узлов и источников

| Тип узла | Источник | Атрибуты для маппинга |
|----------|----------|----------------------|
| **Service** | OTel traces, Istio logs, K8s API | `service.name`, `workload` |
| **TeamOwner** | K8s Deployment, ArgoCD | `annotations.team`, `labels.team` |
| **Library** | OpenTelemetry traces | `telemetry.sdk.language`, `telemetry.sdk.name` |
| **SLASLO** | Prometheus | `type == 'slo-metric'` |
| **SecretConfig** | Terraform state | `type == 'aws_secretsmanager_secret'` |
| **ExternalAPI** | Istio logs, OTel traces | `is_external_call == true`, `external_api` |
| **Table** | OpenTelemetry traces | `db.table` |
| **Database** | Terraform state, OTel traces | `type == 'aws_db_instance'`, `db.name` |
| **Cache** | Terraform state | `type == 'aws_elasticache_cluster'` |
| **QueueTopic** | Terraform state | `type == 'aws_msk_topic'` |

## Presets

После генерации данных импортируйте соответствующие presets:

```bash
# Импортировать все unified presets
for preset in kubernetes-unified opentelemetry-traces-unified istio-access-logs-unified prometheus-slo terraform-state-unified argocd-unified; do
  curl -X POST "http://localhost:8000/api/v1/presets/$preset/import"
done
```

## Пример workflow

```bash
# 1. Запустить backend
docker-compose up neo4j backend

# 2. Создать маппинги (один раз)
python -m mocker.create_mappings --url http://localhost:8000

# 3. Сгенерировать данные
python -m mocker.run --once --url http://localhost:8000

# 4. Проверить граф
curl -s "http://localhost:8000/api/v1/graph/stats" | jq
curl -s "http://localhost:8000/api/v1/graph/full?limit=50" | jq
```

### Альтернативно: генерация в файлы

```bash
# 1. Сгенерировать данные в файлы
python -m mocker.run_generator --count 100

# 2. Отправить через API
for file in mocker/data/kubernetes-api/*.json; do
  curl -X POST "http://localhost:8000/api/v1/receiver/raw?source_type=kubernetes-api" \
    -H "Content-Type: application/json" \
    -d @"$file"
done
```

## Архитектура

```
mocker/
├── run.py              # CLI для непрерывной генерации данных
├── run_generator.py    # CLI для генерации данных в файлы
├── create_mappings.py  # Скрипт создания маппингов
├── raw_generator.py    # Генераторы raw данных для каждого source type
├── shared_state.py     # Консистентное состояние (services, nodes, pods, etc.)
├── mappings/           # Определения маппингов
│   ├── __init__.py
│   ├── kubernetes_api.py
│   ├── opentelemetry_traces.py
│   ├── opentelemetry_metrics.py
│   ├── istio_access_logs.py
│   ├── istio_metrics.py
│   ├── prometheus.py
│   ├── terraform_state.py
│   ├── argocd.py
│   └── api_gateway.py
├── data/               # Сгенерированные данные (от run_generator.py)
└── generator.py        # Старый генератор топологии (deprecated)
```

**SharedState** обеспечивает консистентность — все агенты используют одни и те же сервисы, базы данных, очереди и т.д. Это гарантирует, что не будет dangling references в графе.

**Mappings** определяют как raw данные преобразуются в узлы и рёбра графа. Каждый маппинг содержит:
- `field_mappings` — правила извлечения полей через JMESPath
- `conditional_rules` — условия для определения типа узла
- `edge_preset_id` — preset для автоматического создания рёбер
