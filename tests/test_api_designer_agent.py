"""Tests for ApiDesignerAgent."""
import json
import tempfile
import yaml
from pathlib import Path
from unittest.mock import MagicMock
from openapi_spec_validator import validate
from openapi_spec_validator.readers import read_from_filename
from app.agents.impl_design import ApiDesignerAgent


def test_api_designer_generates_openapi_from_contract():
    """Test that ApiDesignerAgent generates valid OpenAPI 3.0.3 YAML from a contract with 2 entities."""
    # Create a temporary workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        # Create workspace structure
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        # Create a test ui-contract.json with 2 entities
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
                            "name": "rating",
                            "type": "number",
                            "required": False,
                            "nullable": False,
                            "raw": {"type": "number"}
                        }
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                },
                {
                    "name": "Ingredient",
                    "sourcePath": "src/Entities/Ingredient.json",
                    "fields": [
                        {
                            "name": "id",
                            "type": "string",
                            "required": True,
                            "nullable": False,
                            "raw": {"type": "string"}
                        },
                        {
                            "name": "name",
                            "type": "string",
                            "required": True,
                            "nullable": False,
                            "raw": {"type": "string"}
                        },
                        {
                            "name": "quantity",
                            "type": "number",
                            "required": False,
                            "nullable": False,
                            "raw": {"type": "number"}
                        }
                    ],
                    "relationships": [],
                    "rawShapeHint": "fields-array"
                }
            ],
            "entityDetection": {
                "directoriesFound": [],
                "filesParsed": 2,
                "filesFailed": []
            },
            "endpointsUsed": [],
            "notes": []
        }
        
        # Write contract
        contract_path = artifacts_dir / "ui-contract.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        
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
        agent = ApiDesignerAgent()
        result = agent.run(mock_job, mock_ws)
        
        # Assert agent succeeded
        assert result.ok, f"Agent failed: {result.message}"
        
        # Read the generated OpenAPI YAML
        openapi_path = artifacts_dir / "openapi.yaml"
        assert openapi_path.exists(), "openapi.yaml was not created"
        
        # Parse YAML
        with open(openapi_path, "r", encoding="utf-8") as f:
            openapi_spec = yaml.safe_load(f)
        
        # Validate OpenAPI version
        assert openapi_spec["openapi"] == "3.0.3", "OpenAPI version must be 3.0.3"
        
        # Validate required top-level keys
        assert "info" in openapi_spec
        assert "servers" in openapi_spec
        assert "tags" in openapi_spec
        assert "paths" in openapi_spec
        assert "components" in openapi_spec
        assert "schemas" in openapi_spec["components"]
        
        # Validate schemas contain both entities
        schemas = openapi_spec["components"]["schemas"]
        assert "Recipe" in schemas, "Recipe schema not found"
        assert "Ingredient" in schemas, "Ingredient schema not found"
        assert "RecipeCreate" in schemas, "RecipeCreate schema not found"
        assert "IngredientCreate" in schemas, "IngredientCreate schema not found"
        assert "RecipeUpdate" in schemas, "RecipeUpdate schema not found"
        assert "IngredientUpdate" in schemas, "IngredientUpdate schema not found"
        
        # Validate CRUD paths exist for Recipe
        assert "/api/recipe" in openapi_spec["paths"], "Recipe list path not found"
        assert "get" in openapi_spec["paths"]["/api/recipe"], "Recipe GET list not found"
        assert "post" in openapi_spec["paths"]["/api/recipe"], "Recipe POST create not found"
        assert "/api/recipe/{id}" in openapi_spec["paths"], "Recipe detail path not found"
        recipe_detail = openapi_spec["paths"]["/api/recipe/{id}"]
        assert "get" in recipe_detail, "Recipe GET one not found"
        assert "put" in recipe_detail, "Recipe PUT not found"
        assert "patch" in recipe_detail, "Recipe PATCH not found"
        assert "delete" in recipe_detail, "Recipe DELETE not found"
        
        # Validate CRUD paths exist for Ingredient
        assert "/api/ingredient" in openapi_spec["paths"], "Ingredient list path not found"
        assert "get" in openapi_spec["paths"]["/api/ingredient"], "Ingredient GET list not found"
        assert "post" in openapi_spec["paths"]["/api/ingredient"], "Ingredient POST create not found"
        assert "/api/ingredient/{id}" in openapi_spec["paths"], "Ingredient detail path not found"
        ingredient_detail = openapi_spec["paths"]["/api/ingredient/{id}"]
        assert "get" in ingredient_detail, "Ingredient GET one not found"
        assert "put" in ingredient_detail, "Ingredient PUT not found"
        assert "patch" in ingredient_detail, "Ingredient PATCH not found"
        assert "delete" in ingredient_detail, "Ingredient DELETE not found"
        
        # Validate using openapi-spec-validator
        spec_dict, spec_url = read_from_filename(str(openapi_path))
        validate(spec_dict)


def test_api_designer_fails_when_both_empty():
    """Test that ApiDesignerAgent fails when both entities and endpointsUsed are empty."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        workspace_root = temp_path / "test_workspace"
        workspace_root.mkdir()
        
        artifacts_dir = workspace_root / "workspace"
        artifacts_dir.mkdir(parents=True)
        source_dir = workspace_root / "source"
        source_dir.mkdir(parents=True)
        
        # Create contract with empty entities and endpointsUsed
        contract = {
            "source_repo_url": "https://github.com/test/repo",
            "framework": {"name": "vite", "versionHint": "^6.0.0"},
            "envVars": [],
            "apiClientFiles": [],
            "entities": [],
            "entityDetection": {"directoriesFound": [], "filesParsed": 0, "filesFailed": []},
            "endpointsUsed": [],
            "notes": []
        }
        
        contract_path = artifacts_dir / "ui-contract.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        
        mock_job = MagicMock()
        
        class MockWorkspace:
            def __init__(self, root, source_dir, artifacts_dir):
                self.root = root
                self.source_dir = source_dir
                self.artifacts_dir = artifacts_dir
        
        mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)
        
        agent = ApiDesignerAgent()
        result = agent.run(mock_job, mock_ws)
        
        # Should fail with clear message
        assert not result.ok, "Agent should fail when entities and endpointsUsed are empty"
        assert "entities and endpointsUsed are both empty" in result.message


def test_api_designer_handles_endpoints_used():
    """Test that ApiDesignerAgent includes endpoints from endpointsUsed."""
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
            "endpointsUsed": [
                {
                    "method": "POST",
                    "pathHint": "/api/custom/endpoint",
                    "dynamic": False,
                    "sourceLocations": ["src/api.js:10-10"],
                    "requestBodyHint": None,
                    "responseShapeHint": None
                }
            ],
            "notes": []
        }
        
        contract_path = artifacts_dir / "ui-contract.json"
        contract_path.write_text(json.dumps(contract, indent=2), encoding="utf-8")
        
        mock_job = MagicMock()
        
        class MockWorkspace:
            def __init__(self, root, source_dir, artifacts_dir):
                self.root = root
                self.source_dir = source_dir
                self.artifacts_dir = artifacts_dir
        
        mock_ws = MockWorkspace(workspace_root, source_dir, artifacts_dir)
        
        agent = ApiDesignerAgent()
        result = agent.run(mock_job, mock_ws)
        
        assert result.ok, f"Agent failed: {result.message}"
        
        openapi_path = artifacts_dir / "openapi.yaml"
        with open(openapi_path, "r", encoding="utf-8") as f:
            openapi_spec = yaml.safe_load(f)
        
        # Check that custom endpoint is included
        assert "/api/custom/endpoint" in openapi_spec["paths"]
        assert "post" in openapi_spec["paths"]["/api/custom/endpoint"]
        
        # Check that upstream tag exists
        tag_names = [tag["name"] for tag in openapi_spec["tags"]]
        assert "upstream" in tag_names

