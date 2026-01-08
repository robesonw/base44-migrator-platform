from dataclasses import dataclass
from typing import Dict, Any
from app.core.workflow import JobStage

@dataclass
class AgentResult:
    stage: JobStage
    ok: bool
    message: str
    artifacts_index: Dict[str, Any]

class BaseAgent:
    stage: JobStage
    def run(self, job, ws) -> AgentResult:
        raise NotImplementedError
