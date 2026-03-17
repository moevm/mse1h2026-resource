# Resource Graph Analyzer

Анализатор ресурсов и зависимостей распределённых систем — веб-приложение, которое автоматически строит граф ресурсов и взаимодействий в распределённых/SOA приложениях (сервисы, базы данных, очереди, API, топики, узлы, деплойменты).

## Описание проекта

Система предназначена для визуализации и анализа зависимостей между компонентами микросервисной архитектуры. Она позволяет:

- Импортировать данные из источников телеметрии (OpenTelemetry, Kubernetes API, Prometheus, etc.)
- Строить ориентированный граф ресурсов с настраиваемыми правилами обхода
- Визуализировать зависимости в интерактивном веб-интерфейсе
- Экспортировать граф в различные форматы для внешних инструментов

## Модель данных

Проект использует собственную спецификацию данных для представления графа ресурсов. Спецификации определены в формате JSON Schema в директории `schemas/`.

### Типы вершин (16 типов)

| Тип | Описание |
|-----|----------|
| **Service** | Микросервис (язык, фреймворк, версия, RPS, latency) |
| **Endpoint** | API endpoint (путь, метод, лимиты, аутентификация) |
| **Deployment** | Kubernetes Deployment (реплики, стратегия, namespace) |
| **Pod** | Kubernetes Pod (фаза, node, ресурсы) |
| **Node** | Вычислительный узел (instance type, CPU, memory) |
| **Database** | База данных (движок, версия, подключения) |
| **Table** | Таблица БД (схема, строки, индексы) |
| **QueueTopic** | Очередь/топик сообщений (брокер, партиции, lag) |
| **Cache** | Кэш (Redis, hit rate, eviction policy) |
| **ExternalAPI** | Внешний API (провайдер, rate limits, SLA) |
| **SecretConfig** | Секреты/конфигурация (ротация, шифрование) |
| **Library** | Библиотека (версия, лицензия, CVE) |
| **TeamOwner** | Команда-владелец (email, Slack, on-call) |
| **SLASLO** | SLA/SLO определения (target, error budget) |
| **RegionCluster** | Регион/кластер (провайдер, зоны, K8s version) |

### Типы связей (11 типов)

| Связь | Описание |
|-------|----------|
| `calls` | Синхронные вызовы (HTTP, gRPC) |
| `publishesto` | Публикация в очередь/топик |
| `consumesfrom` | Потребление из очереди/топика |
| `reads` | Операции чтения БД |
| `writes` | Операции записи в БД |
| `dependson` | Зависимости между сервисами |
| `deployedon` | Размещение на инфраструктуре |
| `ownedby` | Принадлежность команде |
| `authenticatesvia` | Аутентификация |
| `ratelimitedby` | Rate limiting |
| `fails_over_to` | Failover отношения |

## Архитектура

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Frontend   │────▶│   Backend   │────▶│    Neo4j    │
│   (React)   │     │  (FastAPI)  │     │  (Graph DB) │
│ Cytoscape.js│     │  NetworkX   │     │    APOC     │
└─────────────┘     └─────────────┘     └─────────────┘
                           ▲
                           │
                    ┌──────┴──────┐
                    │   Agents    │
                    │ OTel, K8s   │
                    │ Prometheus  │
                    └─────────────┘
```

### Технологии

- **Backend**: Python 3.12, FastAPI, Pydantic, NetworkX
- **Frontend**: React 19, TypeScript, Tailwind CSS, Cytoscape.js, Zustand
- **Database**: Neo4j 5 Community (APOC plugin)
- **Containerization**: Docker, Docker Compose

## Установка и запуск

### Через Docker (рекомендуется)

```bash
# Клонирование репозитория
git clone <repository-url>
cd mse1h2026-resource

# Создание .env файла
cp .env.example .env

# Запуск всех сервисов
docker-compose up --build
```

После запуска доступны:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Neo4j Browser: http://localhost:7474

### Локальная разработка

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (в другом терминале)
cd frontend
npm install
npm run dev
```

### Загрузка тестовых данных

```bash
python -m mocker.run --url http://localhost:8000 --agent-name test-agent
```

## API Endpoints

| Method | Endpoint | Описание |
|--------|----------|----------|
| POST | `/api/v1/agents/register` | Регистрация агента сбора данных |
| POST | `/api/v1/ingest/topology` | Загрузка топологии |
| GET | `/api/v1/graph/full` | Получение полного графа |
| POST | `/api/v1/graph/subgraph` | Подграф от указанного узла |
| POST | `/api/v1/graph/path` | Кратчайший путь между узлами |
| POST | `/api/v1/graph/impact` | Анализ влияния (blast-radius) |
| GET | `/api/v1/graph/analytics` | PageRank, betweenness, communities |
| POST | `/api/v1/traversal/execute` | Обход по пользовательским правилам |
| POST | `/api/v1/export/download` | Экспорт графа |

### Поддерживаемые форматы экспорта

- **JSON** — нативный формат
- **GraphML** — для Gephi, yEd
- **GEXF** — для Gephi
- **DOT** — для Graphviz (SVG/PNG)
- **Cytoscape JSON** — для Cytoscape.js
- **CSV** — таблицы узлов и рёбер

## Примеры правил обхода

```
# Зависимости сервиса с downstream базами
Service → (calls)* → Service → (writes/reads) → Database

# Потребители топика и их зависимости
QueueTopic → (consumesfrom) → Service → (calls)* → downstream

# По критичности: сначала Payment команда
owned_by=Payments → all downstream resources
```

## Планы развития

### Маппер форматов данных (roadmap)

В будущем планируется реализовать веб-интерфейс для маппинга произвольных форматов данных во внутреннюю модель:

```
Входные форматы              Маппер              Внутренняя модель
─────────────────         ┌─────────┐          ┌─────────────────┐
OpenTelemetry traces  ───▶│         │──▶       │ Nodes (16 types)│
Kubernetes API        ───▶│  Web    │──▶       │ Edges (11 types)│
Istio telemetry       ───▶│  UI     │──▶       │                 │
Prometheus metrics    ───▶│ Mapper  │──▶       │ schemas/*.json  │
Terraform state       ───▶│         │──▶       │                 │
AWS/GCP/Azure APIs    ───▶│         │──▶       │                 │
                       ▲  └─────────┘          └─────────────────┘
                       │
              Ручное связывание
              полей форматов
```

Это позволит подключать любые источники телеметрии без изменения кода.

## Структура проекта

```
├── app/                    # Backend (FastAPI)
│   ├── api/               # REST endpoints
│   ├── models/            # Pydantic models
│   ├── repositories/      # Neo4j data access
│   └── services/          # Business logic
├── frontend/              # Frontend (React)
│   └── src/
│       ├── components/   # UI components
│       ├── store/        # Zustand stores
│       └── api/          # API client
├── schemas/               # JSON Schema спецификации
│   ├── nodes/            # Схемы вершин
│   └── edges/            # Схемы рёбер
├── mocker/                # Генератор тестовых данных
└── docker-compose.yml     # Docker Compose конфигурация
```

## Команда

Михайлова — Анализатор ресурсов и зависимостей распределённых систем (Магистерская работа, 2026)
