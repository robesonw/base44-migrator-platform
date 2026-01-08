from pathlib import Path
from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage
from app.generators.backend_gen import generate_backend

class BackendBuilderAgent(BaseAgent):
    stage = JobStage.GENERATE_BACKEND
    def run(self, job, ws):
        # Get paths to required artifacts
        ui_contract_path = ws.artifacts_dir / "ui-contract.json"
        storage_plan_path = ws.artifacts_dir / "storage-plan.json"
        
        # Check that required artifacts exist
        if not ui_contract_path.exists():
            return AgentResult(
                self.stage,
                False,
                "ui-contract.json not found in workspace artifacts",
                {}
            )
        
        if not storage_plan_path.exists():
            return AgentResult(
                self.stage,
                False,
                "storage-plan.json not found in workspace artifacts",
                {}
            )
        
        # Set output directory for generated backend
        out_dir = ws.root / "generated" / "backend"
        
        try:
            # Generate backend skeleton
            generated_files = generate_backend(
                job_id=job.id,
                ui_contract_path=ui_contract_path,
                storage_plan_path=storage_plan_path,
                out_dir=out_dir,
            )
            
            return AgentResult(
                self.stage,
                True,
                f"Generated {len(generated_files)} backend files",
                {"backend_dir": str(out_dir.relative_to(ws.root))}
            )
        except Exception as e:
            return AgentResult(
                self.stage,
                False,
                f"Backend generation failed: {e}",
                {}
            )

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
