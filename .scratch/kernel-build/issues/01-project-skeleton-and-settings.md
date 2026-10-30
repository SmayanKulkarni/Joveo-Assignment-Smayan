# 01: Project skeleton and settings

**What to build:** a working Python project that every later ticket builds in. A developer runs `uv run pytest` from a clean checkout and it passes, and the Kernel's settings load from the real root `.env`. Spec: [Kernel LLD](../../../docs/lld/kernel.md) §2, §13, §16 steps 1-2.

Pin the versions from the research: `langgraph` 1.2.18, `langgraph-checkpoint-sqlite` 3.1.2, `langchain-core` 1.7.2, `langchain-openrouter` 0.2.9, `langchain-typesafe` 0.0.1a3, `langsmith` 0.14.16, `pydantic` 2.14.2, plus `pydantic-settings` and `pytest` at their current versions.

Decisions made when these tickets were cut, not in the LLD:
- **Adzuna key name.** `.env` has `ADZUNA_API_KEY`, while the LLD's field is `adzuna_app_key`. Keep the LLD's field name and read the existing variable through an alias. Don't change `.env`.
- **`LANGSMITH_TRACING`.** It is in `.env` but missing from the LLD's settings table. Add it and export it with the other LangSmith vars, because tracing depends on it. Update §13 to match.
- **uv on PATH.** `uv` was installed with `pip --user` into Python's user Scripts folder, which may not be on PATH. Make sure `uv` resolves from a normal shell.

**Blocked by:** None (can start immediately).

**Status:** done

- [x] `uv run pytest` passes from a clean checkout on Python 3.12, with the dependencies above pinned
- [x] The `talent_scout` package imports from the `src` layout
- [x] `get_settings()` loads the real `.env`, is cached, and exports the LangSmith vars to the environment on first load, before any LangChain call
- [x] Every setting and default in LLD §13 exists
- [x] Test: a `max_tokens` value of 999 is rejected
- [x] Test: a comma list in `LLM_CHEAP` parses into a model chain
- [x] Test: `ADZUNA_API_KEY` populates `adzuna_app_key`
- [x] `.gitignore` covers `.venv`, `.cache` and `graphify-out/`
- [x] A `.graphifyignore` excludes `.claude/`, so skills and agent worktrees stay out of the code graph
- [x] `graphify update .` builds a graph containing the new package and nothing from `.claude/`
