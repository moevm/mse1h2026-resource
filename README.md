# MSE Анализатор ресурсов и зависимостей распределенных систем  

## Быстрый старт


```bash
# Клонирование репозитория
git clone https://github.com/moevm/mse1h2026-resource
cd mse1h2026-resource

# Создание .env файла
cp .env.example .env

# 1. # Запуск всех сервисов
docker compose up --build
```
При первом старте backend автоматически создаёт тестового пользователя:

- email: `admin@example.com`
- username: `admin`
- password: `admin`

Только для этого пользователя при старте автоматически накатываются тестовые данные и дефолтные маппинги:

- `python -m mocker.run --full --url http://localhost:8000 --auth-token <admin-token>` — создаёт связанный тестовый граф;
- `python -m mocker.create_mappings --url http://localhost:8000 --auth-token <admin-token>` — создаёт и активирует стандартные mapping-конфигурации.

Для остальных пользователей тестовые данные и маппинги автоматически не создаются. Если нужно повторить генерацию вручную, это можно сделать в UI во вкладке mapper.

- Кнопка `Generate mock data` запускает команду:
	`python -m mocker.run --full --url http://localhost:8000`
- Кнопка `Create default mappings` запускает команду:
	`python -m mocker.create_mappings --url http://localhost:8000`

```bash
#Заходим в контейнер бэкенда и все команды генерации выполняем внутри
docker exec -it resource-backend sh

# 2. Сгенерировать данные
python -m mocker.run --full --url http://localhost:8000

# 3. Создать маппинги (один раз)
python -m mocker.create_mappings --url http://localhost:8000

```

После запуска доступны:

Frontend: http://localhost:3000

Backend API: http://localhost:8000

API Documentation: http://localhost:8000/docs

## Создание маппингов

Маппинг — это конфигурация преобразования сырых данных от агентов в доменную модель графа. Агенты присылают payload'ы в разных форматах: Kubernetes API, OpenTelemetry traces/metrics, Istio logs, Prometheus, Terraform state и т.д. Без маппинга backend сохраняет такой payload как raw chunk, но не знает, какие поля считать сервисом, подом, базой данных, ребром `calls`, `reads`, `deployedon` и т.п.

Маппинги нужны, чтобы:

- извлекать из raw payload'ов узлы графа (`Service`, `Pod`, `Database`, `Endpoint`, `Table` и другие типы);
- создавать связи между узлами по правилам (`calls`, `reads`, `writes`, `deployedon`, `ownedby`, `dependson` и т.д.);
- автоматически применять активный mapping к новым raw chunks от агентов;
- переигрывать исторические raw chunks после изменения mapping-конфигурации;
- настраивать разные правила преобразования для разных `source_type`.

При старте проекта дефолтные маппинги автоматически создаются только для пользователя `admin@example.com` / `admin`. Для ручного создания или пересоздания можно выполнить:

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

## Все API endpoints

Базовый префикс API: `/api/v1`

### Health

- `GET /health` — проверка состояния backend.

### Agents (`/api/v1/agents`)

- `POST /register` — регистрация агента.
- `GET /` — список зарегистрированных агентов.

### Applications (`/api/v1/apps`)

- `POST /register` — регистрация приложения.
- `GET /` — список приложений.
- `GET /{app_id}` — детали приложения и связанные агенты.

### Ingest (`/api/v1/ingest`)

- `POST /topology` — приём пакета топологии (nodes/edges).

### Graph (`/api/v1/graph`)

- `GET /full` — полный граф (с лимитом).
- `POST /subgraph` — подграф от узла по глубине.
- `POST /path` — кратчайший путь между узлами.
- `POST /impact` — impact/blast-radius анализ.
- `GET /stats` — агрегированная статистика графа.
- `GET /analytics` — аналитика (PageRank, communities и т.д.).
- `GET /layout` — граф с предрасчитанными координатами.

### Export (`/api/v1/export`)

- `POST /download` — экспорт графа в выбранный формат.
- `GET /formats` — список доступных форматов экспорта.

### Traversal (`/api/v1/traversal`)

- `GET /presets` — список предустановленных traversal-правил.
- `POST /execute` — выполнение traversal-правила.

### Receiver (`/api/v1/receiver`)

- `POST /raw` — приём raw telemetry данных.
- `GET /raw` — список сохранённых raw чанков.
- `GET /raw/{chunk_id}` — получить конкретный raw chunk.
- `DELETE /raw/{chunk_id}` — удалить raw chunk.

### Mapper (`/api/v1/mapper`)

- `POST /` — создать mapping-конфигурацию.
- `GET /` — список mapping-конфигураций.
- `POST /recreate-edges` — пересоздать рёбра по auto-edge rules.
- `GET /active/{source_type}` — получить активный mapping для source type.
- `GET /{mapping_id}` — получить mapping по id.
- `PUT /{mapping_id}` — обновить mapping.
- `DELETE /{mapping_id}` — удалить mapping.
- `POST /{mapping_id}/activate` — активировать mapping.
- `POST /{mapping_id}/deactivate` — деактивировать mapping.
- `POST /{mapping_id}/deactivate-and-clear` — деактивировать mapping и очистить графовые данные source type.
- `POST /{mapping_id}/replay` — переиграть mapping на исторических данных.
- `POST /preview` — preview mapping без записи в граф.
- `POST /apply` — применить mapping и записать в граф.
- `POST /preview-raw` — preview mapping для произвольного raw JSON (`mapping_id` передаётся query-параметром).

### Edge Presets (`/api/v1/edge-presets`)

- `GET` — список edge presets.
- `GET /{preset_id}` — получить edge preset по id.
- `POST` — создать edge preset.
- `PUT /{preset_id}` — обновить edge preset.
- `DELETE /{preset_id}` — удалить edge preset.

### Mocker (`/api/v1/mocker`)

- `POST /run-full` — запуск `python -m mocker.run --full --url http://localhost:8000`.
- `POST /create-mappings` — запуск `python -m mocker.create_mappings --url http://localhost:8000`.