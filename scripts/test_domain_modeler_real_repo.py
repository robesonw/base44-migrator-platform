"""Script to test DomainModelerAgent with real repository."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from git import Repo
from app.agents.impl_intake import RepoIntakeAgent
from app.agents.impl_design import DomainModelerAgent

SOURCE_REPO = "https://github.com/robesonw/culinary-compass.git"
TARGET_REPO = "https://github.com/robesonw/cc"
DB_STACK = "hybrid"  # Use hybrid to see both postgres and mongo outputs

# Create a persistent output directory
output_dir = Path(__file__).parent.parent / "test_output" / "culinary_compass_test"
output_dir.mkdir(parents=True, exist_ok=True)

workspace_root = output_dir / "workspace"
workspace_root.mkdir(exist_ok=True)

artifacts_dir = workspace_root / "workspace"
artifacts_dir.mkdir(parents=True, exist_ok=True)
source_dir = workspace_root / "source"
source_dir.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("Testing DomainModelerAgent with real repository")
print("=" * 80)
print(f"Source: {SOURCE_REPO}")
print(f"Target: {TARGET_REPO}")
print(f"DB Stack: {DB_STACK}")
print(f"Workspace: {workspace_root}")
print()

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

class MockWorkspace:
    def __init__(self, root, source_dir, artifacts_dir):
        self.root = root
        self.source_dir = source_dir
        self.artifacts_dir = artifacts_dir

mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)

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
domain_job.artifacts = {}  # No db_preferences
domain_job.id = "test-job-id"

domain_result = DomainModelerAgent().run(domain_job, mock_ws)

if not domain_result.ok:
    print(f"  ERROR: DomainModelerAgent failed: {domain_result.message}")
    exit(1)

print(f"  DomainModelerAgent completed: {domain_result.message}")
print()

# Step 4: Display outputs
print("=" * 80)
print("DOMAIN MODELER OUTPUTS")
print("=" * 80)

# Display storage-plan.json
storage_plan_path = artifacts_dir / "storage-plan.json"
if storage_plan_path.exists():
    print("\n1. storage-plan.json:")
    print("-" * 80)
    with open(storage_plan_path, "r", encoding="utf-8") as f:
        content = f.read()
        print(content)
    print()

# Display db-schema.sql (if exists)
db_schema_sql_path = artifacts_dir / "db-schema.sql"
if db_schema_sql_path.exists():
    print("\n2. db-schema.sql (first 50 lines):")
    print("-" * 80)
    with open(db_schema_sql_path, "r", encoding="utf-8") as f:
        lines = f.readlines()[:50]
        for line in lines:
            print(line, end="")
        if len(f.readlines()) > 50:
            print("\n... (truncated)")
    print()

# Display mongo-schemas.json (if exists)
mongo_schemas_path = artifacts_dir / "mongo-schemas.json"
if mongo_schemas_path.exists():
    print("\n3. mongo-schemas.json (first 60 lines):")
    print("-" * 80)
    with open(mongo_schemas_path, "r", encoding="utf-8") as f:
        lines = f.readlines()[:60]
        for line in lines:
            print(line, end="")
        if len(f.readlines()) > 60:
            print("\n... (truncated)")
    print()

# List all generated files
print("\n4. All generated files:")
print("-" * 80)
for file_path in sorted(artifacts_dir.rglob("*")):
    if file_path.is_file():
        relative_path = file_path.relative_to(artifacts_dir)
        size = file_path.stat().st_size
        print(f"  {relative_path} ({size} bytes)")

print("\n" + "=" * 80)
print(f"Workspace directory: {workspace_root}")
print("=" * 80)

