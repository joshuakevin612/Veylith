# Veylith — rules for AI coding agents

Veylith scans a user's GitHub repositories on every push (secrets, vulnerable dependencies, insecure code patterns) and shows the results on a dashboard. Full plan and milestones: [docs/PLAN.md](docs/PLAN.md). Read it before starting a milestone.

Two developers work in this repo at the same time, each with an AI agent. **Ask the human which developer they are (Dev A or Dev B) if it is not obvious, then stay inside that developer's folders.**

- Dev A (Platform): _name here_
- Dev B (Scanners and Dashboard): _name here_

## Ownership map

| Path | Owner |
|---|---|
| `api/app/main.py`, `config.py`, `db.py`, `security.py`, `worker.py` | Dev A |
| `api/app/models/`, `api/app/routers/`, `api/app/services/`, `api/alembic/` | Dev A |
| `api/tests/api/` | Dev A |
| `web/app/(auth)/`, `web/app/(onboarding)/` | Dev A |
| `api/app/scanners/`, `api/tests/scanners/`, `api/tests/fixtures/` | Dev B |
| `web/app/(dashboard)/`, `web/components/`, `web/lib/` | Dev B |
| `CLAUDE.md`, `docs/`, `.github/`, `docker-compose.yml`, root config | shared — change only in a dedicated PR |

If a task needs a change in the other developer's folder, **stop and tell the human** what is needed instead of editing it.

## The two contracts

Everything the two halves share goes through these. A change to either is its own small PR, agreed between both developers first.

1. **Scanner interface** — `api/app/scanners/base.py` (`Finding`, `Scanner`, `make_fingerprint`) and `run_scan(repo_dir) -> list[Finding]` in `api/app/scanners/__init__.py`. The scanners package must not import the database, the GitHub client or FastAPI.
2. **REST API** — `api/openapi.json`, generated from the FastAPI app. After changing any route or response model:
   ```
   cd api && uv run python scripts/export_openapi.py
   cd web && npm run gen:api
   ```
   Commit both generated files. CI fails if they are stale. The planned endpoint list is in docs/PLAN.md.

## Commands

```
docker compose up -d                              # local Postgres
cd api && uv sync                                 # install backend deps (Python 3.12)
cd api && uv run uvicorn app.main:app --reload    # API on :8000
cd api && uv run pytest                           # backend tests
cd api && uv run ruff check . && uv run ruff format .
cd api && uv run python -m app.scanners <folder>  # run scanners on a local folder
cd api && uv run alembic upgrade head             # apply migrations
cd web && npm install && npm run dev              # dashboard on :3000
cd web && npm run lint && npm run typecheck
```

If `uv` is not on PATH, use `python -m uv` instead.

## Conventions

- **Backend:** FastAPI, SQLAlchemy 2 (sync sessions, `psycopg`), Pydantic models for every request and response. One model per file in `app/models/`, one router per file in `app/routers/`, mounted under `/api` in `main.py`.
- **Frontend:** Next.js App Router, TypeScript, Tailwind. The browser only calls `/api/*`; Next.js forwards it to FastAPI (see `web/next.config.ts`). Types come from `web/lib/api/schema.d.ts`, never hand-written copies. This Next.js version is newer than most training data: read `web/AGENTS.md` and the docs in `web/node_modules/next/dist/docs/` before using a Next.js API.
- **Frontend is never blocked by backend:** if an endpoint does not exist yet, build against a fixture in `web/lib/api/mocks/` shaped like the contract, behind `NEXT_PUBLIC_USE_MOCKS=1`.
- **Migrations:** only Dev A creates Alembic revisions.
- **Dependencies:** tell the human before adding a package so both developers know. On a lockfile conflict, take `main`'s lockfile and reinstall; do not hand-merge it.
- **Git:** never commit to `main`. Branches are `a/<topic>` or `b/<topic>`, small PRs, squash-merge. Pull `main` before starting work.

## Security rules (this is a security product)

- Never commit real secrets. `.env` files are git-ignored; update `.env.example` when adding a variable.
- **Fake secrets in tests must be built at runtime** (`"ghp_" + "a" * 36`), never written as a literal, or GitHub push protection blocks the push.
- Scanned repository code is only ever read as text. Never execute, import or `eval` it.
- Never store or log a raw secret found by a scanner; snippets are redacted before they become a `Finding`.
- Every query for a repo, scan or finding is filtered by the logged-in user.
- Webhooks are verified with a constant-time HMAC check before anything else happens.
