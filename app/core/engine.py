from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from app.core.workflow import JobStage
from app.db.models import MigrationJob
from app.workspace.manager import WorkspaceManager
from app.agents.registry import AgentRegistry

log = logging.getLogger(__name__)

class WorkflowEngine:
    def __init__(self, db: Session, workspace: WorkspaceManager, job_id: str):
        self.db = db
        self.ws = workspace
        self.job_id = job_id
        self.registry = AgentRegistry.default()

    def _set_stage(self, job: MigrationJob, stage: JobStage) -> None:
        job.stage = stage
        self.db.commit()

    def _merge_artifacts(self, job: MigrationJob, updates: dict) -> None:
        current = job.artifacts or {}
        current.update(updates)
        job.artifacts = current
        self.db.commit()

    def run(self, job: MigrationJob) -> None:
        stages = [
            JobStage.CLONE_SOURCE,
            JobStage.CLONE_TARGET,
            JobStage.INTAKE_UI_CONTRACT,
            JobStage.DESIGN_DB_SCHEMA,
            JobStage.DESIGN_API,
            JobStage.GENERATE_BACKEND,
            JobStage.ADD_ASYNC,
            JobStage.WIRE_FRONTEND,
            JobStage.VERIFY,
            JobStage.CREATE_PR,
        ]

        for stage in stages:
            self._set_stage(job, stage)
            log.info("Running stage", extra={"job_id": self.job_id, "stage": str(stage)})

            agent = self.registry.get(stage)
            result = agent.run(job=job, ws=self.ws)

            self._merge_artifacts(job, result.artifacts_index)

            if not result.ok:
                log.error("Stage failed", extra={"job_id": self.job_id, "stage": str(stage)})
                job.status = "FAILED"
                job.error_message = result.message
                job.stage = JobStage.FAILED
                self.db.commit()
                raise RuntimeError(result.message)
