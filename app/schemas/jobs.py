from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any
from app.core.workflow import JobStage

class JobCreateRequest(BaseModel):
    source_repo_url: str = Field(..., examples=["https://github.com/org/source"])
    target_repo_url: str = Field(..., examples=["https://github.com/org/target"])
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
