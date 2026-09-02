FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir poetry==1.8.5

WORKDIR /app

COPY packages/domain/pyproject.toml packages/domain/poetry.lock* packages/domain/
COPY packages/shared/pyproject.toml packages/shared/poetry.lock* packages/shared/
COPY packages/ai/pyproject.toml packages/ai/poetry.lock* packages/ai/
COPY packages/worker/pyproject.toml packages/worker/poetry.lock* packages/worker/
COPY pyproject.toml poetry.lock* ./

RUN cd packages/worker && poetry export -f requirements.txt --without-hashes -o /tmp/requirements.txt

RUN pip install --no-cache-dir --prefix=/install -r /tmp/requirements.txt

# --- runtime ---------------------------------------------------------------

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /install /usr/local
COPY packages/domain/ packages/domain/
COPY packages/shared/ packages/shared/
COPY packages/ai/ packages/ai/
COPY packages/worker/ packages/worker/

ENV PYTHONPATH="/app/packages/domain:/app/packages/shared:/app/packages/ai:/app/packages/worker"

CMD ["arq", "worker.main.WorkerSettings"]
