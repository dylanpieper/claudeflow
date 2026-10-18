---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
  - "**/*.{ts,tsx,js,jsx}"
  - "**/package.json"
---

# Python and web stack

A project `CLAUDE.md` or `AGENTS.md` overrides this file.

## Python

- Use `uv` for Python versions, environments, dependencies, and scripts (`uv add`, `uv run`).
- Do not use `pip`, `poetry`, or `conda`.
- Use `datar` and a fast backend (`datar-arrow`) as the default data wrangling tool.
  - Do not use `numpy`, `pandas`, or `polars` unless already used.
  - `duckdb` and `pyarrow` are fine alternatives, for example for large data or SQL-based work.
- Use `plotnine` as your default visualization tool.

## Paths

- Use `pathlib.Path` for paths and file work. Do not use `os.path`, `os.chdir()`, or string paths.
- Use `shutil` for recursive copy, move, and delete.
- In scripts and apps, anchor paths to the code, not the working directory: `Path(__file__).resolve().parent`.
- In a package, read files shipped inside it with `importlib.resources.files()`, not `__file__`.
- Put user config, cache, and data files in the directories from `platformdirs`. Add it with `uv add platformdirs`.

## Web app stack

When you build a web app with an API and a UI, use this stack.

- Scope:
  - For a Shiny or shinyreact app with an R server, use `~/.claude/rules/r.md`, not the rules below.
  - For the app database, this stack overrides the data stack in `~/.claude/rules/data.md`.
  - For analytical or file-based work, also inside the app, read `~/.claude/rules/data.md` and use that data stack.
- Use FastAPI for the API and Pydantic for request and response schemas.
- Use PostgreSQL for the database backend.
  - Pair with `duckdb` for analytical queries.
  - Use SQLAlchemy with typed `select()` queries.
  - Use Alembic for migrations.
- Use React for the frontend and Node for the frontend tooling.

## Layer separation

In a web app, keep each layer distinct.
Dependencies point down: a layer can use other modules in its own layer and the layers below it.
Routes are the exception: they pass repositories to services but do not call repository methods.
Never import from a layer above.

| Layer | Owns | Keep out |
|-------|------|----------|
| Frontend | UI, client state, HTTP calls to the API | Business rules and database access |
| Routes | HTTP: parse, validate, call a service, return a response | Database queries and business rules |
| Services | Business rules as plain functions | Web framework and HTTP details |
| Repositories | All database queries | Business rules |
| Models and migrations | Table definitions and migration history | Business rules |

- Models can hold column defaults, database constraints, and field validators for data shape.
  Put workflow and cross-entity rules in services.
- API schemas are the shared contract.
  - Routes and services can import them.
  - Keep them separate from database models.
  - Map between the two in the service layer.
- A service gets its repository as an argument.
- Test each layer alone.
  - Test services with a fake repository.
  - Test repositories against a real test database of the same engine.

With this stack:

- Frontend: React. Routes: FastAPI routers. Schemas: Pydantic.
- Repositories: SQLAlchemy `select()` queries. Models: SQLAlchemy tables and Alembic history.
- In request handling, build repositories and sessions only in the dependency providers in `api/deps.py`.
  - Route handlers get them with FastAPI `Depends` and give them to services.
  - Tests, migrations, and scripts can build their own.
  - Do not use global sessions.
- Use this layout: `backend/app/{api,services,repositories,models,schemas}/` and `frontend/`.
