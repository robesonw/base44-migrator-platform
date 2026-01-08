import logging
from git import Repo
from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage

log = logging.getLogger(__name__)

class CloneSourceAgent(BaseAgent):
    stage = JobStage.CLONE_SOURCE
    def run(self, job, ws):
        try:
            if ws.source_dir.exists() and any(ws.source_dir.iterdir()):
                return AgentResult(self.stage, True, "Source already present", {"source_dir": str(ws.source_dir)})
            Repo.clone_from(job.source_repo_url, ws.source_dir, depth=1)
            return AgentResult(self.stage, True, "Cloned source repo", {"source_dir": str(ws.source_dir)})
        except Exception as e:
            return AgentResult(self.stage, False, f"Failed to clone source repo: {e}", {})

class CloneTargetAgent(BaseAgent):
    stage = JobStage.CLONE_TARGET
    def run(self, job, ws):
        try:
            if ws.target_dir.exists() and any(ws.target_dir.iterdir()):
                return AgentResult(self.stage, True, "Target already present", {"target_dir": str(ws.target_dir)})
            Repo.clone_from(job.target_repo_url, ws.target_dir, depth=1)
            return AgentResult(self.stage, True, "Cloned target repo", {"target_dir": str(ws.target_dir)})
        except Exception as e:
            return AgentResult(self.stage, False, f"Failed to clone target repo: {e}", {})
