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

Перед запуском проекта нужно инициализировать k8s кластер(установить cri-o (>= 1.32),kubelet, kubeadm, в качестве CNI можно использовать Calico), для корректной работы рекомендуем использовать кластер из одной control plane и двух воркеров.
Кластер был запущен на трёх впс с Ubuntu 22.04, 
у мастер ноды RAM:4gb, размер диска: 50 gb, ядер: 2.
у обоих воркеров RAM:2gb, размер диска: 30 gb, ядер: 2.

> Проект: `monitoring-microservices-demo`

**Проверка корректности работы:**
Все поды ищз неймспейсам monitoring-demo должны быть runnung. Можно посмотреть на демо видео к третьей итерации в ветке reports.
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

## 6. Создание и настройка маппингов

Маппинги преобразуют raw-данные от агентов в узлы и рёбра графа. Они создаются и редактируются через вкладку **Mapper** или REST API `/api/v1/mapper`. Готовые шаблоны находятся в `app/mapping_templates/`.

**Поддерживаемые source types:**

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

# 3. В UI: Mapper → создать или отредактировать mapping под нужный `source_type`

# 4. Перейти на Graph → увидеть граф топологии

# 5. (Опционально) Запустить демо-приложение
cd ../monitoring-microservices-demo
docker compose up -d
```
