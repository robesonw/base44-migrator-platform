from pathlib import Path
from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage

class BackendBuilderAgent(BaseAgent):
    stage = JobStage.GENERATE_BACKEND
    def run(self, job, ws):
        marker = Path(ws.target_dir) / "MIGRATION_BACKEND_TODO.md"
        marker.write_text(
            "# Backend generation TODO\n\n"
            "Generate backend (python|node) based on workspace/openapi.yaml and workspace/ui-contract.json.\n",
            encoding="utf-8"
        )
        return AgentResult(self.stage, True, "Created backend TODO marker", {"backend_marker": "target/MIGRATION_BACKEND_TODO.md"})

class AsyncArchitectAgent(BaseAgent):
    stage = JobStage.ADD_ASYNC
    def run(self, job, ws):
        marker = Path(ws.target_dir) / "MIGRATION_ASYNC_TODO.md"
        marker.write_text(
            "# Async architecture TODO\n\n"
            "Add queue + worker (Redis) pattern for long-running tasks.\n",
            encoding="utf-8"
        )
        return AgentResult(self.stage, True, "Created async TODO marker", {"async_marker": "target/MIGRATION_ASYNC_TODO.md"})

class FrontendWiringAgent(BaseAgent):
    stage = JobStage.WIRE_FRONTEND
    def run(self, job, ws):
        marker = Path(ws.target_dir) / "MIGRATION_WIRING_TODO.md"
        marker.write_text(
            "# Frontend wiring TODO\n\n"
            "Update ONLY api client wrapper + env vars to point to backend.\n",
            encoding="utf-8"
        )
        return AgentResult(self.stage, True, "Created wiring TODO marker", {"wiring_marker": "target/MIGRATION_WIRING_TODO.md"})

class VerificationAgent(BaseAgent):
    stage = JobStage.VERIFY
    def run(self, job, ws):
        report = Path(ws.artifacts_dir) / "verification.md"
        report.write_text(
            "# Verification (placeholder)\n\n"
            "- TODO: run docker compose for migrated app\n"
            "- TODO: smoke test endpoints\n"
            "- TODO: optional Playwright UI smoke tests\n",
            encoding="utf-8"
        )
        return AgentResult(self.stage, True, "Wrote placeholder verification report", {"verification": str(report.relative_to(ws.root))})
