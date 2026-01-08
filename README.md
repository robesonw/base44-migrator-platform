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
    "source_repo_url": "https://github.com/ORG/source-base44-ui",
    "target_repo_url": "https://github.com/ORG/target-migrated-repo",
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
