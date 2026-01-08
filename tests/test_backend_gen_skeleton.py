"""Tests for backend generation skeleton."""
import json
import tempfile
from pathlib import Path
from app.generators.backend_gen.generator import generate_backend


def test_backend_gen_skeleton():
    """Test that backend generator creates all expected files with correct content."""
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
                        },
                        {
                            "name": "title",
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
            "mode": "postgres",
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
        
        # Assert files were generated
        assert len(generated_files) == 8, f"Expected 8 files, got {len(generated_files)}"
        
        # Expected file paths
        expected_files = [
            "app/main.py",
            "app/api/__init__.py",
            "app/api/health.py",
            "app/core/config.py",
            "requirements.txt",
            "Dockerfile",
            "docker-compose.yml",
            "README.md",
        ]
        
        # Verify all files exist and have expected content
        for file_path in expected_files:
            full_path = out_dir / file_path
            assert full_path.exists(), f"File {file_path} was not created"
            assert full_path.is_file(), f"{file_path} is not a file"
            
            content = full_path.read_text(encoding="utf-8")
            assert len(content) > 0, f"File {file_path} is empty"
            
            # Verify no TODO notes (as per requirements)
            assert "TODO" not in content, f"File {file_path} contains TODO note"
        
        # Verify specific file contents
        main_py = (out_dir / "app/main.py").read_text(encoding="utf-8")
        assert "from fastapi import FastAPI" in main_py
        assert "app = FastAPI" in main_py
        assert "health_router" in main_py
        
        health_py = (out_dir / "app/api/health.py").read_text(encoding="utf-8")
        assert "from fastapi import APIRouter" in health_py
        assert "@router.get(\"/health\")" in health_py
        assert '{"status": "ok"}' in health_py
        
        config_py = (out_dir / "app/core/config.py").read_text(encoding="utf-8")
        assert "from pydantic_settings import BaseSettings" in config_py
        assert "class Settings" in config_py
        
        requirements_txt = (out_dir / "requirements.txt").read_text(encoding="utf-8")
        assert "fastapi" in requirements_txt
        assert "uvicorn" in requirements_txt
        
        dockerfile = (out_dir / "Dockerfile").read_text(encoding="utf-8")
        assert "FROM python:3.11-slim" in dockerfile
        assert "CMD" in dockerfile
        
        docker_compose = (out_dir / "docker-compose.yml").read_text(encoding="utf-8")
        assert "services:" in docker_compose
        assert "api:" in docker_compose
        
        readme = (out_dir / "README.md").read_text(encoding="utf-8")
        assert "# Generated Backend API" in readme
        assert "FastAPI" in readme

