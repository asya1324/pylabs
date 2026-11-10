FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    LOG_LEVEL=INFO \
    DATABASE_URL=sqlite:///./data/task_manager.db \
    DATABASE_AUTO_CREATE=true

WORKDIR /app

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/data /app/logs /app/output \
    && chown -R appuser:appuser /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY migrations ./migrations
COPY alembic.ini ./

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

USER appuser
EXPOSE 8000
VOLUME ["/app/data"]

CMD ["uvicorn", "task_manager.api:app", "--host", "0.0.0.0", "--port", "8000"]
