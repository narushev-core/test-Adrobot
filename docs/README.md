# Adrobot — обёртка над Keitaro

Сервис для создания и редактирования рекламных кампаний в трекере Keitaro через его Admin API.

## Вступление

В этом тестовом я решил хорошенько показать свои навыки и знания. Некоторые решения будут излишни в данном контексте, но я всё равно решил их реализовать.

Я стремлюсь к уровню senior-разработчика. Поэтому советую читать документацию по пунктам, которые я опишу ниже: они идут в том порядке, в котором я строил процесс анализа задачи и разработки.

### [1. Определение функциональных и нефункциональных требований](./REQUIREMENTS.md)
### [2. Схема БД](./DATABASE.md)
### [3. Диаграммы последовательности](./SEQUENCE_DIAGRAMS.md)

---

## Стек

| Область | Технологии |
|---------|------------|
| API | FastAPI, [fastapi-filter](https://github.com/arthurio/fastapi-filter), [fastapi-pagination](https://github.com/uriyyo/fastapi-pagination), sse-starlette |
| Воркер и события | [FastStream](https://faststream.airt.ai/), Redpanda (Kafka API) |
| База данных | PostgreSQL, SQLAlchemy 2.0 (async, asyncpg), Alembic |
| Интеграция с Keitaro | httpx (async) |
| Валидация и конфигурация | Pydantic v2, pydantic-settings |
| Планировщик | APScheduler |
| Тесты | pytest, pytest-asyncio, respx |
| Качество кода | ruff (линтер и форматтер), mypy, pre-commit |
| Инфраструктура | Docker, docker compose |

---

## Архитектура

Проект построен по принципам DDD: бизнес-логика отделена от фреймворков, базы данных и внешних API.

```
src/adrobot/
├── domain/            # сущности, value objects, доменные события,
│                      # интерфейсы репозиториев; не зависит ни от чего
├── application/       # сценарии использования (use cases): создание кампании,
│                      # изменение офферов, синк групп
├── infrastructure/    # реализации: SQLAlchemy-репозитории, клиент Keitaro,
│                      # outbox, брокер
└── presentation/
    ├── api/           # FastAPI: роутеры, SSE
    └── worker/        # FastStream: хендлеры событий, планировщик
```

Зависимости направлены строго внутрь: `presentation` → `application` → `domain`. `infrastructure` реализует интерфейсы, объявленные в `domain` и `application`. Благодаря этому бизнес-логику можно тестировать без БД, брокера и Keitaro.

Инварианты предметной области живут в value objects, а не размазаны по сервисам. Например:

- `Geo` — код страны в формате ISO 3166-1 alpha-2, некорректный код не может существовать как объект;
- `OfferShares` — распределение долей офферов в потоке, сумма всегда равна 100.

Все изменяющие операции выполняются асинхронно через события: transactional outbox на стороне продюсера и идемпотентный консьюмер на стороне воркера. Статусы операций доходят до браузера через SSE. Подробности — в [диаграммах последовательности](./SEQUENCE_DIAGRAMS.md).

---

## Быстрый старт

1. Скопируйте файл с переменными окружения и заполните данные Keitaro:

   ```bash
   cp .env.example .env
   ```

2. Запустите проект:

   ```bash
   docker compose up --build
   ```

   Миграции применяются автоматически при старте API. Чтобы применить их вручную:

   ```bash
   docker compose run --rm api alembic upgrade head
   ```

3. Откройте в браузере:

   | Сервис | Адрес |
   |--------|-------|
   | Интерфейс | http://localhost:8000 |
   | Swagger (OpenAPI) | http://localhost:8000/docs |
   | Redpanda Console | http://localhost:8080 |

---

## Переменные окружения

| Переменная | Описание |
|------------|----------|
| `KEITARO_URL` | Адрес трекера Keitaro |
| `KEITARO_API_KEY` | API-ключ из админки Keitaro |
| `KEITARO_DOMAIN_ID` | ID домена для создаваемых кампаний |
| `KEITARO_TRAFFIC_SOURCE_ID` | ID источника трафика для создаваемых кампаний |
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Подключение к PostgreSQL (строка подключения собирается в `settings.db.database_url`) |
| `KAFKA_BOOTSTRAP_SERVERS` | Адрес Redpanda |
| `GROUPS_SYNC_INTERVAL_MINUTES` | Интервал синхронизации групп из Keitaro |

