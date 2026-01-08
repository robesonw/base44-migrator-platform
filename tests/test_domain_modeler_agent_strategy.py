"""Tests for DomainModelerAgent hybridStrategy configuration."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from app.agents.impl_design import DomainModelerAgent


def test_docToMongo_strategy_additionalProperties():
    """Test that docToMongo strategy classifies entities with additionalProperties as mongo."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        # Create contract with entity that has additionalProperties
        contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
            "envVars": [],
            "apiClientFiles": [],
            "entities": [
                {
                    "name": "Config",
                    "sourcePath": "src/Entities/Config.json",
                    "fields": [
                        {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {"name": "name", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {
                            "name": "settings",
                            "type": "object",
                            "required": False,
                            "nullable": False,
                            "raw": {
                                "type": "object",
                                "additionalProperties": True
                            }
                        }
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                }
            ],
            "entityDetection": {"directoriesFound": [], "filesParsed": 1, "filesFailed": []},
            "endpointsUsed": [],
            "notes": []
        }
        
        contract_path = artifacts_dir / "ui-contract.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        
        mock_job = MagicMock()
        mock_job.db_stack = "hybrid"
        mock_job.artifacts = {
            "db_preferences": {
                "hybridStrategy": "docToMongo"
            }
        }
        mock_job.id = "test-job-id"
        
        class MockWorkspace:
            def __init__(self, root, source_dir, artifacts_dir):
                self.root = root
                self.source_dir = source_dir
                self.artifacts_dir = artifacts_dir
        
        mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)
        
        agent = DomainModelerAgent()
        result = agent.run(mock_job, mock_ws)
        
        assert result.ok, f"Agent failed: {result.message}"
        
        # Check storage-plan.json
        storage_plan_path = artifacts_dir / "storage-plan.json"
        assert storage_plan_path.exists(), "storage-plan.json was not created"
        
        with open(storage_plan_path, "r", encoding="utf-8") as f:
            storage_plan = json.load(f)
        
        assert storage_plan["mode"] == "hybrid"
        assert len(storage_plan["entities"]) == 1
        assert storage_plan["entities"][0]["name"] == "Config"
        assert storage_plan["entities"][0]["store"] == "mongo", "Entity with additionalProperties should be mongo in docToMongo strategy"
        reason_lower = storage_plan["entities"][0]["reason"].lower()
        assert "additionalproperties" in reason_lower or "additional" in reason_lower, f"Reason should mention additionalProperties: {storage_plan['entities'][0]['reason']}"
        assert "map" in reason_lower, f"Reason should mention map: {storage_plan['entities'][0]['reason']}"


def test_docToMongo_strategy_default():
    """Test that docToMongo is the default strategy (no db_preferences)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        # Create contract with entity that has additionalProperties
        contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
            "envVars": [],
            "apiClientFiles": [],
            "entities": [
                {
                    "name": "Metadata",
                    "sourcePath": "src/Entities/Metadata.json",
                    "fields": [
                        {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {
                            "name": "tags",
                            "type": "object",
                            "required": False,
                            "nullable": False,
                            "raw": {
                                "type": "object",
                                "additionalProperties": True
                            }
                        }
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                }
            ],
            "entityDetection": {"directoriesFound": [], "filesParsed": 1, "filesFailed": []},
            "endpointsUsed": [],
            "notes": []
        }
        
        contract_path = artifacts_dir / "ui-contract.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        
        mock_job = MagicMock()
        mock_job.db_stack = "hybrid"
        mock_job.artifacts = {}  # No db_preferences - should default to docToMongo
        mock_job.id = "test-job-id"
        
        class MockWorkspace:
            def __init__(self, root, source_dir, artifacts_dir):
                self.root = root
                self.source_dir = source_dir
                self.artifacts_dir = artifacts_dir
        
        mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)
        
        agent = DomainModelerAgent()
        result = agent.run(mock_job, mock_ws)
        
        assert result.ok, f"Agent failed: {result.message}"
        
        # Check storage-plan.json
        storage_plan_path = artifacts_dir / "storage-plan.json"
        with open(storage_plan_path, "r", encoding="utf-8") as f:
            storage_plan = json.load(f)
        
        assert storage_plan["entities"][0]["store"] == "mongo", "Default strategy (docToMongo) should classify additionalProperties as mongo"
        reason_lower = storage_plan["entities"][0]["reason"].lower()
        assert "additionalproperties" in reason_lower or "additional" in reason_lower, f"Reason should mention additionalProperties: {storage_plan['entities'][0]['reason']}"


def test_postgresJsonbFirst_strategy_additionalProperties():
    """Test that postgresJsonbFirst strategy keeps additionalProperties in postgres (stored as JSONB)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        # Create contract with entity that has simple additionalProperties (no nested properties)
        contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
            "envVars": [],
            "apiClientFiles": [],
            "entities": [
                {
                    "name": "Settings",
                    "sourcePath": "src/Entities/Settings.json",
                    "fields": [
                        {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {"name": "name", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {
                            "name": "metadata",
                            "type": "object",
                            "required": False,
                            "nullable": False,
                            "raw": {
                                "type": "object",
                                "additionalProperties": True
                            }
                        }
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                }
            ],
            "entityDetection": {"directoriesFound": [], "filesParsed": 1, "filesFailed": []},
            "endpointsUsed": [],
            "notes": []
        }
        
        contract_path = artifacts_dir / "ui-contract.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        
        mock_job = MagicMock()
        mock_job.db_stack = "hybrid"
        mock_job.artifacts = {
            "db_preferences": {
                "hybridStrategy": "postgresJsonbFirst"
            }
        }
        mock_job.id = "test-job-id"
        
        class MockWorkspace:
            def __init__(self, root, source_dir, artifacts_dir):
                self.root = root
                self.source_dir = source_dir
                self.artifacts_dir = artifacts_dir
        
        mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)
        
        agent = DomainModelerAgent()
        result = agent.run(mock_job, mock_ws)
        
        assert result.ok, f"Agent failed: {result.message}"
        
        # Check storage-plan.json
        storage_plan_path = artifacts_dir / "storage-plan.json"
        with open(storage_plan_path, "r", encoding="utf-8") as f:
            storage_plan = json.load(f)
        
        assert storage_plan["entities"][0]["store"] == "postgres", "postgresJsonbFirst strategy should keep simple additionalProperties in postgres (as JSONB)"
        
        # Check that db-schema.sql exists and contains the entity
        db_schema_sql_path = artifacts_dir / "db-schema.sql"
        assert db_schema_sql_path.exists(), "db-schema.sql should exist for postgres entity"
        
        sql_content = db_schema_sql_path.read_text(encoding="utf-8")
        assert "settings" in sql_content.lower(), "Settings table should be in SQL"


def test_postgresJsonbFirst_strategy_array_of_objects():
    """Test that postgresJsonbFirst strategy classifies array-of-objects as mongo (deep nesting)."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        # Create contract with entity that has array of objects
        contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
            "envVars": [],
            "apiClientFiles": [],
            "entities": [
                {
                    "name": "Collection",
                    "sourcePath": "src/Entities/Collection.json",
                    "fields": [
                        {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {
                            "name": "items",
                            "type": "array",
                            "required": False,
                            "nullable": False,
                            "raw": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "value": {"type": "string"}
                                    }
                                }
                            }
                        }
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                }
            ],
            "entityDetection": {"directoriesFound": [], "filesParsed": 1, "filesFailed": []},
            "endpointsUsed": [],
            "notes": []
        }
        
        contract_path = artifacts_dir / "ui-contract.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        
        mock_job = MagicMock()
        mock_job.db_stack = "hybrid"
        mock_job.artifacts = {
            "db_preferences": {
                "hybridStrategy": "postgresJsonbFirst"
            }
        }
        mock_job.id = "test-job-id"
        
        class MockWorkspace:
            def __init__(self, root, source_dir, artifacts_dir):
                self.root = root
                self.source_dir = source_dir
                self.artifacts_dir = artifacts_dir
        
        mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)
        
        agent = DomainModelerAgent()
        result = agent.run(mock_job, mock_ws)
        
        assert result.ok, f"Agent failed: {result.message}"
        
        # Check storage-plan.json
        storage_plan_path = artifacts_dir / "storage-plan.json"
        with open(storage_plan_path, "r", encoding="utf-8") as f:
            storage_plan = json.load(f)
        
        assert storage_plan["entities"][0]["store"] == "mongo", "postgresJsonbFirst strategy should classify array-of-objects as mongo (deep nesting)"
        assert "array of objects" in storage_plan["entities"][0]["reason"].lower()

