## Быстрый старт

```bash
# Клонирование репозитория
git clone https://github.com/moevm/mse1h2026-resource
cd mse1h2026-resource

# Создание .env файла
cp .env.example .env

# 1. # Запуск всех сервисов
docker compose up --build

#Заходим в контейнер бэкенда и все команды генерации выполняем внутри
docker exec -it resourse-backend sh

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