"""Unit tests for RepoIntakeAgent scanner functionality."""
import json
import pytest
from pathlib import Path
from app.agents.intake_scanner import (
    discover_entities,
    detect_framework,
    detect_env_vars,
    scan_endpoints,
    detect_api_client_files,
    EntityDetectionResult,
)

# Get the fixtures directory
TESTS_DIR = Path(__file__).parent
FIXTURE_REPO = TESTS_DIR / "fixtures" / "fake_base44_ui"


class TestEntityDiscovery:
    """Test entity discovery functionality."""
    
    def test_discover_entities_fields_array_shape(self):
        """Test parsing entities with fields-array shape."""
        result = discover_entities(FIXTURE_REPO)
        
        # Should find Recipe entity with fields-array shape
        recipe_entities = [e for e in result.entities if e.name == "Recipe"]
        assert len(recipe_entities) == 1
        
        recipe = recipe_entities[0]
        assert recipe.rawShapeHint == "fields-array"
        assert len(recipe.fields) == 4
        assert recipe.fields[0]["name"] == "id"
        assert recipe.fields[0]["type"] == "string"
        assert recipe.fields[0]["required"] is True
        assert len(recipe.relationships) == 1
        assert recipe.relationships[0]["kind"] == "one_to_many"
    
    def test_discover_entities_key_map_shape(self):
        """Test parsing entities with key-map shape."""
        result = discover_entities(FIXTURE_REPO)
        
        # Should find Ingredient entity with key-map shape
        ingredient_entities = [e for e in result.entities if e.name == "Ingredient"]
        assert len(ingredient_entities) == 1
        
        ingredient = ingredient_entities[0]
        assert ingredient.rawShapeHint == "key-map"
        assert len(ingredient.fields) == 4
        assert any(f["name"] == "id" for f in ingredient.fields)
        assert any(f["name"] == "name" for f in ingredient.fields)
    
    def test_discover_entities_embedded_schema_shape(self):
        """Test parsing entities with embedded-schema shape."""
        result = discover_entities(FIXTURE_REPO)
        
        # Should find User entity with embedded-schema shape
        user_entities = [e for e in result.entities if e.name == "User"]
        assert len(user_entities) == 1
        
        user = user_entities[0]
        assert user.rawShapeHint == "embedded-schema"
        assert len(user.fields) >= 3
        assert any(f["name"] == "id" for f in user.fields)
        assert any(f["name"] == "email" for f in user.fields)
    
    def test_discover_entities_json_schema_shape(self):
        """Test parsing entities with json-schema shape."""
        result = discover_entities(FIXTURE_REPO)
        
        # Should find Product entity with json-schema shape
        product_entities = [e for e in result.entities if e.name == "Product"]
        assert len(product_entities) == 1
        
        product = product_entities[0]
        assert product.rawShapeHint == "json-schema"
        assert len(product.fields) == 3
        # Check required fields
        id_field = next(f for f in product.fields if f["name"] == "id")
        assert id_field["required"] is True
        name_field = next(f for f in product.fields if f["name"] == "name")
        assert name_field["required"] is True
    
    def test_entity_detection_metadata(self):
        """Test entityDetection metadata is correct."""
        result = discover_entities(FIXTURE_REPO)
        
        assert "src/Entities" in result.directoriesFound or "src/entities" in result.directoriesFound
        assert result.filesParsed >= 3  # At least Recipe, Ingredient, User
        assert isinstance(result.filesFailed, list)
    
    def test_entity_source_paths(self):
        """Test that entity source paths are relative to source_dir."""
        result = discover_entities(FIXTURE_REPO)
        
        for entity in result.entities:
            assert not Path(entity.sourcePath).is_absolute()
            assert entity.sourcePath.endswith(".json")


class TestFrameworkDetection:
    """Test framework detection functionality."""
    
    def test_detect_nextjs_framework(self):
        """Test detection of Next.js framework."""
        framework = detect_framework(FIXTURE_REPO)
        
        assert framework["name"] == "nextjs"
        assert "versionHint" in framework


class TestEnvVarDetection:
    """Test environment variable detection."""
    
    def test_detect_env_vars(self):
        """Test detection of NEXT_PUBLIC_* and VITE_* environment variables."""
        env_vars = detect_env_vars(FIXTURE_REPO)
        
        # Should find NEXT_PUBLIC_API_URL
        next_pub_vars = [v for v in env_vars if v["name"] == "NEXT_PUBLIC_API_URL"]
        assert len(next_pub_vars) >= 1
        
        # Should find VITE_API_BASE
        vite_vars = [v for v in env_vars if v["name"] == "VITE_API_BASE"]
        assert len(vite_vars) >= 1
        
        # Check sourceLocations format
        for env_var in env_vars:
            assert "name" in env_var
            assert "sourceLocations" in env_var
            assert isinstance(env_var["sourceLocations"], list)
            for loc in env_var["sourceLocations"]:
                assert ":" in loc  # Should be file:line format


class TestEndpointScanning:
    """Test endpoint usage scanning."""
    
    def test_scan_fetch_literal_endpoint(self):
        """Test scanning fetch() calls with literal strings."""
        endpoints = scan_endpoints(FIXTURE_REPO)
        
        # Should find fetch calls
        fetch_endpoints = [e for e in endpoints if e["method"] == "GET"]
        assert len(fetch_endpoints) >= 1
        
        # Check for literal pathHint
        literal_endpoints = [e for e in fetch_endpoints if not e["dynamic"]]
        assert len(literal_endpoints) >= 1
    
    def test_scan_fetch_template_string_endpoint(self):
        """Test scanning fetch() calls with template strings (dynamic)."""
        endpoints = scan_endpoints(FIXTURE_REPO)
        
        # Should find dynamic endpoints
        dynamic_endpoints = [e for e in endpoints if e["dynamic"]]
        assert len(dynamic_endpoints) >= 1
    
    def test_scan_axios_method_calls(self):
        """Test scanning axios.get/post/put/delete() calls."""
        endpoints = scan_endpoints(FIXTURE_REPO)
        
        # Should find axios method calls - check for GET, PUT methods from our fixtures
        get_endpoints = [e for e in endpoints if e["method"] == "GET" and "/recipes" in e.get("pathHint", "")]
        put_endpoints = [e for e in endpoints if e["method"] == "PUT"]
        
        assert len(get_endpoints) >= 1
        assert len(put_endpoints) >= 1
    
    def test_scan_axios_config_object(self):
        """Test scanning axios({...}) config object form."""
        endpoints = scan_endpoints(FIXTURE_REPO)
        
        # Should find DELETE method from axios config object
        delete_endpoints = [e for e in endpoints if e["method"] == "DELETE"]
        assert len(delete_endpoints) >= 1
    
    def test_endpoint_structure(self):
        """Test that endpoints have correct structure."""
        endpoints = scan_endpoints(FIXTURE_REPO)
        
        assert len(endpoints) >= 3  # At least fetch literal, fetch template, axios calls
        
        for endpoint in endpoints:
            assert "method" in endpoint
            assert "pathHint" in endpoint
            assert "dynamic" in endpoint
            assert isinstance(endpoint["dynamic"], bool)
            assert "sourceLocations" in endpoint
            assert isinstance(endpoint["sourceLocations"], list)
            for loc in endpoint["sourceLocations"]:
                assert ":" in loc  # Should be file:lineStart-lineEnd format


class TestApiClientFiles:
    """Test API client file detection."""
    
    def test_detect_api_client_files(self):
        """Test detection of common API client wrapper files."""
        api_files = detect_api_client_files(FIXTURE_REPO)
        
        # Should find src/lib/api.ts
        assert any("src/lib/api.ts" in f for f in api_files)
        assert len(api_files) >= 1
        
        # Check paths are relative
        for file_path in api_files:
            assert not Path(file_path).is_absolute()


class TestIntegration:
    """Integration tests for full contract generation."""
    
    def test_full_scan_integration(self):
        """Test that all components work together."""
        # Entity discovery
        entity_result = discover_entities(FIXTURE_REPO)
        assert len(entity_result.entities) >= 4  # Recipe, Ingredient, User, Product
        
        # Framework detection
        framework = detect_framework(FIXTURE_REPO)
        assert framework["name"] == "nextjs"
        
        # Env vars
        env_vars = detect_env_vars(FIXTURE_REPO)
        assert len(env_vars) >= 2
        
        # Endpoints
        endpoints = scan_endpoints(FIXTURE_REPO)
        assert len(endpoints) >= 3
        
        # API client files
        api_files = detect_api_client_files(FIXTURE_REPO)
        assert len(api_files) >= 1

