"""Script to test BackendBuilderAgent with real repository."""
import json
from pathlib import Path
from unittest.mock import MagicMock
from git import Repo
from app.agents.impl_intake import RepoIntakeAgent
from app.agents.impl_design import DomainModelerAgent, ApiDesignerAgent
from app.agents.impl_build import BackendBuilderAgent

SOURCE_REPO = "https://github.com/robesonw/culinary-compass.git"
TARGET_REPO = "https://github.com/robesonw/cc"
DB_STACK = "hybrid"  # Use hybrid to see both postgres and mongo outputs

# Create a persistent output directory
output_dir = Path(__file__).parent.parent / "test_output" / "culinary_compass_backend_test"
output_dir.mkdir(parents=True, exist_ok=True)

workspace_root = output_dir / "workspace"
workspace_root.mkdir(exist_ok=True)

artifacts_dir = workspace_root / "workspace"
artifacts_dir.mkdir(parents=True, exist_ok=True)
source_dir = workspace_root / "source"
source_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("Testing BackendBuilderAgent with real repository")
print("=" * 80)
print(f"Source: {SOURCE_REPO}")
print(f"Target: {TARGET_REPO}")
print(f"DB Stack: {DB_STACK}")
print(f"Workspace: {workspace_root}")
print()

class MockWorkspace:
    def __init__(self, root, source_dir, artifacts_dir):
        self.root = root
        self.source_dir = source_dir
        self.artifacts_dir = artifacts_dir

mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)

# Step 1: Clone source repository
print("Step 1: Cloning source repository...")
if source_dir.exists() and any(source_dir.iterdir()):
    print(f"  Source directory already exists, skipping clone")
else:
    try:
        Repo.clone_from(SOURCE_REPO, source_dir, depth=1)
        print(f"  Cloned successfully")
    except Exception as e:
        print(f"  ERROR: Failed to clone: {e}")
        exit(1)

# Step 2: Run RepoIntakeAgent to generate ui-contract.json
print("\nStep 2: Running RepoIntakeAgent to generate ui-contract.json...")
mock_job = MagicMock()
mock_job.source_repo_url = SOURCE_REPO

intake_agent = RepoIntakeAgent()
intake_result = intake_agent.run(mock_job, mock_ws)

if not intake_result.ok:
    print(f"  ERROR: Intake agent failed: {intake_result.message}")
    exit(1)

print(f"  Intake agent completed: {intake_result.message}")

# Check if ui-contract.json was created
contract_path = artifacts_dir / "ui-contract.json"
if not contract_path.exists():
    print(f"  ERROR: ui-contract.json was not created")
    exit(1)

# Load and show entity count
with open(contract_path, "r", encoding="utf-8") as f:
    contract = json.load(f)
    entities = contract.get("entities", [])
    print(f"  Found {len(entities)} entities")

# Step 3: Run DomainModelerAgent
print("\nStep 3: Running DomainModelerAgent...")
domain_job = MagicMock()
domain_job.db_stack = DB_STACK
domain_job.artifacts = {
    "db_preferences": {
        "hybridStrategy": "docToMongo"
    }
}
domain_job.id = "test-job-id"

domain_result = DomainModelerAgent().run(domain_job, mock_ws)

if not domain_result.ok:
    print(f"  ERROR: DomainModelerAgent failed: {domain_result.message}")
    exit(1)

print(f"  DomainModelerAgent completed: {domain_result.message}")

# Step 4: Run ApiDesignerAgent
print("\nStep 4: Running ApiDesignerAgent...")
api_job = MagicMock()
api_job.source_repo_url = SOURCE_REPO

api_result = ApiDesignerAgent().run(api_job, mock_ws)

if not api_result.ok:
    print(f"  ERROR: ApiDesignerAgent failed: {api_result.message}")
    exit(1)

print(f"  ApiDesignerAgent completed: {api_result.message}")

# Step 5: Run BackendBuilderAgent
print("\nStep 5: Running BackendBuilderAgent...")
backend_job = MagicMock()
backend_job.id = "test-job-id"

backend_result = BackendBuilderAgent().run(backend_job, mock_ws)

if not backend_result.ok:
    print(f"  ERROR: BackendBuilderAgent failed: {backend_result.message}")
    exit(1)

print(f"  BackendBuilderAgent completed: {backend_result.message}")
print()

# Step 6: Display outputs
print("=" * 80)
print("BACKEND GENERATION OUTPUTS")
print("=" * 80)

# Display backend directory structure
backend_dir = workspace_root / "generated" / "backend"
if backend_dir.exists():
    print(f"\nBackend directory: {backend_dir}")
    print("-" * 80)
    
    # List all generated files
    print("\nGenerated files:")
    for file_path in sorted(backend_dir.rglob("*")):
        if file_path.is_file():
            relative_path = file_path.relative_to(backend_dir)
            size = file_path.stat().st_size
            print(f"  {relative_path} ({size} bytes)")
    
    # Show content of key files
    key_files = [
        "app/main.py",
        "app/api/health.py",
        "app/core/config.py",
        "requirements.txt",
        "README.md",
    ]
    
    for key_file in key_files:
        file_path = backend_dir / key_file
        if file_path.exists():
            print(f"\n{key_file}:")
            print("-" * 80)
            content = file_path.read_text(encoding="utf-8")
            # Show first 30 lines
            lines = content.split("\n")
            for i, line in enumerate(lines[:30], 1):
                print(f"{i:3}: {line}")
            if len(lines) > 30:
                print(f"     ... ({len(lines) - 30} more lines)")
            print()
else:
    print(f"\nERROR: Backend directory not found at {backend_dir}")

print("=" * 80)
print(f"Workspace directory: {workspace_root}")
print(f"Backend directory: {backend_dir}")
print("=" * 80)

