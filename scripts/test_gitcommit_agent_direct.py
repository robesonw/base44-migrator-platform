#!/usr/bin/env python3
"""
Direct test of GitCommitAgent - runs the full workflow using a temporary database.
This script creates a job and runs all agents including GitCommitAgent.
Usage: python scripts/test_gitcommit_agent_direct.py
"""
import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set up environment for testing
import tempfile
temp_workspace = tempfile.mkdtemp(prefix="test_workspace_")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("WORKSPACES_DIR", temp_workspace)

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from app.db.models import Base, MigrationJob
from app.core.workflow import JobStage
from app.workspace.manager import WorkspaceManager
from app.core.engine import WorkflowEngine

def run_test_workflow():
    """Run the workflow with a temporary SQLite database."""
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    
    db: Session = SessionLocal()
    try:
        # Create job
        job = MigrationJob(
            source_repo_url="https://github.com/robesonw/culinary-compass.git",
            target_repo_url="https://github.com/robesonw/cc.git",
            backend_stack="python",
            db_stack="postgres",
            commit_mode="pr",
            artifacts={},
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        print("=" * 80)
        print("GITCOMMIT AGENT TEST")
        print("=" * 80)
        print(f"Job ID: {job.id}")
        print(f"Source: {job.source_repo_url}")
        print(f"Target: {job.target_repo_url}")
        print(f"Backend: {job.backend_stack}, DB: {job.db_stack}")
        print()
        
        # Check for GitHub token
        github_token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
        if github_token:
            print(f"[OK] GitHub token found: {'*' * (len(github_token) - 4)}{github_token[-4:]}")
        else:
            print("[WARNING] No GH_TOKEN or GITHUB_TOKEN found. PR will not be created automatically.")
        print()
        
        # Create workspace
        ws = WorkspaceManager(job_id=job.id)
        ws.ensure()
        print(f"Workspace: {ws.root}")
        print()
        
        # Run workflow
        print("=" * 80)
        print("Running workflow...")
        print("=" * 80)
        print()
        
        workflow_engine = WorkflowEngine(db=db, workspace=ws, job_id=job.id)
        workflow_engine.run(job)
        
        # Refresh job
        db.refresh(job)
        
        print()
        print("=" * 80)
        print(f"Workflow Status: {job.status}, Stage: {job.stage}")
        print("=" * 80)
        print()
        
        # Show artifacts
        if job.artifacts:
            print("Job Artifacts:")
            for key, value in job.artifacts.items():
                print(f"  {key}: {value}")
            print()
        
        # Show gitops.md if it exists
        gitops_path = ws.artifacts_dir / "gitops.md"
        if gitops_path.exists():
            print("=" * 80)
            print("GITOPS.MD OUTPUT:")
            print("=" * 80)
            print(gitops_path.read_text(encoding="utf-8"))
            print()
        
        # Show target repo structure
        target_repo_dir = ws.root / "target_repo"
        if target_repo_dir.exists():
            print("=" * 80)
            print("TARGET REPO STRUCTURE:")
            print("=" * 80)
            print(f"Location: {target_repo_dir}")
            print()
            
            backend_dir = target_repo_dir / "backend"
            if backend_dir.exists():
                print(f"[OK] Backend directory: {backend_dir}")
                backend_files = list(backend_dir.rglob("*"))
                backend_files = [f for f in backend_files if f.is_file()]
                print(f"  Files: {len(backend_files)}")
                for f in sorted(backend_files)[:10]:  # Show first 10
                    print(f"    {f.relative_to(target_repo_dir)}")
                if len(backend_files) > 10:
                    print(f"    ... and {len(backend_files) - 10} more files")
                print()
            
            artifacts_dir = target_repo_dir / "migrator-artifacts" / job.id
            if artifacts_dir.exists():
                print(f"[OK] Artifacts directory: {artifacts_dir}")
                artifact_files = list(artifacts_dir.rglob("*"))
                artifact_files = [f for f in artifact_files if f.is_file()]
                for f in sorted(artifact_files):
                    print(f"    {f.relative_to(target_repo_dir)}")
                print()
        
        print("=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print(f"Job ID: {job.id}")
        print(f"Status: {job.status}")
        print(f"Stage: {job.stage}")
        if job.error_message:
            print(f"Error: {job.error_message}")
        print(f"\nWorkspace: {ws.root}")
        
        return job
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        if job:
            db.refresh(job)
            print(f"\nJob Status: {job.status}")
            print(f"Job Stage: {job.stage}")
            if job.error_message:
                print(f"Error Message: {job.error_message}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Testing GitCommitAgent with full workflow...")
    print()
    run_test_workflow()

