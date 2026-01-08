"""Simple script to verify openapi.yaml file generation."""
import json
import tempfile
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
            "name": "TestEntity",
            "sourcePath": "src/Entities/TestEntity.json",
            "fields": [
                {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                {"name": "name", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}}
            ],
            "relationships": [],
            "rawShapeHint": "fields-array"
        }
    ],
    "entityDetection": {"directoriesFound": [], "filesParsed": 1, "filesFailed": []},
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
    print("FILE GENERATION TEST")
    print("=" * 60)
    print(f"Agent result OK: {result.ok}")
    print(f"Agent message: {result.message}")
    print(f"openapi.yaml exists: {openapi_path.exists()}")
    
    if openapi_path.exists():
        file_size = openapi_path.stat().st_size
        print(f"openapi.yaml size: {file_size} bytes")
        print(f"openapi.yaml path: {openapi_path}")
        print("\nSUCCESS: openapi.yaml file was generated!")
        
        # Show first few lines
        with open(openapi_path, "r", encoding="utf-8") as f:
            lines = f.readlines()[:10]
            print("\nFirst 10 lines of generated file:")
            for i, line in enumerate(lines, 1):
                print(f"  {i:2}: {line}", end="")
    else:
        print("\nFAILURE: openapi.yaml file was NOT generated!")
        exit(1)

