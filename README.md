# mse1h2026-resource


[Вики по проекту](https://github.com/moevm/mse1h2026-resource/wiki)
[Отчётные материалы](https://github.com/moevm/mse1h2026-resource/tree/reports)
## Запуск приложения

```
docker compose up -d
```

## Запуск mocker для генерации моковых данных каждые 5 секунд

```
python -m mocker.run --url http://localhost:8000 --interval 5
```

## Веб-страница
```
http://localhost:3000
```

# API документация
## Базовый URL

```
http://localhost:8000
```
**POST** `/register`

Регистрация внешнего агента. Перед отправкой топологии агент обязан зарегистрироваться и получить токен.

### Тело запроса

```json
{
  "name": "k8s-agent-1",
  "source_type": "kubernetes",
  "description": "Cluster A agent"
}
```

### Ответ (201 Created)

```json
{
  "agent_id": "uuid",
  "token": "secret-token",
  "name": "k8s-agent-1",
  "source_type": "kubernetes",
  "registered_at": "2026-03-10T12:00:00"
}
```

## Список агентов

**GET** `/`

Возвращает список всех зарегистрированных агентов.

```json
[
  {
    "agent_id": "uuid",
    "name": "k8s-agent-1",
    "source_type": "kubernetes",
    "description": "Cluster A agent",
    "registered_at": "2026-03-10T12:00:00",
    "last_seen_at": "2026-03-10T12:05:00"
  }
]
```

## Получить полный граф

**GET** `/full`

Параметры:
- limit — ограничение количества узлов (по умолчанию 500)
## Получить подграф

**POST** `/subgraph`

BFS-обход вокруг указанного узла.

```json
{
  "center_node_id": "urn:service:api",
  "depth": 2,
  "node_types": ["service"],
  "edge_types": ["calls"]
}
```
## Найти кратчайший путь

**POST** `/path`

```json
{
  "source_id": "urn:service:api",
  "target_id": "urn:db:postgres",
  "max_depth": 5
}
```
## Анализ влияния

**POST** `/impact`

```json
{
  "node_id": "urn:service:api",
  "depth": 3,
  "direction": "downstream"
}
```

directions:
- downstream
- upstream
- both

## Статистика графа

**GET** `/stats`

Возвращает агрегированную статистику по графу.

## Аналитика

**GET** `/analytics`

Параметры:
- limit (по умолчанию 1000)

## Граф с координатами

**GET** `/layout`

Параметры:
- limit (по умолчанию 500)
- layout:
  - spring
  - kamada_kawai
  - circular
  - shell

Возвращает граф с предрассчитанными координатами (x, y).

## Отправка батча топологии

**POST** `/topology`

Требуется авторизация агента.

Принимает пакет узлов и связей:


```json
{
  "nodes": [...],
  "edges": [...]
}
```


## Список предустановленных правил

**GET** `/presets`

Возвращает встроенные правила обхода графа.

## Выполнить правило обхода

**POST** `/execute`

```json
{
  "steps": [
    {
      "edge_types": ["calls"],
      "direction": "out",
      "node_types": ["service"],
      "depth": 2
    }
  ]
}
```
## Скачать граф

**POST** `/download`

Экспортирует граф в выбранном формате.



## Список форматов экспорта

**GET** `/formats`

Возвращает список доступных форматов экспорта.

