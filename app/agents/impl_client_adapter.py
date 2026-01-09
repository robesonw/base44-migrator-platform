"""
Base44ClientAdapterAgent - Generates compatibility client for Base44 API.
"""
import json
import logging
from pathlib import Path
from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage
from app.agents.base44_scanner import scan_base44_client_usage
from app.generators.client_adapter_gen.generator import generate_base44_client_adapter

log = logging.getLogger(__name__)


class Base44ClientAdapterAgent(BaseAgent):
    stage = JobStage.ADAPT_CLIENT  # Will be added to workflow.py
    
    def run(self, job, ws):
        try:
            # Check required artifacts
            storage_plan_path = ws.artifacts_dir / "storage-plan.json"
            ui_contract_path = ws.artifacts_dir / "ui-contract.json"
            
            if not storage_plan_path.exists():
                return AgentResult(
                    self.stage,
                    False,
                    "storage-plan.json not found in workspace artifacts",
                    {}
                )
            
            if not ui_contract_path.exists():
                return AgentResult(
                    self.stage,
                    False,
                    "ui-contract.json not found in workspace artifacts",
                    {}
                )
            
            # Load artifacts
            with open(storage_plan_path, 'r', encoding='utf-8') as f:
                storage_plan = json.load(f)
            
            with open(ui_contract_path, 'r', encoding='utf-8') as f:
                ui_contract = json.load(f)
            
            # Scan source for base44Client usage
            log.info("Scanning source repository for base44Client usage...")
            base44_usage = scan_base44_client_usage(ws.source_dir)
            
            # Write usage artifact
            usage_artifact_path = ws.artifacts_dir / "base44-client-usage.json"
            usage_artifact_path.write_text(
                json.dumps(base44_usage, indent=2),
                encoding="utf-8"
            )
            log.info(f"Generated base44-client-usage.json artifact")
            
            # Generate compatibility client in target repo
            log.info("Generating Base44 compatibility client...")
            generated_files = generate_base44_client_adapter(
                target_dir=ws.target_dir,
                storage_plan=storage_plan,
                ui_contract=ui_contract,
                base44_usage=base44_usage,
                source_dir=ws.source_dir,
            )
            
            log.info(f"Generated {len(generated_files)} compatibility client files")
            
            return AgentResult(
                self.stage,
                True,
                f"Generated Base44 compatibility client with {len(generated_files)} files",
                {
                    "base44_client_usage": str(usage_artifact_path.relative_to(ws.root)),
                    "generated_files": generated_files,
                }
            )
        
        except Exception as e:
            log.exception(f"Failed to generate Base44 compatibility client: {e}")
            return AgentResult(
                self.stage,
                False,
                f"Failed to generate Base44 compatibility client: {e}",
                {}
            )

