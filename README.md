# Task Manager — варіант 14

Наскрізний Python-проєкт для курсу **«Професійний Python»**. Предметна область — система керування завданнями.

**Автор:** [вкажи власні ПІБ] · **Група:** ФеП-33 · **Індивідуальний варіант:** 14

Проєкт продовжує один і той самий домен від ЛР1 до ЛР10 і містить консольний інтерфейс, модуль аналітики, потоковий CSV pipeline, типізовану ООП-модель, імпорт/експорт, автоматизовані тести, SQLite/SQLAlchemy persistence layer, REST API, профілювання, package build, Docker та GitHub Actions.

## 1. Предметна область і функціональність

Основна сутність `Task` містить:

- `title` — назва;
- `description` — опис;
- `priority` — `low`, `medium`, `high` або `critical`;
- `status` — `todo`, `in_progress`, `completed` або `cancelled`;
- `assigned_to` — ID користувача-виконавця;
- `deadline` — необов'язковий дедлайн;
- `created_at` — дата створення.

Реалізовано створення, перегляд, пошук, фільтрацію за статусом/пріоритетом/виконавцем, зміну статусу та пріоритету, призначення виконавця, видалення, підрахунок completed/incomplete і пошук прострочених завдань. `cancelled` є термінальним статусом; завершене завдання можна повернути в роботу.

## 2. Структура проєкту

```text
task-manager/
├── .github/workflows/ci.yml
├── data/
│   ├── tasks.csv
│   └── tasks_with_errors.csv
├── logs/
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial.py
│       └── 0002_add_deadline.py
├── output/
├── reports/
│   ├── lab09_experiment_notes.md
│   ├── lab09_performance_report.json
│   └── validation.md
├── src/task_manager/
│   ├── analytics.py
│   ├── api.py
│   ├── config.py
│   ├── config.yaml
│   ├── database.py
│   ├── db_models.py
│   ├── dbapi.py
│   ├── domain.py
│   ├── enums.py
│   ├── exceptions.py
│   ├── external_api.py
│   ├── import_export.py
│   ├── logging_config.py
│   ├── main.py
│   ├── performance.py
│   ├── protocols.py
│   ├── repositories.py
│   ├── resources.py
│   ├── schemas.py
│   ├── services.py
│   └── streaming.py
├── tests/
│   ├── conftest.py
│   └── test_*.py
├── .dockerignore
├── .env.example
├── .gitignore
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── MANIFEST.in
└── README.md
```

## 3. Відповідність лабораторним роботам

| ЛР | Реалізація у проєкті |
|---|---|
| 1 | `src-layout`, package `task_manager`, `pyproject.toml`, `README`, `.gitignore`, `main.py`, type hints, CLI та Git history. |
| 2 | `list`, `tuple`, `set`, `dict`, `Counter`, `defaultdict`, comprehensions, generator expressions, `*args`, `**kwargs`, lambda, closure, decorator, пошук/групування/сортування/агрегація. |
| 3 | `TaskBatchIterator`, `iter()`/`next()` protocol, generators, `yield from`, `itertools.groupby`, `islice`, streaming CSV reader, lazy filters/transforms та batching. |
| 4 | `Task`, `BugTask`, `FeatureTask`, `Priority`, `TaskBoard`, dataclasses, encapsulation/validation, inheritance, composition, ABC `TaskPolicy`, `Protocol`, `TypedDict`, `TypeVar`/Generic, dunder methods. |
| 5 | Custom exceptions, exception chaining, logging, YAML configuration, CSV streaming import, strict/tolerant modes, JSON export, custom context manager `AtomicTextWriter`, atomic `os.replace`. |
| 6 | pytest fixtures, parametrization, `tmp_path`, `monkeypatch`, `Mock`, `MagicMock`, `AsyncMock`, unit/integration/API tests, coverage command. |
| 7 | SQLite, SQLAlchemy ORM, `users`/`tasks`, CRUD repositories, parameterized DB-API queries, transactions/rollback, Alembic revisions, `deadline`, integration tests. |
| 8 | FastAPI, Pydantic schemas, REST endpoints, HTTP status codes, HTTPX async client, `asyncio.Task`, `gather`, `Semaphore`, timeout і retry. |
| 9 | Dataset generator на 100 000+ задач, `timeit`, `cProfile`, `tracemalloc`, `ThreadPoolExecutor`, `ProcessPoolExecutor`, NumPy aggregation, dashboard cache з invalidation. |
| 10 | Installable package, wheel/sdist, environment configuration, Dockerfile, persistent volume, GitHub Actions: Ruff, mypy, pytest/coverage, package build і Docker build. |

## 4. Встановлення та локальний запуск

Потрібен Python 3.11 або новіший.

```bash
# 1. Перейти в корінь проєкту
cd task-manager

# 2. Створити та активувати virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Оновити pip та встановити проєкт з dev dependencies
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

# 4. Підготувати локальну конфігурацію
cp .env.example .env

# 5. Запустити демонстрацію CLI
python -m task_manager.main demo
```

Для shell-сесії можна завантажити `.env` так:

```bash
set -a
source .env
set +a
```

`DATABASE_URL` за замовчуванням — `sqlite:///./data/task_manager.db`. Каталог `data/` створюється автоматично. `DATABASE_AUTO_CREATE=true` дозволяє створити таблиці під час старту API для локальної демонстрації.

## 5. База даних і міграції

Для швидкого локального запуску:

```bash
python -m task_manager.main db-init
```

Для контрольованого оновлення схеми через Alembic використовуйте нову/порожню базу даних та вимкніть автоматичне створення таблиць:

```bash
export DATABASE_URL="sqlite:///./data/task_manager.db"
export DATABASE_AUTO_CREATE=false
alembic upgrade head
```

Історія міграцій:

- `0001_initial` — таблиці `users` і `tasks`, foreign key та індекси;
- `0002_add_deadline` — додавання `tasks.deadline` та індексу для призначеного виконавця/дедлайну.

У `dbapi.py` також є параметризовані SQLite DB-API запити для фільтрації та транзакційне пакетне оновлення статусів з rollback у разі помилки.

## 6. CSV import та JSON export

CSV має заголовки `task_id,title,description,priority,status`; необов'язкові поля — `assigned_to,deadline`.

```bash
# Tolerant: некоректні рядки реєструються і пропускаються
python -m task_manager.main import-csv data/tasks_with_errors.csv output/tasks.json

# Strict: імпорт зупиняється на першому некоректному рядку
python -m task_manager.main import-csv data/tasks.csv output/tasks.json --strict
```

Дозволені значення priority/status завантажуються з `config.yaml`. Експорт виконується через власний context manager: дані спочатку записуються в тимчасовий файл у тій самій директорії, а після успішного завершення атомарно замінюють цільовий файл. У разі помилки частковий JSON не залишається.

## 7. REST API

```bash
uvicorn task_manager.api:app --reload
```

Документація Swagger: `http://127.0.0.1:8000/docs`.

| Метод | Endpoint | Призначення |
|---|---|---|
| GET | `/health` | Перевірка доступності сервісу. |
| GET/POST | `/users` | Перегляд і створення виконавців. |
| GET | `/users/{id}/tasks` | Завдання конкретного користувача. |
| GET/POST | `/tasks` | Список завдань з фільтрами або створення. |
| GET | `/tasks/{id}` | Отримання одного завдання. |
| PUT/PATCH | `/tasks/{id}` | Повна або часткова зміна назви, опису, priority, status, виконавця або deadline. |
| DELETE | `/tasks/{id}` | Видалення завдання. |
| GET | `/tasks/overdue` | Прострочені незавершені завдання. |
| GET | `/statistics` | Dashboard статистика. |
| GET | `/tasks/statistics` | Alias dashboard статистики для ЛР8. |
| GET | `/integrations/remote-users/tasks` | Паралельне отримання списків завдань зовнішніх користувачів. |

Фільтри `GET /tasks`: `status`, `priority`, `user_id`, `q`. Приклади:

```bash
curl http://127.0.0.1:8000/health
curl "http://127.0.0.1:8000/tasks?status=todo&priority=high"
curl -X POST http://127.0.0.1:8000/users \
  -H 'Content-Type: application/json' \
  -d '{"name":"Ada Lovelace","email":"ada@example.com"}'
curl -X POST http://127.0.0.1:8000/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"Prepare release","description":"Release notes","priority":"high","status":"todo","assigned_to":1,"deadline":"2027-01-15"}'
```

Для async integration endpoint задайте `TASKS_SOURCE_URL` як базову адресу сумісного сервісу. Клієнт використовує HTTPX, concurrency limit через `asyncio.Semaphore`, `asyncio.create_task`/`gather`, timeout і повторні спроби.

## 8. Тестування та якість

```bash
pytest
pytest --cov=task_manager --cov-branch --cov-report=term-missing
ruff check src tests
ruff format --check src tests
mypy src/task_manager
```

Тести покривають domain objects, priority/status validation, status transitions, CRUD, фільтрацію, пошук, completed/incomplete, overdue, strict/tolerant CSV import, malformed records, JSON export, configuration, atomic write, repositories, DB-API rollback, API workflow, Mock/AsyncMock та генерацію профілювального набору. Під час фінальної перевірки: **40 passed**, branch coverage **86,81%**; перевірені команди та локальні обмеження задокументовані у `reports/validation.md`.

## 9. Профілювання та оптимізація (ЛР9)

```bash
# Генерація 100 000 задач, baseline profiling і CPU comparison
python -m task_manager.main profile --count 100000 --workers 4

# Для швидшого першого експерименту обмежити CPU-набір
python -m task_manager.main profile --count 100000 --workers 4 --cpu-sample-size 5000
```

Команда формує `output/performance_report.json` і `output/task_manager.prof`. У звіті є час baseline, `timeit`, peak memory з `tracemalloc`, cProfile artifact, NumPy aggregation і порівняння sequential/thread/process для CPU-bound kernel. `load_task_files_parallel()` призначений для I/O-bound паралельного завантаження кількох CSV через `ThreadPoolExecutor`. Коефіцієнт прискорення обчислюється як `sequential_time / parallel_time`; він може бути меншим за 1 через overhead або GIL.

Dashboard statistics кешується в `TaskService`; cache invalidation відбувається після створення, оновлення (включно зі status/priority/assignee) та видалення завдання.

### Контрольний експеримент (100 000 задач)

Зразок вимірювання, виконаний 10.11.2026 у середовищі збірки цього проєкту:

| Експеримент | Час | Speedup відносно sequential |
|---|---:|---:|
| Baseline: фільтрація/сортування/підрахунок/overdue | 0,565 с | 1,00× |
| CPU kernel sequential | 0,616 с | 1,00× |
| CPU kernel ThreadPoolExecutor | 1,807 с | 0,34× |
| CPU kernel ProcessPoolExecutor | 1,644 с | 0,37× |
| Повторна dashboard-статистика без cache | 30,70 мс/виклик | 1,00× |
| Повторна dashboard-статистика з cache | близько 0,00013 мс/виклик | близько 233 000× |

У цьому штучному CPU kernel thread/process overhead виявився більшим за виграш від розпаралелювання, тому ці два способи не прискорили саме цю операцію. Натомість кешування повторного незмінного dashboard-запиту прибрало повторний обхід 100 000 об'єктів і дало вимірюване прискорення. Це приклад того, чому оптимізацію потрібно підтверджувати вимірюваннями, а не припускати, що паралельність завжди швидша. Абсолютні часи залежать від CPU, ОС та навантаження.

## 10. Docker

```bash
cp .env.example .env
docker compose build
docker compose up
```

API буде доступне на `http://127.0.0.1:8000`. Named volume `task-manager-data` зберігає SQLite database між перезапусками контейнера.

Окремо:

```bash
docker build -t task-manager:1.0.0 .
docker run --rm -p 8000:8000 -v task-manager-data:/app/data task-manager:1.0.0
```

## 11. Packaging і CI/CD

```bash
python -m pip install build
python -m build
ls dist/  # wheel + sdist
```

GitHub Actions у `.github/workflows/ci.yml` запускає Ruff lint/format, mypy, pytest з branch coverage, збирає wheel/sdist та Docker image на `push` і `pull_request` до `main`/`master`.

## 12. Сценарій демонстрації на захисті

1. Показати структуру `src/task_manager`, `pyproject.toml`, `.gitignore` і `git log`.
2. Запустити CLI demo та пояснити `Task`, `Priority`, `TaskStatus`.
3. Продемонструвати фільтрацію/пошук/групування, `Counter`, closure, decorator та lazy generator pipeline.
4. Імпортувати `data/tasks_with_errors.csv` у tolerant mode, показати invalid rows і JSON output.
5. Запустити `pytest --cov`, показати unit та integration tests.
6. Показати SQLite/SQLAlchemy repositories і Alembic migration `deadline`.
7. Запустити API, створити user/task, змінити статус, отримати overdue та statistics.
8. Запустити profiling на 100 000 задач і пояснити speedup/overhead.
9. Зібрати package та Docker image, показати GitHub Actions workflow.

## 13. Безпека та межі реалізації

Секрети не зберігаються в коді, Dockerfile або Git. `.env` виключений через `.gitignore`; `.env.example` містить лише безпечні локальні значення. Для production слід використовувати окрему керовану базу, секрети CI/CD та вимкнути `DATABASE_AUTO_CREATE`, застосовуючи Alembic migrations.
