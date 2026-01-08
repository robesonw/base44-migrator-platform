#!/usr/bin/env python3
"""
Script to run the full migration workflow including GitCommitAgent.
Usage: python scripts/run_full_workflow.py
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine
from app.db.models import MigrationJob, Base
from app.core.workflow import JobStage
from app.workspace.manager import WorkspaceManager
from app.core.engine import WorkflowEngine
from app.core.config import settings

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

def run_workflow(source_repo_url: str, target_repo_url: str, backend_stack: str = "python", db_stack: str = "postgres"):
    """Run the full migration workflow."""
    db: Session = SessionLocal()
    try:
        # Create job
        job = MigrationJob(
            source_repo_url=source_repo_url,
            target_repo_url=target_repo_url,
            backend_stack=backend_stack,
            db_stack=db_stack,
            commit_mode="pr",
            artifacts={},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        print(f"Created job: {job.id}")
        print(f"Source: {source_repo_url}")
        print(f"Target: {target_repo_url}")
        print(f"Backend: {backend_stack}, DB: {db_stack}")
        print()
        
        # Create workspace
        ws = WorkspaceManager(job_id=job.id)
        ws.ensure()
        print(f"Workspace created at: {ws.root}")
        print()
        
        # Run workflow
        print("=" * 80)
        print("Starting workflow...")
        print("=" * 80)
        print()
        
        engine_instance = WorkflowEngine(db=db, workspace=ws, job_id=job.id)
        engine_instance.run(job)
        
        # Refresh job to get final state
        db.refresh(job)
        
        print()
        print("=" * 80)
        print(f"Workflow completed! Status: {job.status}, Stage: {job.stage}")
        print("=" * 80)
        print()
        
        # Show artifacts
        if job.artifacts:
            print("Job Artifacts:")
            for key, value in job.artifacts.items():
                print(f"  {key}: {value}")
            print()
        
        # Check for gitops.md
        gitops_path = ws.artifacts_dir / "gitops.md"
        if gitops_path.exists():
            print("=" * 80)
            print("GitOps Output (gitops.md):")
            print("=" * 80)
            print(gitops_path.read_text(encoding="utf-8"))
            print()
        
        # Check target repo
        target_repo_dir = ws.root / "target_repo"
        if target_repo_dir.exists():
            print("=" * 80)
            print(f"Target repo directory: {target_repo_dir}")
            print("=" * 80)
            
            backend_dir = target_repo_dir / "backend"
            if backend_dir.exists():
                print(f"\nBackend directory exists: {backend_dir}")
                print(f"Files in backend:")
                for item in sorted(backend_dir.rglob("*")):
                    if item.is_file():
                        rel_path = item.relative_to(target_repo_dir)
                        print(f"  {rel_path}")
            
            artifacts_dir = target_repo_dir / "migrator-artifacts" / job.id
            if artifacts_dir.exists():
                print(f"\nArtifacts directory exists: {artifacts_dir}")
                print(f"Files in artifacts:")
                for item in sorted(artifacts_dir.rglob("*")):
                    if item.is_file():
                        rel_path = item.relative_to(target_repo_dir)
                        print(f"  {rel_path}")
        
        return job
        
    except Exception as e:
        print(f"\nERROR: Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        if job:
            db.refresh(job)
            print(f"Job status: {job.status}")
            print(f"Job stage: {job.stage}")
            print(f"Error message: {job.error_message}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    source_repo = "https://github.com/robesonw/culinary-compass.git"
    target_repo = "https://github.com/robesonw/cc.git"
    
    print("Running full migration workflow...")
    print(f"Source: {source_repo}")
    print(f"Target: {target_repo}")
    print()
    
    # Check for GitHub token
    github_token = os.getenv("GH_TOKEN") or settings.github_token
    if github_token:
        print(f"GitHub token found: {'*' * (len(github_token) - 4)}{github_token[-4:]}")
    else:
        print("WARNING: No GitHub token found. PR will not be created automatically.")
    print()
    
    job = run_workflow(
        source_repo_url=source_repo,
        target_repo_url=target_repo,
        backend_stack="python",
        db_stack="postgres"
    )
    
    print(f"\nJob ID: {job.id}")
    print(f"Final Status: {job.status}")
    print(f"Final Stage: {job.stage}")


