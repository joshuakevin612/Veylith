# Veylith

Continuous security scanning for GitHub repositories. Sign in with GitHub, pick repositories, and every push is scanned for leaked secrets, vulnerable dependencies and insecure code patterns, with results on a dashboard.

- `web/` — Next.js dashboard
- `api/` — FastAPI backend, scan worker and scanners
- [docs/PLAN.md](docs/PLAN.md) — architecture, who owns what, milestones
- [CLAUDE.md](CLAUDE.md) — rules for AI coding agents working in this repo

## First-time setup

You need Git, Docker Desktop, Node 20+ and [uv](https://docs.astral.sh/uv/) (`pip install uv`).

```bash
docker compose up -d
```

```bash
cd api && uv sync && cp .env.example .env
```

```bash
cd web && npm install && cp .env.example .env.local
```

Then create your **own** GitHub OAuth App for local development (the values to use are in `api/.env.example`) and fill in `api/.env`.

## Running

```bash
cd api && uv run uvicorn app.main:app --reload
```

```bash
cd web && npm run dev
```

Open http://localhost:3000 — the page shows "API connected" when both halves are running.

## Checks (same as CI)

```bash
cd api && uv run ruff check . && uv run pytest
```

```bash
cd web && npm run lint && npm run typecheck
```
