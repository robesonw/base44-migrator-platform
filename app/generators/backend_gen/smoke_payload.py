"""Helper for generating minimal POST payloads for smoke testing."""
import json
from pathlib import Path
from typing import Dict, Any, Optional

SERVER_MANAGED_FIELDS = {"id", "createdAt", "created_at", "updatedAt", "updated_at", "deletedAt", "deleted_at"}


def build_minimal_payload(ui_contract_path: Path, entity_name: str) -> Dict[str, Any]:
    """
    Build a minimal POST payload for an entity based on its Create model rules.
    
    Args:
        ui_contract_path: Path to ui-contract.json file
        entity_name: Name of the entity to build payload for
        
    Returns:
        Dictionary with minimal required fields set to default values
    """
    # Load ui-contract.json
    with open(ui_contract_path, "r", encoding="utf-8") as f:
        ui_contract = json.load(f)
    
    # Find the entity
    entities = ui_contract.get("entities", [])
    entity = None
    for e in entities:
        if e.get("name") == entity_name:
            entity = e
            break
    
    if not entity:
        raise ValueError(f"Entity '{entity_name}' not found in ui-contract.json")
    
    # Build payload
    payload = {}
    fields = entity.get("fields", [])
    
    for field in fields:
        field_name = field.get("name")
        
        # Skip server-managed fields
        if field_name in SERVER_MANAGED_FIELDS:
            continue
        
        # Only include required fields
        if field.get("required", False):
            field_type = field.get("type", "string").lower()
            
            # Map field type to default value
            if field_type in ("string", "str"):
                payload[field_name] = "test"
            elif field_type in ("number", "integer", "int", "float"):
                payload[field_name] = 1
            elif field_type in ("boolean", "bool"):
                payload[field_name] = True
            elif field_type == "datetime":
                payload[field_name] = "2026-01-01T00:00:00Z"
            elif field_type == "array":
                payload[field_name] = []
            elif field_type == "object":
                payload[field_name] = {}
            else:
                # Default to string
                payload[field_name] = "test"
    
    return payload

