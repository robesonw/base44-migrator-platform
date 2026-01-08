"""Script to generate openapi.yaml and save it to a persistent location for inspection."""
import json
import yaml
from pathlib import Path
from unittest.mock import MagicMock
from app.agents.impl_design import ApiDesignerAgent

# Simple test contract
contract = {
    "source_repo_url": "https://github.com/test/repo",
    "framework": {"name": "vite", "versionHint": "^6.0.0"},
    "envVars": [],
    "apiClientFiles": [],
    "entities": [
        {
            "name": "FavoriteMeal",
            "sourcePath": "src/Entities/FavoriteMeal.json",
            "fields": [
                {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                {"name": "name", "type": "string", "required": True, "nullable": False, "raw": {"type": "string", "description": "Name of the meal"}},
                {"name": "meal_type", "type": "string", "required": True, "nullable": False, "raw": {"type": "string", "enum": ["breakfast", "lunch", "dinner", "snacks"]}},
                {"name": "createdAt", "type": "datetime", "required": True, "nullable": False, "raw": {"type": "datetime"}}
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
                {"name": "rating", "type": "number", "required": False, "nullable": False, "raw": {"type": "number", "minimum": 0, "maximum": 5}}
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

workspace_root = output_dir / "test_workspace"
workspace_root.mkdir(exist_ok=True)

artifacts_dir = workspace_root / "workspace"
artifacts_dir.mkdir(parents=True, exist_ok=True)
source_dir = workspace_root / "source"
source_dir.mkdir(parents=True, exist_ok=True)

# Write contract
contract_path = artifacts_dir / "ui-contract.json"
contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")

# Create mock job and workspace
mock_job = MagicMock()
mock_job.source_repo_url = "https://github.com/test/repo"

class MockWorkspace:
    def __init__(self, root, source_dir, artifacts_dir):
        self.root = root
        self.source_dir = source_dir
        self.artifacts_dir = artifacts_dir

mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)

# Run the agent
agent = ApiDesignerAgent()
result = agent.run(mock_job, mock_ws)

# Verify file generation
openapi_path = artifacts_dir / "openapi.yaml"

print("=" * 60)
print("OPENAPI.YAML GENERATION")
print("=" * 60)
print(f"Agent result OK: {result.ok}")
print(f"Agent message: {result.message}")
print(f"\nGenerated file location:")
print(f"  {openapi_path}")
print(f"  (Absolute: {openapi_path.absolute()})")
print(f"\nFile exists: {openapi_path.exists()}")
if openapi_path.exists():
    file_size = openapi_path.stat().st_size
    print(f"File size: {file_size} bytes")
    print("\nSUCCESS: openapi.yaml file was generated!")
    print(f"\nYou can view it at: {openapi_path.absolute()}")

