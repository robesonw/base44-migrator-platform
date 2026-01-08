"""Integration test for RepoIntakeAgent."""
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from app.agents.impl_intake import RepoIntakeAgent

# Get the fixtures directory
TESTS_DIR = Path(__file__).parent
FIXTURE_REPO = TESTS_DIR / "fixtures" / "fake_base44_ui"


def test_repo_intake_agent_integration():
    """Test RepoIntakeAgent generates ui-contract.json with real scanning."""
    # Create a temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        # Create workspace structure
        source_dir = workspace_root / "source"
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        
        # Copy fixture repo to source_dir
        shutil.copytree(FIXTURE_REPO, source_dir, dirs_exist_ok=True)
        
        # Create mock job
        mock_job = MagicMock()
        mock_job.source_repo_url = "https://github.com/test/repo"
        
        # Create a simple mock workspace object
        class MockWorkspace:
            def __init__(self, root, source_dir, artifacts_dir):
                self.root = root
                self.source_dir = source_dir
                self.artifacts_dir = artifacts_dir
        
        mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)
        
        # Run the agent
        agent = RepoIntakeAgent()
        result = agent.run(mock_job, mock_ws)
        
        # Assert agent succeeded
        assert result.ok, f"Agent failed: {result.message}"
        
        # Read the generated contract
        contract_path = artifacts_dir / "ui-contract.json"
        assert contract_path.exists(), "ui-contract.json was not created"
        
        contract = json.loads(contract_path.read_text())
        
        # Assert contract has all required fields
        assert "source_repo_url" in contract
        assert "framework" in contract
        assert isinstance(contract["framework"], dict)
        assert "envVars" in contract
        assert "apiClientFiles" in contract
        assert "entities" in contract
        assert "entityDetection" in contract
        assert "endpointsUsed" in contract
        assert "notes" in contract
        
        # Assert at least 1 entity was found
        assert len(contract["entities"]) >= 1, "No entities found in contract"
        
        # Assert at least 1 endpoint was found
        assert len(contract["endpointsUsed"]) >= 1, "No endpoints found in contract"
        
        # Assert no placeholder notes
        notes_text = " ".join(contract.get("notes", [])).lower()
        assert "todo: implement real scanning" not in notes_text, \
            "Contract contains placeholder TODO notes"
        assert "this file should drive openapi" not in notes_text, \
            "Contract contains placeholder notes"
