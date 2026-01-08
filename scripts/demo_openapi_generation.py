"""Demo script to generate and show OpenAPI YAML output."""
import json
import tempfile
import yaml
from pathlib import Path
from unittest.mock import MagicMock
from app.agents.impl_design import ApiDesignerAgent

# Create a test contract with FavoriteMeal and another entity
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
                    "raw": {"type": "string", "description": "Name of the meal"}
                },
                {
                    "name": "meal_type",
                    "type": "string",
                    "required": True,
                    "nullable": False,
                    "raw": {
                        "type": "string",
                        "enum": ["breakfast", "lunch", "dinner", "snacks"],
                        "description": "Type of meal"
                    }
                },
                {
                    "name": "calories",
                    "type": "string",
                    "required": False,
                    "nullable": False,
                    "raw": {"type": "string", "description": "Calorie information"}
                },
                {
                    "name": "protein",
                    "type": "number",
                    "required": False,
                    "nullable": False,
                    "raw": {"type": "number", "description": "Protein in grams"}
                },
                {
                    "name": "createdAt",
                    "type": "datetime",
                    "required": True,
                    "nullable": False,
                    "raw": {"type": "datetime"}
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
                    "name": "rating",
                    "type": "number",
                    "required": False,
                    "nullable": False,
                    "raw": {"type": "number", "minimum": 0, "maximum": 5}
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

# Create temporary workspace
with tempfile.TemporaryDirectory() as temp_dir:
    temp_path = Path(temp_dir)
    workspace_root = temp_path / "demo_workspace"
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
    
    if not result.ok:
        print(f"ERROR: {result.message}")
        exit(1)
    
    # Read and display the generated OpenAPI YAML
    openapi_path = artifacts_dir / "openapi.yaml"
    with open(openapi_path, "r", encoding="utf-8") as f:
        openapi_spec = yaml.safe_load(f)
    
    print("=" * 80)
    print("TOP OF GENERATED openapi.yaml")
    print("=" * 80)
    with open(openapi_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        # Show first 30 lines
        for i, line in enumerate(lines[:30], 1):
            print(f"{i:3}: {line}", end="")
    print("\n")
    
    print("=" * 80)
    print("EXAMPLE ENTITY SCHEMA: FavoriteMeal")
    print("=" * 80)
    favorite_meal_schema = openapi_spec["components"]["schemas"]["FavoriteMeal"]
    print(yaml.dump({"FavoriteMeal": favorite_meal_schema}, default_flow_style=False, sort_keys=False))
    
    print("=" * 80)
    print("EXAMPLE CREATE SCHEMA: FavoriteMealCreate (server-managed fields excluded)")
    print("=" * 80)
    favorite_meal_create_schema = openapi_spec["components"]["schemas"]["FavoriteMealCreate"]
    print(yaml.dump({"FavoriteMealCreate": favorite_meal_create_schema}, default_flow_style=False, sort_keys=False))
    
    print("=" * 80)
    print("EXAMPLE UPDATE SCHEMA: FavoriteMealUpdate (all fields optional)")
    print("=" * 80)
    favorite_meal_update_schema = openapi_spec["components"]["schemas"]["FavoriteMealUpdate"]
    print(yaml.dump({"FavoriteMealUpdate": favorite_meal_update_schema}, default_flow_style=False, sort_keys=False))
    
    print("=" * 80)
    print("GENERATED PATHS FOR FavoriteMeal")
    print("=" * 80)
    favorite_meal_paths = {
        "/api/favorite-meal": openapi_spec["paths"]["/api/favorite-meal"],
        "/api/favorite-meal/{id}": openapi_spec["paths"]["/api/favorite-meal/{id}"]
    }
    print(yaml.dump(favorite_meal_paths, default_flow_style=False, sort_keys=False))
    
    print("=" * 80)
    print("GENERATED PATHS FOR Recipe")
    print("=" * 80)
    recipe_paths = {
        "/api/recipe": openapi_spec["paths"]["/api/recipe"],
        "/api/recipe/{id}": openapi_spec["paths"]["/api/recipe/{id}"]
    }
    print(yaml.dump(recipe_paths, default_flow_style=False, sort_keys=False))
    
    print("=" * 80)
    print("SUMMARY: All Paths Generated")
    print("=" * 80)
    for path in sorted(openapi_spec["paths"].keys()):
        methods = list(openapi_spec["paths"][path].keys())
        print(f"  {path}: {', '.join(methods)}")

