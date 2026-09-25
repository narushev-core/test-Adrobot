# syntax=docker/dockerfile:1

FROM python:3.12-slim AS builder

ENV POETRY_VERSION=2.2.1 \
    POETRY_HOME=/opt/poetry \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"
ENV PATH="${POETRY_HOME}/bin:${PATH}"

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-root --no-directory

COPY src ./src
COPY docs/README.md ./docs/README.md
RUN poetry install --only main


FROM python:3.12-slim AS runtime

RUN useradd --create-home --shell /usr/sbin/nologin adrobot

WORKDIR /app
ENV PATH="/app/.venv/bin:${PATH}" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY --from=builder /app/.venv ./.venv
COPY src ./src
COPY frontend ./frontend
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

RUN chown -R adrobot:adrobot /app
USER adrobot

EXPOSE 8000

CMD ["uvicorn", "adrobot.presentation.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
