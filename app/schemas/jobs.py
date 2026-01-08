from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List
from datetime import datetime
from app.core.workflow import JobStage

class JobCreateRequest(BaseModel):
    source_repo_url: str = Field(..., examples=["https://github.com/robesonw/culinary-compass"])
    target_repo_url: str = Field(..., examples=["https://github.com/robesonw/cc"])
    backend_stack: Literal["python", "node"] = "python"
    db_stack: Literal["postgres", "mongo"] = "postgres"
    commit_mode: Literal["pr", "direct"] = "pr"

class JobResponse(BaseModel):
    id: str
    source_repo_url: str
    target_repo_url: str
    backend_stack: str
    db_stack: str
    commit_mode: str
    stage: JobStage
    status: str
    error_message: Optional[str] = None
    artifacts: Dict[str, Any] = {}


class ArtifactInfo(BaseModel):
    path: str
    size: int
    last_modified: datetime


class ArtifactsResponse(BaseModel):
    job_id: str
    artifacts: List[ArtifactInfo]
