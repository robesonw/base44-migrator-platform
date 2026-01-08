from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.models import MigrationJob
from app.schemas.jobs import JobCreateRequest, JobResponse
from app.tasks.jobs import run_job_workflow

router = APIRouter(prefix="/jobs")

@router.post("", response_model=JobResponse)
def create_job(req: JobCreateRequest, db: Session = Depends(get_db)):
    job = MigrationJob(
        source_repo_url=req.source_repo_url,
        target_repo_url=req.target_repo_url,
        backend_stack=req.backend_stack,
        db_stack=req.db_stack,
        commit_mode=req.commit_mode,
        artifacts={},
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    run_job_workflow.delay(job.id)

    return JobResponse(
        id=job.id,
        source_repo_url=job.source_repo_url,
        target_repo_url=job.target_repo_url,
        backend_stack=job.backend_stack,
        db_stack=job.db_stack,
        commit_mode=job.commit_mode,
        stage=job.stage,
        status=job.status,
        error_message=job.error_message,
        artifacts=job.artifacts or {},
    )

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(MigrationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(
        id=job.id,
        source_repo_url=job.source_repo_url,
        target_repo_url=job.target_repo_url,
        backend_stack=job.backend_stack,
        db_stack=job.db_stack,
        commit_mode=job.commit_mode,
        stage=job.stage,
        status=job.status,
        error_message=job.error_message,
        artifacts=job.artifacts or {},
    )
