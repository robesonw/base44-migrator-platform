"""Tests for backend generation database plumbing."""
import json
import tempfile
from pathlib import Path
from app.generators.backend_gen.generator import generate_backend


def test_backend_gen_db_plumbing():
    """Test that backend generator creates database plumbing files with correct configuration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test workspace structure
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        
        # Create test ui-contract.json
        ui_contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
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
                        }
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                }
            ],
            "entityDetection": {"directoriesFound": [], "filesParsed": 1, "filesFailed": []},
            "endpointsUsed": [],
            "envVars": [],
            "apiClientFiles": [],
            "notes": []
        }
        
        ui_contract_path = artifacts_dir / "ui-contract.json"
        ui_contract_path.write_text(json.dumps(ui_contract, indent=2), encoding="utf-8")
        
        # Create test storage-plan.json
        storage_plan = {
            "mode": "hybrid",
            "entities": [
                {
                    "name": "Recipe",
                    "store": "postgres",
                    "reason": "entity has only primitive fields"
                }
            ]
        }
        
        storage_plan_path = artifacts_dir / "storage-plan.json"
        storage_plan_path.write_text(json.dumps(storage_plan, indent=2), encoding="utf-8")
        
        # Set output directory
        out_dir = workspace_root / "generated" / "backend"
        
        # Generate backend
        job_id = "test-job-123"
        generated_files = generate_backend(
            job_id=job_id,
            ui_contract_path=ui_contract_path,
            storage_plan_path=storage_plan_path,
            out_dir=out_dir,
        )
        
        # Verify config.py contains POSTGRES_URL and MONGO_URL references
        config_path = out_dir / "app/core/config.py"
        assert config_path.exists(), "config.py was not created"
        config_content = config_path.read_text(encoding="utf-8")
        
        # Check for environment variable fields (postgres_url, mongo_url, mongo_db)
        assert "postgres_url" in config_content, "POSTGRES_URL not found in config.py"
        assert "mongo_url" in config_content, "MONGO_URL not found in config.py"
        assert "mongo_db" in config_content, "MONGO_DB not found in config.py"
        
        # Verify docker-compose.yml includes both postgres and mongo services
        docker_compose_path = out_dir / "docker-compose.yml"
        assert docker_compose_path.exists(), "docker-compose.yml was not created"
        docker_compose_content = docker_compose_path.read_text(encoding="utf-8")
        
        assert "postgres:" in docker_compose_content, "postgres service not found in docker-compose.yml"
        assert "mongo:" in docker_compose_content, "mongo service not found in docker-compose.yml"
        assert "healthcheck:" in docker_compose_content, "healthcheck not found in docker-compose.yml"
        assert "pg_isready" in docker_compose_content, "postgres healthcheck not found"
        assert "mongosh" in docker_compose_content or "mongo" in docker_compose_content, "mongo healthcheck not found"
        
        # Verify database files exist
        postgres_path = out_dir / "app/db/postgres.py"
        assert postgres_path.exists(), "app/db/postgres.py was not created"
        postgres_content = postgres_path.read_text(encoding="utf-8")
        assert "create_async_engine" in postgres_content
        assert "AsyncSession" in postgres_content
        
        mongo_path = out_dir / "app/db/mongo.py"
        assert mongo_path.exists(), "app/db/mongo.py was not created"
        mongo_content = mongo_path.read_text(encoding="utf-8")
        assert "AsyncIOMotorClient" in mongo_content
        assert "get_collection" in mongo_content
        
        # Verify requirements.txt includes database dependencies
        requirements_path = out_dir / "requirements.txt"
        assert requirements_path.exists(), "requirements.txt was not created"
        requirements_content = requirements_path.read_text(encoding="utf-8")
        assert "sqlalchemy[asyncio]" in requirements_content or "sqlalchemy" in requirements_content
        assert "asyncpg" in requirements_content
        assert "motor" in requirements_content


