from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage

class DomainModelerAgent(BaseAgent):
    stage = JobStage.DESIGN_DB_SCHEMA
    def run(self, job, ws):
        schema_path = ws.artifacts_dir / "db-schema.md"
        schema_path.write_text(
            "# DB Schema (placeholder)\n\n"
            "- TODO: Infer entities from ui-contract.json\n"
            "- TODO: Generate migrations in the migrated app repo\n",
            encoding="utf-8"
        )
        return AgentResult(self.stage, True, "Wrote placeholder db-schema.md", {"db_schema": str(schema_path.relative_to(ws.root))})

class ApiDesignerAgent(BaseAgent):
    stage = JobStage.DESIGN_API
    def run(self, job, ws):
        openapi_path = ws.artifacts_dir / "openapi.yaml"
        openapi_path.write_text(
            "openapi: 3.0.3\n"
            "info:\n"
            "  title: Generated API (placeholder)\n"
            "  version: 0.1.0\n"
            "paths: {}\n",
            encoding="utf-8"
        )
        return AgentResult(self.stage, True, "Wrote placeholder openapi.yaml", {"openapi": str(openapi_path.relative_to(ws.root))})
