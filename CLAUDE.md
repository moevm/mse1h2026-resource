# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Resource Graph Analyzer** — веб-приложение для построения графа ресурсов и зависимостей распределённых/SOA приложений. Система собирает данные о сервисах, базах данных, очередях, API и других ресурсах, строит ориентированный граф их взаимодействий и предоставляет визуализацию с экспортом в различные форматы.

### Domain Model

Проект использует собственную спецификацию данных для представления графа (см. `schemas/`). Универсального формата данных не существует, поэтому определена внутренняя модель:

**16 типов вершин (nodes):** Service, Endpoint, Deployment, Pod, Node, Database, Table, QueueTopic, Cache, ExternalAPI, SecretConfig, Library, TeamOwner, SLASLO, RegionCluster

**11 типов рёбер (edges):** calls, publishesto, consumesfrom, reads, writes, dependson, deployedon, ownedby, authenticatesvia, ratelimitedby, fails_over_to

**Планы развития:** В будущем планируется реализовать веб-интерфейс для маппинга — преобразования произвольных форматов данных от источников (OpenTelemetry, Istio, Kubernetes API, etc.) в внутреннюю модель.

### Data Mapper System

Реализована система маппинга произвольных форматов данных во внутреннюю модель:

**Поддерживаемые source types:** OpenTelemetry traces/metrics, Istio access logs/metrics, Kubernetes API, Prometheus, Terraform state

**Компоненты:**
- `app/models/mapper/` — модели для RawDataChunk, MappingConfig, FieldMapping
- `app/repositories/raw_data_repo.py` — хранение raw данных в Redis (TTL 24h)
- `app/repositories/mapping_repo.py` — CRUD для MappingConfig в Neo4j
- `app/services/transform_service.py` — JMESPath extraction и transforms
- `app/services/mapper_service.py` — core mapping orchestration
- `app/api/receiver.py` — endpoint для приёма raw данных
- `app/api/mapper_config.py` — CRUD для маппингов
- `app/api/mapper_preview.py` — preview и apply маппинга

## Commands

### Docker (recommended)
```bash
docker-compose up --build          # Запуск всех сервисов (neo4j, backend, frontend)
docker-compose up -d neo4j         # Запуск только Neo4j
docker-compose logs -f backend     # Логи бэкенда
docker-compose down -v             # Остановка с удалением volumes
```

### Backend (local development)
```bash
source .venv/bin/activate          # Активация venv
pip install -r requirements.txt    # Установка зависимостей
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend (local development)
```bash
cd frontend
npm install
npm run dev                         # Dev server на :5173
npm run build                       # Production build
```

### Testing with mock data
```bash
python -m mocker.run --url http://localhost:8000 --agent-name test-agent
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend   │────▶│    Neo4j    │
│  (React)    │     │  (FastAPI)  │     │  (Graph DB) │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
   ┌──────────┐     ┌──────────┐     ┌──────────┐
   │  Redis   │     │ JMESPath │     │  Agents  │
   │(Raw Data)│     │ Transform│     │(OTel,K8s)│
   └──────────┘     └──────────┘     └──────────┘
```

### Backend Structure (`app/`)
- `main.py` — FastAPI entry point, CORS, lifespan, routers
- `config.py` — Settings via pydantic-settings (Neo4j connection, TTL)
- `api/` — REST endpoints: agents, graph, ingest, export, traversal
- `models/` — Pydantic models for nodes, edges, topology, export formats
- `repositories/` — Neo4j connection, graph CRUD, agent storage
- `services/` — Business logic: graph queries, analytics (NetworkX), export

### Frontend Structure (`frontend/src/`)
- `components/pages/` — DashboardPage, GraphPage, AgentsPage
- `components/graph/` — GraphCanvas (Cytoscape), GraphControls, NodeDetail
- `store/` — Zustand stores: graphStore, logStore, uiStore
- `api/` — Axios client for backend API calls

### Data Flow
1. **Agents** регистрируются через `/api/v1/agents/register`, получают токен
2. **Ingest** — агенты отправляют топологию (nodes+edges) через `/api/v1/ingest/topology`
3. **Storage** — Neo4j хранит все узлы с label `Resource` + динамические labels по type
4. **Query** — API для full graph, subgraph, shortest path, impact analysis
5. **Export** — JSON, GraphML, GEXF, DOT, Cytoscape JSON, CSV

## Key Files

| File | Purpose |
|------|---------|
| `app/models/nodes.py` | Pydantic models для 16 типов вершин |
| `app/models/edges.py` | Pydantic models для 11 типов рёбер |
| `schemas/nodes/*.json` | JSON Schema спецификации для валидации |
| `schemas/edges/*.json` | JSON Schema спецификации для рёбер |
| `app/repositories/neo4j_repo.py` | Все Cypher-запросы для работы с графом |
| `app/services/graph_service.py` | Graph queries + NetworkX analytics (PageRank, betweenness) |
| `app/services/export_service.py` | Экспорт в GraphML/GEXF/DOT/Cytoscape/CSV |
| `mocker/generator.py` | Генератор mock-данных с сценариями (load spike, cascading failure) |

## API Endpoints (prefix `/api/v1/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/agents/register` | Регистрация агента, возвращает токен |
| GET | `/agents/` | Список зарегистрированных агентов |
| POST | `/ingest/topology` | Загрузка топологии (требует токен агента) |
| GET | `/graph/full` | Полный граф (limit до 5000) |
| POST | `/graph/subgraph` | Подграф от указанного узла (BFS) |
| POST | `/graph/path` | Кратчайший путь между узлами |
| POST | `/graph/impact` | Blast-radius анализ (downstream/upstream) |
| GET | `/graph/stats` | Статистика: count по типам узлов/рёбер |
| GET | `/graph/analytics` | PageRank, betweenness centrality, communities |
| GET | `/traversal/presets` | Preset правила обхода |
| POST | `/traversal/execute` | Выполнение правила обхода |
| POST | `/export/download` | Экспорт в указанном формате |
| GET | `/export/formats` | Список поддерживаемых форматов |
| POST | `/receiver/raw?source_type=...` | Принять raw данные от агента |
| GET | `/receiver/raw` | Список raw data chunks |
| GET/POST/PUT/DELETE | `/mapper` | CRUD для mapping конфигураций |
| POST | `/mapper/preview` | Preview маппинга без сохранения |
| POST | `/mapper/apply` | Применить mapping → Neo4j |

## Node Identification

Все узлы идентифицируются по `id` (URN format): `urn:{type}:{name}`
Пример: `urn:service:payment-api`, `urn:database:postgres-orders`

## Environment Variables

```bash
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=changeme
DEBUG=true
NODE_TTL_HOURS=24
REDIS_HOST=localhost
REDIS_PORT=6379
RAW_DATA_TTL_HOURS=24
```

## Ports

- `3000` — Frontend (Nginx)
- `8000` — Backend API
- `7474` — Neo4j Browser UI
- `7687` — Neo4j Bolt protocol
- `6379` — Redis
