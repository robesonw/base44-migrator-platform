import json
import logging
from pathlib import Path
from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage
from app.agents.intake_scanner import (
    discover_entities,
    detect_framework,
    detect_env_vars,
    scan_endpoints,
    detect_api_client_files,
)

log = logging.getLogger(__name__)


class RepoIntakeAgent(BaseAgent):
    stage = JobStage.INTAKE_UI_CONTRACT

    def run(self, job, ws):
        try:
            artifact_path = ws.artifacts_dir / "ui-contract.json"
            source_dir = ws.source_dir
            
            if not source_dir.exists():
                return AgentResult(
                    self.stage,
                    False,
                    f"Source directory does not exist: {source_dir}",
                    {}
                )
            
            log.info(f"Scanning source repository at {source_dir}")
            
            # 1. Entity discovery
            log.info("Discovering entities...")
            entity_result = discover_entities(source_dir)
            
            # 2. Framework detection
            log.info("Detecting framework...")
            framework_info = detect_framework(source_dir)
            
            # 3. Env var detection
            log.info("Detecting environment variables...")
            env_vars = detect_env_vars(source_dir)
            
            # 4. Endpoint usage scan
            log.info("Scanning for API endpoints...")
            endpoints = scan_endpoints(source_dir)
            
            # 5. API client files detection
            log.info("Detecting API client files...")
            api_client_files = detect_api_client_files(source_dir)
            
            # Build contract
            entities_list = [
                {
                    "name": e.name,
                    "sourcePath": e.sourcePath,
                    "fields": e.fields,
                    "relationships": e.relationships,
                    "rawShapeHint": e.rawShapeHint,
                }
                for e in entity_result.entities
            ]
            
            # Ensure framework is always an object with name and versionHint
            if not isinstance(framework_info, dict) or "name" not in framework_info:
                framework_info = {"name": "unknown", "versionHint": ""}
            if "versionHint" not in framework_info:
                framework_info["versionHint"] = ""
            
            # Log counts
            log.info(
                f"Intake scan completed: {len(entities_list)} entities, "
                f"{len(endpoints)} endpoints, {len(env_vars)} env vars found"
            )
            
            contract = {
                "source_repo_url": job.source_repo_url,
                "framework": framework_info,
                "envVars": env_vars if env_vars else [],
                "apiClientFiles": api_client_files if api_client_files else [],
                "entities": entities_list if entities_list else [],
                "entityDetection": {
                    "directoriesFound": entity_result.directoriesFound if entity_result.directoriesFound else [],
                    "filesParsed": entity_result.filesParsed,
                    "filesFailed": entity_result.filesFailed if entity_result.filesFailed else [],
                },
                "endpointsUsed": endpoints if endpoints else [],
                "notes": [],
            }
            
            # Add meaningful notes (no TODO placeholders)
            if entity_result.filesFailed:
                contract["notes"].append(
                    f"Failed to parse {len(entity_result.filesFailed)} entity file(s). "
                    "See entityDetection.filesFailed for details."
                )
            
            if not entity_result.entities:
                contract["notes"].append(
                    "No entities found. Ensure entity JSON files are in src/Entities/, "
                    "src/entities/, src/models/, or app/Entities/ directories."
                )
            
            if not endpoints:
                contract["notes"].append(
                    "No endpoints detected. UI may not call external APIs or uses patterns not detected by scanner."
                )
            
            if not env_vars:
                contract["notes"].append(
                    "No environment variables detected. UI may not use NEXT_PUBLIC_* or VITE_* variables."
                )
            
            # Write contract file
            artifact_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
            log.info(f"Generated ui-contract.json with {len(entities_list)} entities, "
                    f"{len(endpoints)} endpoints, {len(env_vars)} env vars")
            
            return AgentResult(
                self.stage,
                True,
                f"Generated ui-contract.json with {len(entities_list)} entities, "
                f"{len(endpoints)} endpoints",
                {"ui_contract": str(artifact_path.relative_to(ws.root))}
            )
        
        except Exception as e:
            log.exception(f"Failed to generate ui-contract.json: {e}")
            error_message = str(e)
            
            # Write a small failure artifact (NOT a TODO placeholder contract)
            artifact_path = ws.artifacts_dir / "ui-contract-error.json"
            failure_artifact = {
                "error": True,
                "source_repo_url": job.source_repo_url,
                "error_message": error_message,
                "stage": str(self.stage),
            }
            artifact_path.write_text(json.dumps(failure_artifact, indent=2), encoding="utf-8")
            
            return AgentResult(
                self.stage,
                False,
                f"Failed to generate ui-contract.json: {error_message}",
                {"error_artifact": str(artifact_path.relative_to(ws.root))}
            )
