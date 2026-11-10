# Veylith — project plan (2 developers, shared GitHub repo)

## Context

Veylith is a continuous security platform: a user signs in with GitHub OAuth, picks repositories, Veylith installs webhooks, and every push triggers a background scan (secrets, vulnerable dependencies, insecure code patterns) whose results appear on a dashboard with scores, trends and file/line remediation.

The project folder is empty and not yet a git repo, so this is a greenfield plan. Decisions already made:

- **Stack:** Next.js (dashboard) + FastAPI (API and scan worker) + Postgres
- **Scope:** course / portfolio project, a few weeks, deployed demo
- **Hosting:** free tiers
- **Scanners:** written by us (no Gitleaks/Semgrep); OSV.dev is used only as the vulnerability *database*

Two people build it at the same time, each with an AI coding agent. The plan is therefore organised around one goal: **each person owns separate folders and they meet only at two small, written contracts**, so two agents never rewrite the same file.

## Architecture

```
GitHub ──push webhook──▶ FastAPI  ──insert scan row (queued)──▶ Postgres
   ▲                        │                                       │
   │ OAuth, repo list,      │ REST (JSON)                           │ worker loop claims job
   │ hook install, tarball  ▼                                       ▼
   └──────────────────  Next.js dashboard            download tarball @ SHA → run 3 scanners
                        (proxies /api/* to FastAPI)   → save findings → compute score
```

Key choices and why:

| Area | Choice | Reason |
|---|---|---|
| GitHub integration | OAuth App, scopes `read:user repo admin:repo_hook` | Matches the spec (OAuth + webhooks we install ourselves). A GitHub App is the more modern route; noted as a stretch, not needed. |
| Session | FastAPI runs the OAuth flow, sets an httpOnly `SameSite=Lax` JWT cookie | Next.js rewrites `/api/*` to FastAPI so the cookie is first-party; no CORS or cross-site cookie problems between Vercel and the API host. |
| Job queue | **Postgres is the queue**: the `scans` table with `status`, claimed via `SELECT … FOR UPDATE SKIP LOCKED` | No Redis, no paid background worker. The worker loop starts inside the API process (`RUN_WORKER=1`) but lives in `app/worker.py` so it can run standalone later. |
| Getting code | `GET /repos/{owner}/{repo}/tarball/{sha}` into a temp dir | No git binary, no clone; exact commit SHA; deleted after the scan. |
| Live updates | Dashboard polls scan status every 3 s while a scan is running (TanStack Query) | Simple and reliable; SSE is a stretch goal. |
| Shared types | FastAPI exports `api/openapi.json` (committed); `npm run gen:api` produces TypeScript types | The API contract is a file both agents can read, and CI fails if it is stale. |
| Hosting | Vercel (web), Render free web service (API + worker), Neon (Postgres) | All free. |

**Free-tier caveat:** Render's free service sleeps when idle, and GitHub gives webhooks 10 s to answer, so a push can be missed during a cold start. Two mitigations are in the plan: a free uptime pinger on `/health`, and a "catch-up" check that compares each repo's HEAD SHA with the last scanned SHA when the dashboard loads and queues a scan if they differ.

### Data model (Postgres, SQLAlchemy 2 + Alembic)

- `users` — github_id, login, avatar_url, access_token (Fernet-encrypted)
- `repositories` — user_id, github_repo_id, full_name, default_branch, webhook_id, webhook_secret, active
- `scans` — repository_id, commit_sha, branch, trigger (`push`/`manual`/`initial`), status (`queued`/`running`/`done`/`failed`), score, counts per severity, started_at, finished_at, error
- `findings` — scan_id, repository_id, scanner (`secrets`/`deps`/`sast`), rule_id, severity, title, file_path, line, snippet (secrets redacted), remediation, fingerprint, state (`new`/`existing`/`fixed`)
- `webhook_deliveries` — delivery GUID, for de-duplicating GitHub retries

`fingerprint = sha256(scanner, rule_id, file_path, normalised snippet)` lets a scan say which findings are new, still present, or fixed since the previous scan; that is what powers the trend charts.

**Health score:** `100 − (25·critical + 10·high + 4·medium + 1·low)`, floored at 0, shown as a grade A–F.

### Contract 1 — scanner interface (owned by Dev B, consumed by Dev A's worker)

```python
# api/app/scanners/base.py
class Finding(BaseModel):
    scanner: Literal["secrets", "deps", "sast"]
    rule_id: str; severity: Literal["critical", "high", "medium", "low"]
    title: str; file_path: str; line: int | None
    snippet: str; remediation: str; fingerprint: str

def run_scan(repo_dir: Path) -> list[Finding]: ...   # api/app/scanners/__init__.py
```

The scanner package never touches the database, GitHub or FastAPI. It can be run alone: `python -m app.scanners <folder>` prints findings as JSON.

### Contract 2 — REST API (owned by Dev A, consumed by Dev B's dashboard)

```
GET  /api/auth/github/login      GET /api/auth/github/callback     POST /api/auth/logout
GET  /api/me
GET  /api/github/repos                     repos the user can monitor
POST /api/repos            DELETE /api/repos/{id}        (installs / removes the webhook)
GET  /api/repos            GET  /api/repos/{id}          (with latest score and counts)
POST /api/repos/{id}/scan                  manual scan
GET  /api/repos/{id}/scans GET  /api/scans/{id}
GET  /api/repos/{id}/findings?severity=&scanner=&state=
GET  /api/repos/{id}/trends                score and counts per scan over time
GET  /api/dashboard/summary                totals across all repos
POST /api/webhooks/github                  HMAC-verified, returns 202 at once
```

### The three scanners (all original code)

- **Secrets** — a rule table of regexes (AWS keys, GitHub/Slack/Stripe tokens, private key blocks, `password = "…"` style assignments) plus Shannon-entropy check for generic high-entropy strings; skips binaries, lockfiles, `node_modules`, minified files. Stored snippets are always redacted (`ghp_ab…wxyz`).
- **Dependencies** — our own parsers for `package-lock.json`, `requirements.txt`, `poetry.lock` (more later), then one batched query to the OSV.dev API; severity from CVSS, remediation "upgrade X from 1.2.3 to ≥ 1.2.9".
- **SAST** — Python through the `ast` module (`eval`/`exec`, `subprocess(shell=True)`, SQL built with f-strings or `%` inside `.execute()`, `pickle.loads`, `yaml.load`, `verify=False`, Flask `debug=True`, MD5/SHA1); JavaScript/TypeScript through regex rules kept in a YAML file (`innerHTML`, `dangerouslySetInnerHTML`, `eval`, `document.write`, `child_process.exec` with concatenation, SQL template strings).

## Repository layout and ownership

```
veylith/
├─ CLAUDE.md                 shared rules for both AI agents (see below)
├─ docker-compose.yml        local Postgres
├─ .github/workflows/ci.yml  ruff + pytest, eslint + tsc, openapi freshness check
├─ docs/PLAN.md              this plan
├─ api/                      Python 3.12, uv, FastAPI
│  ├─ openapi.json           generated, committed
│  ├─ alembic/               ── Dev A only
│  └─ app/
│     ├─ main.py, config.py, db.py, security.py     ── Dev A
│     ├─ models/   (one file per table)             ── Dev A
│     ├─ routers/  auth, repos, scans, findings, dashboard, webhooks ── Dev A
│     ├─ services/ github.py, scoring.py, tarball.py ── Dev A
│     ├─ worker.py                                   ── Dev A
│     └─ scanners/ base.py, secrets.py, deps/, sast/, rules/, __main__.py ── Dev B
│  └─ tests/  scanners/ + fixtures/ (Dev B), api/ (Dev A)
└─ web/                      Next.js App Router, TypeScript, Tailwind, shadcn/ui, Recharts, TanStack Query, npm
   ├─ lib/api/               generated types + fetch client     ── Dev B (regenerated by either)
   ├─ app/(auth)/, app/(onboarding)/   login, repo picker       ── Dev A
   └─ app/(dashboard)/       overview, repo detail, findings, trends ── Dev B
```

**Dev A — "Platform"**: OAuth and sessions, GitHub API client, repo selection and webhook install, webhook receiver, job queue and worker, database and migrations, REST endpoints, login and repo-picker pages, backend deployment.

**Dev B — "Scanners and Dashboard"**: the three scanners and their tests and fixtures, the scanner CLI, every dashboard page, charts, frontend deployment.

Each person owns a full vertical slice (A: "connect a repo", B: "see what is wrong with it"), so both have demo-able work every week.

## Working rules for two people vibecoding in one repo

1. **One person scaffolds.** Dev A does Milestone 0 alone and pushes; Dev B clones only after that. Two agents scaffolding in parallel guarantees conflicts in every config file.
2. **`CLAUDE.md` is the shared brain.** It holds the ownership map above, the two contracts, commands (`uv run pytest`, `npm run dev`, `npm run gen:api`), and the rule "do not edit files outside your owner's folders; if a change is needed there, stop and say so". Both agents read it automatically, so they follow the same conventions.
3. **`main` is protected.** Work on short branches (`a/webhooks`, `b/secrets-scanner`), open a PR, CI must pass, the other person skims it, squash-merge. Merge at least daily and pull `main` before each session; long-lived AI branches drift fast.
4. **Contract changes are their own small PR**, agreed in chat first: `scanners/base.py` and anything that changes `openapi.json`.
5. **Migrations: Dev A only.** If B needs a column, B asks A. Two Alembic heads is the most common team breakage.
6. **Dependencies:** say so in chat before adding a package; on a lockfile conflict, take `main`'s lockfile and reinstall rather than hand-merging.
7. **Frontend is never blocked by backend.** B builds against JSON fixtures shaped like the contract (`web/lib/api/mocks/`), switched off by an env flag once the real endpoint exists.
8. **Secrets and local setup:** `.env` is git-ignored, `.env.example` is committed. Each developer creates their *own* GitHub OAuth App for localhost and their own smee.io channel for webhooks; a third OAuth App is for production.
9. **Fake secrets in test fixtures must be assembled at test time** (for example `"ghp_" + "a" * 36`), otherwise GitHub push protection will block the push, and we would be leaking pattern-valid tokens in a security product's repo.
10. Ask the agent for small tasks ("add the HMAC check to the webhook route with tests"), read the diff before committing, and never commit code you cannot explain; this matters for a course.

## Milestones (about five weeks; compress or stretch as needed)

| | Dev A — Platform | Dev B — Scanners and Dashboard | Done when |
|---|---|---|---|
| **M0** (2 days, A first, then together) | `git init`, GitHub repo, monorepo scaffold, Docker Postgres, CI, `CLAUDE.md`, both contracts written, hello-world deploy of web and API | Clone, run everything locally, create own OAuth App and smee channel, review contracts | Both can run web + API locally; CI is green; deployed URLs answer |
| **M1** (week 1) | OAuth login, session cookie, `users`, `/api/me`, `/api/github/repos`, login page | `Finding`, `run_scan`, CLI, **secrets scanner** with tests, a deliberately vulnerable fixture project | A can log in with GitHub; B's CLI finds planted secrets |
| **M2** (week 2) | Repo picker page, webhook install/remove, webhook receiver with HMAC and de-dupe, `scans` queue, worker loop calling a stubbed `run_scan` | **Dependency scanner** (parsers + OSV), dashboard shell and pages against mock data | A push creates a `done` scan row; dashboard looks complete on mocks |
| **M3** (week 3) | Tarball download and safe extraction, worker runs real `run_scan`, saves findings, scans/findings endpoints | **SAST scanner**, switch dashboard from mocks to real API | **First real end-to-end:** push a secret, see it on the dashboard |
| **M4** (week 4) | Scoring, fingerprint diff (new/existing/fixed), trends and summary endpoints, manual scan, initial scan on connect, catch-up check | Score gauges, severity filters, trend charts, finding detail with file/line, GitHub permalink and remediation, live polling | Fixing a finding and pushing shows it as fixed and the score rising |
| **M5** (week 5) | Hardening (below), production deploy, uptime pinger | Empty/loading/error states, responsive polish, public demo repo, README with screenshots, demo video | A stranger can sign in on the live URL and get a scan |

**Hardening checklist (the product is a security tool, so it gets judged on this):** constant-time HMAC comparison with a per-repo webhook secret; OAuth `state` parameter; access tokens encrypted at rest; every repo/scan/finding query filtered by the logged-in user; raw secrets never stored or logged; scanned code is only read, never executed or imported; tar extraction rejects `..`, absolute paths and symlinks, with caps on archive size, file size, file count and scan time; rate limit on the webhook and manual-scan routes.

**Stretch goals, only after M5:** commit status / PR comment with the scan result, SSE instead of polling, suppress or ignore a finding, email or Slack alerts, scan only changed files, more lockfile formats, migrate to a GitHub App.

## Verification

- **Scanners (B):** `uv run pytest api/tests/scanners` — each rule has a positive and a negative fixture; `python -m app.scanners api/tests/fixtures/vulnerable-app` returns the expected findings.
- **Platform (A):** `uv run pytest api/tests/api` — webhook with a bad signature gets 401, a repeated delivery GUID is ignored, user X cannot read user Y's repo, the worker moves a job queued → running → done and marks it failed on error.
- **Contract:** CI regenerates `openapi.json` and fails on a diff; `npm run typecheck` passes against the generated types.
- **End-to-end (both, end of M3 and again at M5):** on the deployed app, sign in, connect the demo repo, push a commit with a fake key, a vulnerable dependency pin and an `eval(input())`; all three appear on the dashboard within about a minute with correct file and line; push the fixes; findings turn "fixed" and the score goes up.

