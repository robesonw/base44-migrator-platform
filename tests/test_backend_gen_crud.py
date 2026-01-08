"""Tests for backend generation CRUD routers and repositories."""
import json
import tempfile
from pathlib import Path
from app.generators.backend_gen.generator import generate_backend


def test_backend_gen_crud():
    """Test that backend generator creates CRUD routers and repositories."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create test workspace structure
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        
        # Create test ui-contract.json with two entities:
        # - UserLink (postgres - simple primitive fields)
        # - Recipe (mongo - has object/array/additionalProperties)
        ui_contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
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
                        }
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                },
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
                                        "quantity": {"type": "number"}
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
            "envVars": [],
            "apiClientFiles": [],
            "notes": []
        }
        
        ui_contract_path = artifacts_dir / "ui-contract.json"
        ui_contract_path.write_text(json.dumps(ui_contract, indent=2), encoding="utf-8")
        
        # Create test storage-plan.json marking stores accordingly
        storage_plan = {
            "mode": "hybrid",
            "entities": [
                {
                    "name": "UserLink",
                    "store": "postgres",
                    "reason": "entity has only primitive fields"
                },
                {
                    "name": "Recipe",
                    "store": "mongo",
                    "reason": "field 'ingredients' is array of objects"
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
        
        # Assert router files exist for both entities
        user_link_router_path = out_dir / "app/api/entities/user_link.py"
        recipe_router_path = out_dir / "app/api/entities/recipe.py"
        
        assert user_link_router_path.exists(), "UserLink router file was not created"
        assert recipe_router_path.exists(), "Recipe router file was not created"
        
        # Assert router code includes correct /api/{slug} paths (via prefix in main.py)
        user_link_router_content = user_link_router_path.read_text(encoding="utf-8")
        recipe_router_content = recipe_router_path.read_text(encoding="utf-8")
        
        # Router should have list endpoint (empty path becomes /api/{slug} with prefix)
        assert '@router.get' in user_link_router_content and 'response_model=dict' in user_link_router_content
        assert '@router.get' in recipe_router_content and 'response_model=dict' in recipe_router_content
        
        # Router should select correct repo class based on store
        assert "PostgresRepo" in user_link_router_content, "UserLink router should use PostgresRepo"
        assert "from app.repos.postgres_repo import PostgresRepo" in user_link_router_content
        assert "MongoRepo" in recipe_router_content, "Recipe router should use MongoRepo"
        assert "from app.repos.mongo_repo import MongoRepo" in recipe_router_content
        
        # Assert models generated for both entities
        user_link_model_path = out_dir / "app/models/user_link.py"
        recipe_model_path = out_dir / "app/models/recipe.py"
        
        assert user_link_model_path.exists(), "UserLink model file was not created"
        assert recipe_model_path.exists(), "Recipe model file was not created"
        
        user_link_model_content = user_link_model_path.read_text(encoding="utf-8")
        recipe_model_content = recipe_model_path.read_text(encoding="utf-8")
        
        # Assert models have expected classes
        assert "class UserLinkBase" in user_link_model_content
        assert "class UserLinkCreate" in user_link_model_content
        assert "class UserLinkUpdate" in user_link_model_content
        assert "class UserLinkOut" in user_link_model_content
        
        assert "class RecipeBase" in recipe_model_content
        assert "class RecipeCreate" in recipe_model_content
        assert "class RecipeUpdate" in recipe_model_content
        assert "class RecipeOut" in recipe_model_content
        
        # Assert repository base files exist
        repos_base_path = out_dir / "app/repos/base.py"
        repos_postgres_path = out_dir / "app/repos/postgres_repo.py"
        repos_mongo_path = out_dir / "app/repos/mongo_repo.py"
        
        assert repos_base_path.exists(), "repos/base.py was not created"
        assert repos_postgres_path.exists(), "repos/postgres_repo.py was not created"
        assert repos_mongo_path.exists(), "repos/mongo_repo.py was not created"
        
        # Assert main.py includes entity routers
        main_py_path = out_dir / "app/main.py"
        assert main_py_path.exists(), "app/main.py was not created"
        main_py_content = main_py_path.read_text(encoding="utf-8")
        
        assert "from app.api.entities.user_link import router as user_link_router" in main_py_content
        assert "from app.api.entities.recipe import router as recipe_router" in main_py_content
        assert 'app.include_router(user_link_router' in main_py_content
        assert 'app.include_router(recipe_router' in main_py_content

