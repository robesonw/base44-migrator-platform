"""Tests for DomainModelerAgent."""
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from app.agents.impl_design import DomainModelerAgent


def test_domain_modeler_postgres_classification():
    """Test that DomainModelerAgent classifies relational entity as postgres."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        # Create contract with relational entity (only primitives)
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
                        {
                            "name": "id",
                            "type": "string",
                            "required": True,
                            "nullable": False,
                            "raw": {"type": "string"}
                        },
                        {
                            "name": "user_id",
                            "type": "string",
                            "required": True,
                            "nullable": False,
                            "raw": {"type": "string"}
                        },
                        {
                            "name": "target_id",
                            "type": "string",
                            "required": True,
                            "nullable": False,
                            "raw": {"type": "string"}
                        },
                        {
                            "name": "created_at",
                            "type": "datetime",
                            "required": True,
                            "nullable": False,
                            "raw": {"type": "datetime"}
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
        mock_job.artifacts = {}
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
        assert storage_plan["entities"][0]["name"] == "UserLink"
        assert storage_plan["entities"][0]["store"] == "postgres"
        reason_lower = storage_plan["entities"][0]["reason"].lower()
        assert "postgres" in reason_lower or "relational" in reason_lower or "primitive" in reason_lower
        
        # Check db-schema.md exists
        db_schema_path = artifacts_dir / "db-schema.md"
        assert db_schema_path.exists(), "db-schema.md was not created"
        
        # Check Postgres SQL exists (should have postgres entities)
        db_schema_sql_path = artifacts_dir / "db-schema.sql"
        assert db_schema_sql_path.exists(), "db-schema.sql was not created"
        
        # Check SQL contains UserLink table
        sql_content = db_schema_sql_path.read_text(encoding="utf-8")
        assert "user_link" in sql_content.lower()
        assert "CREATE TABLE" in sql_content
        
        # Check models_postgres.py exists
        models_pg_path = artifacts_dir / "models_postgres.py"
        assert models_pg_path.exists(), "models_postgres.py was not created"
        
        # Check migration exists
        migrations_dir = artifacts_dir / "migrations"
        assert migrations_dir.exists(), "migrations directory was not created"
        migration_files = list(migrations_dir.glob("*.py"))
        assert len(migration_files) > 0, "Alembic migration was not created"


def test_domain_modeler_mongo_classification():
    """Test that DomainModelerAgent classifies document entity as mongo."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        # Create contract with document entity (nested object/array of objects)
        contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
            "envVars": [],
            "apiClientFiles": [],
            "entities": [
                {
                    "name": "Recipe",
                    "sourcePath": "src/Entities/Recipe.json",
                    "fields": [
                        {
                            "name": "id",
                            "type": "string",
                            "required": True,
                            "nullable": False,
                            "raw": {"type": "string"}
                        },
                        {
                            "name": "title",
                            "type": "string",
                            "required": True,
                            "nullable": False,
                            "raw": {"type": "string", "description": "Recipe title"}
                        },
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
            "entityDetection": {"directoriesFound": [], "filesParsed": 1, "filesFailed": []},
            "endpointsUsed": [],
            "notes": []
        }
        
        contract_path = artifacts_dir / "ui-contract.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        
        mock_job = MagicMock()
        mock_job.db_stack = "hybrid"
        mock_job.artifacts = {}
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
        assert storage_plan["entities"][0]["name"] == "Recipe"
        assert storage_plan["entities"][0]["store"] == "mongo"
        reason_lower = storage_plan["entities"][0]["reason"].lower()
        assert "mongo" in reason_lower or "complex" in reason_lower or "array" in reason_lower or "object" in reason_lower
        
        # Check db-schema.md exists
        db_schema_path = artifacts_dir / "db-schema.md"
        assert db_schema_path.exists(), "db-schema.md was not created"
        
        # Check Mongo artifacts exist
        mongo_collections_path = artifacts_dir / "mongo-collections.md"
        assert mongo_collections_path.exists(), "mongo-collections.md was not created"
        
        mongo_schemas_path = artifacts_dir / "mongo-schemas.json"
        assert mongo_schemas_path.exists(), "mongo-schemas.json was not created"
        
        with open(mongo_schemas_path, "r", encoding="utf-8") as f:
            mongo_schemas = json.load(f)
        
        assert "recipes" in mongo_schemas, "recipes collection schema not found"
        assert mongo_schemas["recipes"]["properties"]["_id"]["type"] == "string"
        
        # Check models_mongo.py exists
        models_mongo_path = artifacts_dir / "models_mongo.py"
        assert models_mongo_path.exists(), "models_mongo.py was not created"
        
        # Verify SQL is NOT generated for mongo entities
        db_schema_sql_path = artifacts_dir / "db-schema.sql"
        if db_schema_sql_path.exists():
            sql_content = db_schema_sql_path.read_text(encoding="utf-8")
            # Recipe should not be in SQL (it's mongo)
            assert "recipe" not in sql_content.lower(), "Mongo entity should not appear in SQL"


def test_domain_modeler_postgres_only():
    """Test DomainModelerAgent with db_stack=postgres."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
            "envVars": [],
            "apiClientFiles": [],
            "entities": [
                {
                    "name": "Product",
                    "sourcePath": "src/Entities/Product.json",
                    "fields": [
                        {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {"name": "name", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {"name": "price", "type": "number", "required": False, "nullable": False, "raw": {"type": "number"}}
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
        mock_job.db_stack = "postgres"
        mock_job.artifacts = {}
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
        
        # Check storage plan mode is postgres
        storage_plan_path = artifacts_dir / "storage-plan.json"
        with open(storage_plan_path, "r", encoding="utf-8") as f:
            storage_plan = json.load(f)
        
        assert storage_plan["mode"] == "postgres"
        assert storage_plan["entities"][0]["store"] == "postgres"
        
        # Check Postgres artifacts exist
        assert (artifacts_dir / "db-schema.sql").exists()
        assert (artifacts_dir / "models_postgres.py").exists()
        assert (artifacts_dir / "migrations").exists()
        
        # Check Mongo artifacts do NOT exist
        assert not (artifacts_dir / "mongo-collections.md").exists()
        assert not (artifacts_dir / "mongo-schemas.json").exists()
        assert not (artifacts_dir / "models_mongo.py").exists()


def test_domain_modeler_mongo_only():
    """Test DomainModelerAgent with db_stack=mongo."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
            "envVars": [],
            "apiClientFiles": [],
            "entities": [
                {
                    "name": "Document",
                    "sourcePath": "src/Entities/Document.json",
                    "fields": [
                        {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {"name": "content", "type": "object", "required": True, "nullable": False, "raw": {"type": "object", "properties": {"text": {"type": "string"}}}}
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
        mock_job.db_stack = "mongo"
        mock_job.artifacts = {}
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
        
        # Check storage plan mode is mongo
        storage_plan_path = artifacts_dir / "storage-plan.json"
        with open(storage_plan_path, "r", encoding="utf-8") as f:
            storage_plan = json.load(f)
        
        assert storage_plan["mode"] == "mongo"
        assert storage_plan["entities"][0]["store"] == "mongo"
        
        # Check Mongo artifacts exist
        assert (artifacts_dir / "mongo-collections.md").exists()
        assert (artifacts_dir / "mongo-schemas.json").exists()
        assert (artifacts_dir / "models_mongo.py").exists()
        
        # Check Postgres artifacts do NOT exist
        assert not (artifacts_dir / "db-schema.sql").exists()
        assert not (artifacts_dir / "models_postgres.py").exists()
        assert not (artifacts_dir / "migrations").exists()


def test_domain_modeler_explicit_overrides():
    """Test DomainModelerAgent with explicit db_preferences overrides."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        # Create entities - one relational, one document
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
                        {"name": "user_id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}}
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                },
                {
                    "name": "Recipe",
                    "sourcePath": "src/Entities/Recipe.json",
                    "fields": [
                        {"name": "id", "type": "string", "required": True, "nullable": False, "raw": {"type": "string"}},
                        {"name": "ingredients", "type": "array", "required": False, "nullable": False, "raw": {"type": "array", "items": {"type": "object", "properties": {}}}}
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                }
            ],
            "entityDetection": {"directoriesFound": [], "filesParsed": 2, "filesFailed": []},
            "endpointsUsed": [],
            "notes": []
        }
        
        contract_path = artifacts_dir / "ui-contract.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        
        mock_job = MagicMock()
        mock_job.db_stack = "hybrid"
        mock_job.artifacts = {
            "db_preferences": {
                "mongoEntities": ["UserLink"],  # Override: force UserLink to mongo
                "postgresEntities": ["Recipe"]  # Override: force Recipe to postgres
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
        
        # Check storage plan respects overrides
        storage_plan_path = artifacts_dir / "storage-plan.json"
        with open(storage_plan_path, "r", encoding="utf-8") as f:
            storage_plan = json.load(f)
        
        userlink_classified = next(e for e in storage_plan["entities"] if e["name"] == "UserLink")
        recipe_classified = next(e for e in storage_plan["entities"] if e["name"] == "Recipe")
        
        assert userlink_classified["store"] == "mongo", "UserLink should be mongo due to override"
        assert "explicit override" in userlink_classified["reason"].lower()
        assert recipe_classified["store"] == "postgres", "Recipe should be postgres due to override"
        assert "explicit override" in recipe_classified["reason"].lower()

