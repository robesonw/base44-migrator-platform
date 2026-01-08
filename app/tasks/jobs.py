from __future__ import annotations
import logging
from sqlalchemy.orm import Session
from app.tasks.celery_app import celery_app
from app.db.session import SessionLocal
from app.db.models import MigrationJob
from app.core.workflow import JobStage
from app.workspace.manager import WorkspaceManager
from app.core.engine import WorkflowEngine

log = logging.getLogger(__name__)

@celery_app.task(name="run_job_workflow")
def run_job_workflow(job_id: str) -> None:
    db: Session = SessionLocal()
    try:
        job = db.get(MigrationJob, job_id)
        if not job:
            log.error("Job not found: %s", job_id)
            return

        job.status = "RUNNING"
        db.commit()

        ws = WorkspaceManager(job_id=job.id)
        ws.ensure()

        engine = WorkflowEngine(db=db, workspace=ws)
        engine.run(job)

        job = db.get(MigrationJob, job_id)
        if job and job.status != "FAILED":
            job.status = "DONE"
            job.stage = JobStage.DONE
            db.commit()

    except Exception as e:
        log.exception("Workflow failed for job %s", job_id)
        job = db.get(MigrationJob, job_id)
        if job:
            job.status = "FAILED"
            job.stage = JobStage.FAILED
            job.error_message = str(e)
            db.commit()
    finally:
        db.close()
