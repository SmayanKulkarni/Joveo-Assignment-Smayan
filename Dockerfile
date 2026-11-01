FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src
# Sample Runs the app loads on start, so a fresh deploy is not empty.
COPY seed ./seed
ENV SEED_DIR=seed
RUN uv sync --frozen --no-dev

# Shell form so Render's PORT expands, and exec so the server receives Render's stop signal.
CMD exec .venv/bin/scout serve --host 0.0.0.0 --port ${PORT:-10000}
