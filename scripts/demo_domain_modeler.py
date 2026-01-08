"""Script to demonstrate DomainModelerAgent and show generated artifacts."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from app.agents.impl_design import DomainModelerAgent

# Create a test contract with both relational and document entities
contract = {
    "source_repo_url": "https://github.com/test/repo",
    "framework": {"name": "vite", "versionHint": "^6.0.0"},
    "envVars": [],
    "apiClientFiles": [],
    "entities": [
        {
            "name": "UserLink",
            "sourcePath": "src/Entities/UserLink.json",
            "fields": [
                {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                {"name": "user_id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                {"name": "target_id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                {"name": "created_at", "type": "datetime", "required": True, "nullable": False, "raw": {"type": "datetime"}}
            ],
            "relationships": [],
            "rawShapeHint": "fields-array"
        },
        {
            "name": "Recipe",
            "sourcePath": "src/Entities/Recipe.json",
            "fields": [
                {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                {"name": "title", "type": "string", "required": True, "nullable": False, "raw": {"type": "string", "description": "Recipe title"}},
                {"name": "rating", "type": "number", "required": False, "nullable": False, "raw": {"type": "number", "minimum": 0, "maximum": 5}},
                {
                    "name": "ingredients",
                    "type": "array",
                    "required": False,
                    "nullable": False,
                    "raw": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "quantity": {"type": "number"},
                                "unit": {"type": "string"}
                            }
                        }
                    }
                },
                {
                    "name": "metadata",
                    "type": "object",
                    "required": False,
                    "nullable": False,
                    "raw": {
                        "type": "object",
                        "properties": {
                            "author": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}}
                        },
                        "additionalProperties": True
                    }
                }
            ],
            "relationships": [],
            "rawShapeHint": "fields-array"
        }
    ],
    "entityDetection": {"directoriesFound": [], "filesParsed": 2, "filesFailed": []},
    "endpointsUsed": [],
    "notes": []
}

with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    workspace_root = temp_path / "test_workspace"
    workspace_root.mkdir()
    
    artifacts_dir = workspace_root / "workspace"
    artifacts_dir.mkdir(parents=True)
    source_dir = workspace_root / "source"
    source_dir.mkdir(parents=True)
    
    # Write contract
    contract_path = artifacts_dir / "ui-contract.json"
    contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
    
    # Create mock job with hybrid db_stack
    mock_job = MagicMock()
    mock_job.db_stack = "hybrid"
    mock_job.artifacts = {}
    mock_job.id = "demo-job-id"
    
    class MockWorkspace:
        def __init__(self, root, source_dir, artifacts_dir):
            self.root = root
            self.source_dir = source_dir
            self.artifacts_dir = artifacts_dir
    
    mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)
    
    # Run the agent
    print("=" * 60)
    print("Running DomainModelerAgent...")
    print("=" * 60)
    agent = DomainModelerAgent()
    result = agent.run(mock_job, mock_ws)
    
    if not result.ok:
        print(f"ERROR: {result.message}")
        exit(1)
    
    print(f"\nAgent completed successfully: {result.message}\n")
    
    # Display storage-plan.json
    storage_plan_path = artifacts_dir / "storage-plan.json"
    if storage_plan_path.exists():
        print("=" * 60)
        print("storage-plan.json (first 30 lines)")
        print("=" * 60)
        with open(storage_plan_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[:30]
            for line in lines:
                print(line, end="")
        print("\n...\n")
    
    # Display db-schema.sql (top)
    db_schema_sql_path = artifacts_dir / "db-schema.sql"
    if db_schema_sql_path.exists():
        print("=" * 60)
        print("db-schema.sql (top 40 lines)")
        print("=" * 60)
        with open(db_schema_sql_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[:40]
            for line in lines:
                print(line, end="")
        print("\n...\n")
    
    # Display mongo-schemas.json (top)
    mongo_schemas_path = artifacts_dir / "mongo-schemas.json"
    if mongo_schemas_path.exists():
        print("=" * 60)
        print("mongo-schemas.json (first 50 lines)")
        print("=" * 60)
        with open(mongo_schemas_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[:50]
            for line in lines:
                print(line, end="")
        print("\n...\n")

