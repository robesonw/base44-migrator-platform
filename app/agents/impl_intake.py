import json
from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage

class RepoIntakeAgent(BaseAgent):
    stage = JobStage.INTAKE_UI_CONTRACT

    def run(self, job, ws):
        artifact_path = ws.artifacts_dir / "ui-contract.json"
        contract = {
            "source_repo_url": job.source_repo_url,
            "framework": "unknown",
            "apiClientFiles": [],
            "endpointsUsed": [],
            "envVars": [],
            "notes": [
                "TODO: Implement real scanning for axios/fetch usage, api client wrappers, and env vars.",
                "This file should drive OpenAPI + DB schema generation."
            ],
        }
        artifact_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        return AgentResult(self.stage, True, "Generated placeholder ui-contract.json", {
            "ui_contract": str(artifact_path.relative_to(ws.root))
        })
