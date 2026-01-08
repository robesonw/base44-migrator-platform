# Base44 Refactor & Migration Automation Platform (MVP Scaffold)

This repo is a **Python + Postgres** automation platform that orchestrates a **collaborating multi-agent pipeline** to:
- Clone a **source Base44 UI GitHub repo**
- Infer UI data/API needs (**UI Contract Map**)
- Generate backend + DB + async worker skeletons (later agents will implement)
- Wire the frontend to the backend with minimal diffs
- Run verification (compose + smoke tests)
- Push a branch + open a PR to a **target GitHub repo**

> ✅ This is an **implementation-ready scaffold** designed to be continued in Cursor.

---

## Architecture

```mermaid
flowchart LR
  UI[CLI / (Future UI)] --> API[FastAPI Orchestrator]
  API --> DB[(Postgres)]
  API --> RQ[Redis Queue]
  API --> WS[Workspace Runner\nwork dirs/containers]
  RQ --> W1[Celery Worker]
  W1 --> Agents[Agent Plugins]
  Agents --> FS[(Workspace Files)]
  Agents --> GH[GitHub API / git]
  DB --> API
```

---

## Development Workflow

This repository uses a **dev/main branch workflow**:

- **`dev` branch**: Active development branch for new features and changes
- **`main` branch**: Production-ready code

### Workflow Steps:
1. Create feature branches from `dev`: `git checkout -b feature/my-feature dev`
2. Make changes and commit to your feature branch
3. Push feature branch and create PR to `dev`
4. After merging to `dev`, create PR from `dev` to `main` for production deployment

### Creating PRs:
- **Via GitHub Web UI**: Visit https://github.com/robesonw/base44-migrator-platform/compare/main...dev
- **Via Script**: Use `python scripts/create_pr.py` (requires GITHUB_TOKEN environment variable)

---

## Quickstart

### Requirements
- Docker + Docker Compose
- Python 3.11+ (optional if you run only via Docker)

### Run services
```bash
docker compose up --build
```

- API: http://localhost:8080
- Swagger: http://localhost:8080/docs

### Create a job
```bash
curl -X POST http://localhost:8080/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source_repo_url": "https://github.com/robesonw/culinary-compass",
    "target_repo_url": "https://github.com/robesonw/cc",
    "backend_stack": "python",
    "db_stack": "postgres",
    "commit_mode": "pr"
  }'
```

### Poll status
```bash
curl http://localhost:8080/v1/jobs/<JOB_ID>
```

---

## Where to implement the real intelligence
Agent plugins live in `app/agents/`.

Workspace artifacts live under `workspaces/<job_id>/workspace/` and drive downstream steps:
- `ui-contract.json`
- `openapi.yaml`
- `db-schema.md`
- `verification.md`

---

## Troubleshooting

### Docker Issues

**Services fail to start:**
- Ensure Docker and Docker Compose are running
- Check port conflicts: `5432` (PostgreSQL), `6379` (Redis), `8080` (API)
- Verify `.env` file exists with required variables (`DATABASE_URL`, `REDIS_URL`)
- Try rebuilding: `docker compose down -v && docker compose up --build`

**Database connection errors:**
- The API automatically waits for PostgreSQL to be ready (up to 30 seconds)
- Check PostgreSQL logs: `docker compose logs postgres`
- Verify database credentials in `.env` match `docker-compose.yml`
- If issues persist, try: `docker compose restart postgres`

**Volume/permission issues:**
- Ensure `workspaces/` directory exists and is writable
- On Linux/Mac, check file permissions: `chmod -R 755 workspaces/`
- On Windows, ensure Docker Desktop has access to the project directory

### Database Migrations

**Migration fails on startup:**
- The API runs `alembic upgrade head` automatically on startup
- If migration fails, the API will fail fast with clear error logs
- Check API logs: `docker compose logs api`
- Verify database is accessible: `docker compose exec postgres psql -U app -d app -c "SELECT 1"`
- To run migrations manually: `docker compose exec api alembic upgrade head`

**Reset database:**
- WARNING: This will delete all data
- `docker compose down -v` (removes volumes)
- Restart services: `docker compose up`

**Check migration status:**
- `docker compose exec api alembic current`
- `docker compose exec api alembic history`

### Logs

**View logs:**
- All services: `docker compose logs`
- Specific service: `docker compose logs api` or `docker compose logs worker`
- Follow logs: `docker compose logs -f worker`
- Last 100 lines: `docker compose logs --tail=100 api`

**Worker logs format:**
- All worker logs include `job_id` and `stage` fields
- Format: `[job_id=<id> stage=<stage>] - <message>`
- Example: `2024-01-01 12:00:00 INFO app.tasks.jobs [job_id=abc-123 stage=CLONE_SOURCE] - Running stage`

**Logs not appearing:**
- Ensure services are running: `docker compose ps`
- Check log level in environment variables
- Verify volumes are mounted correctly

---

## Run generated backend smoke test

The smoke test script generates a backend, starts it with Docker Compose, and runs CRUD tests against one Postgres and one Mongo entity.

**Bash (Linux/Mac):**
```bash
./scripts/test_generated_backend.sh
```

**PowerShell (Windows):**
```powershell
.\scripts\test_generated_backend.ps1
```

The script:
1. Runs the full generator pipeline (Intake → Domain Modeling → API Design → Backend Generation)
2. Starts the generated backend with `docker compose up -d --build`
3. Waits for the health endpoint to be ready
4. Selects one Postgres and one Mongo entity from the storage plan
5. Performs full CRUD operations (POST, GET list, GET by ID, PATCH, DELETE) on both entities
6. Writes a `verification.md` report to the workspace artifacts
7. Cleans up by running `docker compose down -v`

You can customize the test by setting environment variables:
- `JOB_ID`: Job identifier (default: `generated_backend_smoke`)
- `SOURCE_REPO_URL`: Source repository URL (default: `https://github.com/robesonw/culinary-compass.git`)
- `OUT_DIR`: Output directory (default: `test_output/${JOB_ID}/workspace`)

---

## Repo layout
```
app/
  api/                FastAPI routes
  agents/             Agent plugin implementations
  core/               config, logging, workflow engine, github wrapper
  db/                 SQLAlchemy models + session
  schemas/            Pydantic models
  tasks/              Celery tasks
  workspace/          Workspace lifecycle utilities
docs/
docker/
docker-compose.yml
```
