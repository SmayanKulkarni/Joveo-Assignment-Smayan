# Container and Blueprint

Status: written, not yet built (Render's first build is the test)
Blocked by: [Public backend settings](01-public-backend-settings.md)
Spec: [Choose a free backend host](../../deployment/issues/07-choose-a-free-backend-host.md), [What survives a restart](../../deployment/issues/04-what-survives-a-restart.md)

- `Dockerfile`: `python:3.12-slim`, install `uv`, copy only `pyproject.toml`, `uv.lock` and `src/`, run `uv sync --frozen --no-dev`, and start with `scout serve --host 0.0.0.0 --port $PORT` from the venv, in shell form so `$PORT` expands.
- `render.yaml`: `type: web`, `runtime: docker`, `plan: free`, and `sync: false` for `OPENROUTER_API_KEY`, `ADZUNA_APP_ID`, `ADZUNA_API_KEY`, `USAJOBS_API_KEY`, `USAJOBS_USER_AGENT`, `LANGSMITH_API_KEY`, `LANGSMITH_TRACING`, `LANGSMITH_PROJECT`, `ACCESS_CODE` and `WEB_ORIGIN`. Set `LLM_CONCURRENCY` to `5` and `JEV_CONCURRENCY` to `16`, because the free instance is small. No `healthCheckPath`: the host guard could refuse a probe with an internal Host and fail the deploy, and Render then just checks the open port.

No Docker on this machine, so Render's build is the test. Done when the build log is clean and `/api/meta` answers.
