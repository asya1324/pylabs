# Фінальний звіт перевірки проєкту

**Дата:** 10.11.2026  
**Проєкт:** Task Manager, варіант 14  
**Середовище тестування:** Linux, Python 3.13.5

## Успішно перевірено

| Перевірка | Результат |
|---|---|
| `PYTHONPATH=src pytest --cov=task_manager --cov-branch --cov-report=term-missing` | 40 тестів пройшли; branch coverage 86,81%; поріг 80% виконано |
| `alembic upgrade head` на окремій SQLite-БД | Обидві міграції пройшли; поточна ревізія `0002_add_deadline` |
| Схема БД після міграції | Таблиці `users`, `tasks`; колонка `tasks.deadline` присутня |
| `python -m task_manager.main demo` | Успішний запуск CLI та демонстрація задач |
| `import-csv` у tolerant mode | 5 рядків, 1 валідний запис, 4 невалідні записи залоговано й пропущено; JSON сформовано |
| Wheel build | `task_manager-1.0.0-py3-none-any.whl` створено |
| Source distribution build | `task_manager-1.0.0.tar.gz` створено; перевірена наявність migrations, tests, data та reports |
| Чисте virtualenv | Wheel встановлено через `pip install --no-deps`; перевірено імпорт пакета, metadata version та вбудований `config.yaml` |
| Git | Історія містить окремі commits за етапами scaffold, domain/processing, persistence/API, tests/deployment і documentation; робоче дерево чисте |

## Що не вдалося виконати в цьому середовищі

- `ruff check`, `ruff format --check` та `mypy` не запускалися: ці інструменти не були встановлені, а мережевий доступ для інсталяції пакетів у контейнері був недоступний. Команди включено до GitHub Actions workflow, який встановлює залежності з `.[dev]` і запускає їх на Python 3.12.
- Docker image не будувався локально, оскільки Docker CLI/daemon відсутній у середовищі виконання. Крок `docker build` є в GitHub Actions; `Dockerfile` та `docker-compose.yml` додані.

Отже, тести, міграції, CLI, імпорт/експорт, wheel/sdist та ізольоване встановлення перевірені локально. Ruff/mypy та реальний Docker build залишаються для запуску в GitHub Actions або локальному середовищі з відповідними інструментами.
