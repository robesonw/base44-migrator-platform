"""Entity-specific rendering functions for backend generation."""
import re
from typing import Dict, List, Any
from app.generators.backend_gen.utils import (
    entity_to_slug,
    entity_to_path,
    to_plural_snake_case,
)


SERVER_MANAGED_FIELDS = {"id", "createdAt", "created_at", "updatedAt", "updated_at", "deletedAt", "deleted_at"}


def _map_field_to_pydantic_type(field: Dict[str, Any]) -> str:
    """Map entity field type to Pydantic type annotation (returns base type, no Optional)."""
    field_type = field.get("type", "string").lower()
    
    type_map = {
        "string": "str",
        "number": "float",
        "integer": "int",
        "int": "int",
        "boolean": "bool",
        "bool": "bool",
        "datetime": "datetime",
        "date": "date",
        "array": "List[Any]",
        "object": "Dict[str, Any]",
    }
    
    return type_map.get(field_type, "str")


def _is_server_managed(field_name: str) -> bool:
    """Check if field is server-managed."""
    return field_name in SERVER_MANAGED_FIELDS


def render_entity_model(entity_name: str, fields: List[Dict[str, Any]]) -> str:
    """Generate Pydantic models for an entity."""
    slug = entity_to_slug(entity_name)
    
    lines = [
        "from pydantic import BaseModel",
        "from typing import Optional, Dict, Any, List",
        "from datetime import datetime, date",
        "",
        "",
    ]
    
    # Base model
    lines.append(f"class {entity_name}Base(BaseModel):")
    for field in fields:
        field_name = field["name"]
        base_type = _map_field_to_pydantic_type(field)
        if not field.get("required", False) or field.get("nullable", False):
            field_type = f"Optional[{base_type}]"
        else:
            field_type = base_type
        lines.append(f"    {field_name}: {field_type}")
    lines.append("")
    
    # Create model (exclude server-managed fields)
    lines.append(f"class {entity_name}Create(BaseModel):")
    for field in fields:
        field_name = field["name"]
        if _is_server_managed(field_name):
            continue
        base_type = _map_field_to_pydantic_type(field)
        if not field.get("required", False) or field.get("nullable", False):
            field_type = f"Optional[{base_type}]"
        else:
            field_type = base_type
        lines.append(f"    {field_name}: {field_type}")
    lines.append("")
    
    # Update model (all fields optional)
    lines.append(f"class {entity_name}Update(BaseModel):")
    for field in fields:
        field_name = field["name"]
        if _is_server_managed(field_name):
            continue
        base_type = _map_field_to_pydantic_type(field)
        lines.append(f"    {field_name}: Optional[{base_type}] = None")
    lines.append("")
    
    # Out model (includes id and timestamps)
    lines.append(f"class {entity_name}Out(BaseModel):")
    lines.append("    id: str")
    for field in fields:
        field_name = field["name"]
        if field_name == "id":
            continue
        base_type = _map_field_to_pydantic_type(field)
        if not field.get("required", False) or field.get("nullable", False):
            field_type = f"Optional[{base_type}]"
        else:
            field_type = base_type
        lines.append(f"    {field_name}: {field_type}")
    lines.append("    created_at: Optional[datetime] = None")
    lines.append("    updated_at: Optional[datetime] = None")
    
    return "\n".join(lines)


def render_entity_router(entity_name: str, entity_slug: str, path_slug: str, store_type: str, fields: List[Dict[str, Any]]) -> str:
    """Generate CRUD router for an entity."""
    repo_class = "PostgresRepo" if store_type == "postgres" else "MongoRepo"
    
    if store_type == "postgres":
        table_name = entity_to_slug(entity_name)
        # Format fields as Python list of dicts for repo initialization
        field_dicts = []
        for f in fields:
            required_val = "True" if f.get("required", False) else "False"
            nullable_val = "True" if f.get("nullable", False) else "False"
            field_dicts.append(f'{{"name": "{f["name"]}", "type": "{f.get("type", "string")}", "required": {required_val}, "nullable": {nullable_val}}}')
        fields_repr = "[" + ", ".join(field_dicts) + "]"
        repo_init = f'{repo_class}("{table_name}", {fields_repr})'
    else:
        collection_name = to_plural_snake_case(entity_name)
        repo_init = f'{repo_class}("{collection_name}")'
    
    lines = [
        "from fastapi import APIRouter, HTTPException, Query",
        "from typing import Optional",
        f"from app.models.{entity_slug} import {entity_name}Create, {entity_name}Update, {entity_name}Out",
        f"from app.repos.{'postgres_repo' if store_type == 'postgres' else 'mongo_repo'} import {repo_class}",
        "",
        "router = APIRouter()",
        "",
    ]
    
    lines.append(f'repo = {repo_init}')
    lines.append("")
    
    # List endpoint
    lines.append("@router.get(\"\", response_model=dict)")
    lines.append(f"async def list_{entity_slug}(limit: int = Query(100, ge=1), offset: int = Query(0, ge=0), q: Optional[str] = Query(None)):")
    lines.append(f'    result = await repo.list(limit=limit, offset=offset, q=q)')
    lines.append(f'    return {{"items": result["items"], "total": result["total"]}}')
    lines.append("")
    
    # Create endpoint
    lines.append(f"@router.post(\"\", response_model={entity_name}Out, status_code=201)")
    lines.append(f"async def create_{entity_slug}(data: {entity_name}Create):")
    lines.append(f'    result = await repo.create(data.model_dump())')
    lines.append(f"    return {entity_name}Out(**result)")
    lines.append("")
    
    # Get endpoint
    lines.append(f"@router.get(\"/{{id}}\", response_model={entity_name}Out)")
    lines.append(f"async def get_{entity_slug}(id: str):")
    lines.append(f'    result = await repo.get(id)')
    lines.append(f'    if not result:')
    lines.append(f'        raise HTTPException(status_code=404, detail=f"{entity_name} with id {{id}} not found")')
    lines.append(f"    return {entity_name}Out(**result)")
    lines.append("")
    
    # Replace endpoint
    lines.append(f"@router.put(\"/{{id}}\", response_model={entity_name}Out)")
    lines.append(f"async def replace_{entity_slug}(id: str, data: {entity_name}Create):")
    lines.append(f'    try:')
    lines.append(f'        result = await repo.replace(id, data.model_dump())')
    lines.append(f"        return {entity_name}Out(**result)")
    lines.append(f'    except ValueError as e:')
    lines.append(f'        raise HTTPException(status_code=404, detail=str(e))')
    lines.append("")
    
    # Patch endpoint
    lines.append(f"@router.patch(\"/{{id}}\", response_model={entity_name}Out)")
    lines.append(f"async def patch_{entity_slug}(id: str, data: {entity_name}Update):")
    lines.append(f'    update_data = {{k: v for k, v in data.model_dump().items() if v is not None}}')
    lines.append(f'    try:')
    lines.append(f'        result = await repo.patch(id, update_data)')
    lines.append(f"        return {entity_name}Out(**result)")
    lines.append(f'    except ValueError as e:')
    lines.append(f'        raise HTTPException(status_code=404, detail=str(e))')
    lines.append("")
    
    # Delete endpoint
    lines.append("@router.delete(\"/{id}\", status_code=204)")
    lines.append(f"async def delete_{entity_slug}(id: str):")
    lines.append(f'    success = await repo.delete(id)')
    lines.append(f'    if not success:')
    lines.append(f'        raise HTTPException(status_code=404, detail=f"{entity_name} with id {{id}} not found")')
    lines.append(f'    return None')
    
    return "\n".join(lines)

