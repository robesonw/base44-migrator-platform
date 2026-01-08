"""Test that optional fields in Create and Update models have = None defaults."""
import json
import tempfile
from pathlib import Path
from app.generators.backend_gen.generator import generate_backend
from app.generators.backend_gen.render_entity import render_entity_model


def test_create_update_models_have_optional_defaults():
    """Test that optional fields in Create and Update models include = None default."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Create a test entity with both required and optional fields
        ui_contract = {
            "entities": [
                {
                    "name": "TestEntity",
                    "sourcePath": "test/path",
                    "fields": [
                        {"name": "required_string", "type": "string", "required": True, "nullable": False},
                        {"name": "optional_string", "type": "string", "required": False, "nullable": False},
                        {"name": "required_number", "type": "number", "required": True, "nullable": False},
                        {"name": "optional_number", "type": "number", "required": False, "nullable": False},
                        {"name": "optional_bool", "type": "boolean", "required": False, "nullable": False},
                    ],
                    "relationships": []
                }
            ]
        }
        
        # Generate the model
        model_content = render_entity_model("TestEntity", ui_contract["entities"][0]["fields"])
        
        # Check Create model
        create_start = model_content.find("class TestEntityCreate(BaseModel):")
        create_end = model_content.find("class TestEntityUpdate", create_start)
        create_section = model_content[create_start:create_end] if create_end != -1 else model_content[create_start:]
        
        # Assert required fields don't have = None
        assert "required_string: str" in create_section, "Required string field should not have = None"
        assert "required_string: Optional" not in create_section, "Required string field should not be Optional"
        assert "required_number: float" in create_section, "Required number field should not have = None"
        
        # Assert optional fields have = None
        assert "optional_string: Optional[str] = None" in create_section, "Optional string field should have = None default"
        assert "optional_number: Optional[float] = None" in create_section, "Optional number field should have = None default"
        assert "optional_bool: Optional[bool] = None" in create_section, "Optional boolean field should have = None default"
        
        # Check Update model (all fields should have = None)
        update_start = model_content.find("class TestEntityUpdate(BaseModel):")
        update_end = model_content.find("class TestEntityOut", update_start)
        update_section = model_content[update_start:update_end] if update_end != -1 else model_content[update_start:]
        
        # All non-server-managed fields in Update should have = None
        assert "required_string: Optional[str] = None" in update_section, "Required field in Update should have = None"
        assert "optional_string: Optional[str] = None" in update_section, "Optional field in Update should have = None"
        assert "required_number: Optional[float] = None" in update_section, "Required number field in Update should have = None"

