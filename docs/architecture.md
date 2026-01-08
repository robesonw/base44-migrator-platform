# Architecture

## Components
- **FastAPI Orchestrator**: job intake + status + persistence
- **Postgres**: job/state storage
- **Redis + Celery**: async execution of workflow stages
- **Workspace**: per-job isolated folder with shared artifacts
- **Agent plugins**: deterministic stage executors that write artifacts
- **GitOps**: branch + PR creation to the target repo (stubbed)

## Deterministic stages
1. CLONE_SOURCE
2. CLONE_TARGET
3. INTAKE_UI_CONTRACT
4. DESIGN_DB_SCHEMA
5. DESIGN_API
6. GENERATE_BACKEND
7. ADD_ASYNC
8. WIRE_FRONTEND
9. VERIFY
10. CREATE_PR

## Mermaid diagrams
See `docs/diagrams.mmd`.
