"""Script to demonstrate DomainModelerAgent and save artifacts to a persistent location."""
import json
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

# Use a persistent directory in the project
output_dir = Path(__file__).parent.parent / "test_output"
output_dir.mkdir(exist_ok=True)

workspace_root = output_dir / "test_workspace_domain_modeler"
workspace_root.mkdir(exist_ok=True)

artifacts_dir = workspace_root / "workspace"
artifacts_dir.mkdir(parents=True, exist_ok=True)
source_dir = workspace_root / "source"
source_dir.mkdir(parents=True, exist_ok=True)

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
print("=" * 60)
print("Files saved to:")
print("=" * 60)
print(f"Workspace directory: {workspace_root}")
print(f"Artifacts directory: {artifacts_dir}\n")

# List generated files
print("Generated files:")
for file_path in sorted(artifacts_dir.rglob("*")):
    if file_path.is_file():
        relative_path = file_path.relative_to(artifacts_dir)
        size = file_path.stat().st_size
        print(f"  - {relative_path} ({size} bytes)")

print("\nKey files:")
print(f"  1. storage-plan.json: {artifacts_dir / 'storage-plan.json'}")
print(f"  2. db-schema.sql: {artifacts_dir / 'db-schema.sql'}")
print(f"  3. mongo-schemas.json: {artifacts_dir / 'mongo-schemas.json'}")

