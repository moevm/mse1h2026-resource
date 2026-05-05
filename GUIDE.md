# Руководство по запуску и настройке

## Содержание

1. [Запуск кластера Kubernetes с демо-приложением](#1-запуск-кластера-kubernetes-с-демо-приложением)
2. [Запуск мониторинга (Resource Graph Service)](#2-запуск-мониторинга-resource-graph-service)
3. [Доступ к сервисам](#3-доступ-к-сервисам)
4. [Регистрация пользователя](#4-регистрация-пользователя)
5. [Добавление агентов](#5-добавление-агентов)
6. [Создание / загрузка дефолтных маппингов](#6-создание--загрузка-дефолтных-маппингов)

---

## 1. Запуск кластера Kubernetes с демо-приложением

> Проект: `monitoring-microservices-demo`

### Вариант A: Docker Compose (локально)

```bash
cd monitoring-microservices-demo

# Запуск всех сервисов (приложения + observability-стек)
docker compose up -d

# Запуск с генераторами нагрузки (k6)
docker compose -f docker-compose.yaml -f docker-compose.generators.yaml up -d

# Остановка
docker compose down -v
```

### Вариант B: Kubernetes (удалённый кластер)

```bash
cd monitoring-microservices-demo/k8s

# 1. Собрать и запушить образы в Docker Hub, поменяйте переменую с указанием проекта
./build-and-load-images.sh

# 2. Развернуть инфраструктуру (namespace, configmaps, secrets, storage, observability)
./apply.sh

# 3. Развернуть приложения и observability-стек, поменяйте переменую с указанием проекта
./apply-apps.sh
```

Скрипты используют SSH-доступ к ноде `vpa-k8s-server-1.l.postgrespro.ru` (конфиг и ключ из `~/envs/k8s/ssh/`). Неймспейс: `monitoring-demo`.

**Проверка:**

```bash
kubectl get pods -n monitoring-demo
```

---

## 2. Запуск мониторинга (Resource Graph Service)

> Проект: `mse1h2026-resource`

```bash
cd mse1h2026-resource

# 1. Создать .env (если нет)
cp .env.example .env

# 2. Запустить все сервисы (Redis, Neo4j, Backend, Frontend)
docker compose up --build -d
```

**Что поднимется:**

| Сервис | Контейнер | Описание |
|--------|-----------|----------|
| Redis | `resource-redis` | Кэш / хранение сессий |
| Neo4j | `resource-neo4j` | Графовая БД |
| Backend | `resource-backend` | FastAPI API (порт 8000) |
| Frontend | `resource-frontend` | React UI + Nginx (порт 3000) |

**Остановка:**

```bash
docker compose down -v    # -v удалит тома (данные БД)
docker compose down       # без удаления томов
```

---

## 3. Доступ к сервисам

| Сервис | URL |
|--------|-----|
| **Frontend (UI)** | http://localhost:3000 |
| **Backend API** | http://localhost:8000 |
| **API документация (Swagger)** | http://localhost:8000/docs |
| **Neo4j Browser** | http://localhost:7474 |

> Порты настраиваются в `.env` через `FRONTEND_PORT` и `BACKEND_PORT`.

---

## 4. Регистрация пользователя

### Через UI

1. Откройте http://localhost:3000
2. Нажмите **«Register»** (или перейдите на http://localhost:3000/register)
3. Заполните форму: **email**, **username**, **password**
4. После регистрации вы будете автоматически залогинены

### Через API

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "username": "myuser", "password": "secretpass"}'
```

После регистрации возвращаются `access_token` и `refresh_token`. Используйте `access_token` для авторизации в API (заголовок `Authorization: Bearer <token>`).

**Логин:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "secretpass"}'
```

---

## 5. Добавление агентов

Агенты — это источники данных (OTel Collector, K8s watcher, Terraform и т.д.), которые отправляют топологию в систему.

### Через UI

1. Залогиньтесь → перейдите на вкладку **Agents** (http://localhost:3000/agents)
2. Нажмите **«Register Agent»**
3. Укажите: **name**, **source_type**, опционально **app_token** (если агент привязан к приложению)
4. После регистрации вы получите **agent token** — он нужен агенту для отправки данных

### Через API

```bash
# Сначала (опционально) зарегистрируйте приложение
curl -X POST http://localhost:8000/api/v1/apps/register \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-app", "description": "My application", "owner": "team"}'

# Затем зарегистрируйте агента
curl -X POST http://localhost:8000/api/v1/agents/register \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "k8s-watcher", "source_type": "kubernetes-api", "description": "Kubernetes watcher agent"}'
```

**Доступные source_type:**

`kubernetes-api`, `opentelemetry-traces`, `opentelemetry-metrics`, `istio-access-logs`, `istio-metrics`, `prometheus`, `terraform-state`, `argocd`, `api-gateway`

**Отправка данных от агента:**

```bash
curl -X POST "http://localhost:8000/api/v1/receiver/raw?source_type=kubernetes-api" \
  -H "X-Agent-Token: <agent_token>" \
  -H "Content-Type: application/json" \
  -d '{"nodes": [...], "edges": [...]}'
```

---

## 6. Создание / загрузка дефолтных маппингов

Маппинги преобразуют raw-данные от агентов в узлы и рёбра графа. Дефолтные маппинги создаются один раз.

### Через UI (рекомендуемый способ)

1. Залогиньтесь → перейдите на вкладку **Mapper** (http://localhost:3000/mapper)
2. Нажмите **«Create default mappings»** — создаст и активирует все маппинги
3. Нажмите **«Generate mock data»** — сгенерирует тестовые данные для всех source types

### Через API

```bash
TOKEN="<access_token>"

# Создать дефолтные маппинги
curl -X POST http://localhost:8000/api/v1/mocker/create-mappings \
  -H "Authorization: Bearer $TOKEN"

# Сгенерировать mock-данные
curl -X POST http://localhost:8000/api/v1/mocker/generate-full \
  -H "Authorization: Bearer $TOKEN"
```

### Через CLI (внутри контейнера)

```bash
# Зайти в контейнер бэкенда
docker exec -it resource-backend sh

# Сгенерировать mock-данные
python -m mocker.run --full --url http://localhost:8000

# Создать маппинги
python -m mocker.create_mappings --url http://localhost:8000
```

**Опции `create_mappings`:**

```bash
python -m mocker.create_mappings --dry-run -v          # Предпросмотр без изменений
python -m mocker.create_mappings --source-type kubernetes-api  # Только один source type
python -m mocker.create_mappings --no-activate         # Создать без активации
python -m mocker.create_mappings --skip-data           # Пропустить отправку sample-данных
```

**Дефолтные маппинги включают:**

| Source type | Описание |
|-------------|----------|
| `kubernetes-api` | Kubernetes-объекты (pods, services, deployments) |
| `opentelemetry-traces` | Трейсы из OTel |
| `opentelemetry-metrics` | Метрики из OTel |
| `istio-access-logs` | Логи Istio access |
| `istio-metrics` | Метрики Istio |
| `prometheus` | Метрики Prometheus |
| `prometheus-slo` | SLO-метрики |
| `terraform-state` | Terraform state |
| `argocd` | ArgoCD ресурсы |
| `api-gateway` | API Gateway маршруты |

---

## Быстрый старт (все шаги)

```bash
# 1. Запуск мониторинга
cd mse1h2026-resource
cp .env.example .env
docker compose up --build -d

# 2. Зайти на http://localhost:3000 → Register → создать аккаунт

# 3. В UI: Mapper → "Create default mappings" → "Generate mock data"

# 4. Перейти на Graph → увидеть граф топологии

# 5. (Опционально) Запустить демо-приложение
cd ../monitoring-microservices-demo
docker compose up -d
```
