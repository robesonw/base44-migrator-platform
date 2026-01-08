import json
import logging
import re
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.agents.base import BaseAgent, AgentResult
from app.core.workflow import JobStage

log = logging.getLogger(__name__)

# Server-managed fields that should be excluded from Create schemas
SERVER_MANAGED_FIELDS = {"id", "createdAt", "created_at", "updatedAt", "updated_at", "deletedAt", "deleted_at"}


def to_kebab_case(name: str) -> str:
    """Convert PascalCase or camelCase to kebab-case."""
    # Insert hyphen before uppercase letters (except the first)
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    # Insert hyphen before uppercase letters that follow lowercase
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1)
    return s2.lower()


def to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()


def entity_to_path(entity_name: str) -> str:
    """Convert entity name to API path (prefer kebab-case, fallback to snake-case)."""
    # Try kebab-case first, but if it looks like it's already snake_case, use that
    if '_' in entity_name:
        return to_snake_case(entity_name)
    return to_kebab_case(entity_name)


def map_field_type(field_type: str) -> str:
    """Map entity field type to JSON schema type."""
    type_map = {
        "string": "string",
        "number": "number",
        "integer": "integer",
        "int": "integer",
        "boolean": "boolean",
        "bool": "boolean",
        "array": "array",
        "object": "object",
        "datetime": "string",  # OpenAPI uses string with format: date-time
        "date": "string",  # OpenAPI uses string with format: date
    }
    return type_map.get(field_type.lower(), "string")  # Default to string if unknown


def field_to_json_schema(field: Dict[str, Any]) -> Dict[str, Any]:
    """Convert entity field to JSON schema property."""
    schema = {}
    
    # Get raw JSON schema info if available
    raw = field.get("raw", {})
    
    # Type mapping
    field_type = field.get("type", "string")
    schema_type = map_field_type(field_type)
    schema["type"] = schema_type
    
    # Handle format for datetime/date
    if field_type.lower() in ("datetime", "date"):
        if field_type.lower() == "datetime":
            schema["format"] = "date-time"
        elif field_type.lower() == "date":
            schema["format"] = "date"
    elif "format" in raw:
        schema["format"] = raw["format"]
    
    # Preserve enum
    if "enum" in raw:
        schema["enum"] = raw["enum"]
    
    # Preserve minimum/maximum
    if "minimum" in raw:
        schema["minimum"] = raw["minimum"]
    if "maximum" in raw:
        schema["maximum"] = raw["maximum"]
    
    # Handle array items
    if schema_type == "array":
        if "items" in raw:
            schema["items"] = raw["items"]
        else:
            schema["items"] = {"type": "string"}  # Default
    
    # Handle object properties
    if schema_type == "object":
        if "properties" in raw:
            schema["properties"] = raw["properties"]
        if "additionalProperties" in raw:
            schema["additionalProperties"] = raw["additionalProperties"]
        else:
            schema["additionalProperties"] = True  # Permissive default
    
    # Preserve description
    if "description" in raw:
        schema["description"] = raw["description"]
    
    return schema


def is_server_managed(field_name: str) -> bool:
    """Check if a field name indicates it's server-managed."""
    return field_name in SERVER_MANAGED_FIELDS


def entity_to_schemas(entity: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Generate base, Create, and Update schemas for an entity."""
    entity_name = entity["name"]
    fields = entity.get("fields", [])
    
    # Base schema
    base_properties = {}
    base_required = []
    
    for field in fields:
        field_name = field["name"]
        base_properties[field_name] = field_to_json_schema(field)
        if field.get("required", False):
            base_required.append(field_name)
    
    base_schema = {
        "type": "object",
        "properties": base_properties,
    }
    if base_required:
        base_schema["required"] = base_required
    
    # Create schema (exclude server-managed fields)
    create_properties = {}
    create_required = []
    
    for field in fields:
        field_name = field["name"]
        if not is_server_managed(field_name):
            create_properties[field_name] = field_to_json_schema(field)
            if field.get("required", False):
                create_required.append(field_name)
    
    create_schema = {
        "type": "object",
        "properties": create_properties,
    }
    if create_required:
        create_schema["required"] = create_required
    
    # Update schema (all fields optional)
    update_properties = {}
    for field in fields:
        field_name = field["name"]
        field_schema = field_to_json_schema(field)
        update_properties[field_name] = field_schema
    
    update_schema = {
        "type": "object",
        "properties": update_properties,
    }
    
    return {
        entity_name: base_schema,
        f"{entity_name}Create": create_schema,
        f"{entity_name}Update": update_schema,
    }


def generate_crud_paths(entity_name: str, path_base: str) -> Dict[str, Any]:
    """Generate CRUD paths for an entity."""
    paths = {}
    
    # GET /api/{path_base} - List
    list_path = f"/api/{path_base}"
    paths[list_path] = {
        "get": {
            "tags": [entity_name],
            "summary": f"List {entity_name} entities",
            "parameters": [
                {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "default": 100}, "description": "Maximum number of items to return"},
                {"name": "offset", "in": "query", "schema": {"type": "integer", "minimum": 0, "default": 0}, "description": "Number of items to skip"},
                {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Search query", "required": False},
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "items": {
                                        "type": "array",
                                        "items": {"$ref": f"#/components/schemas/{entity_name}"}
                                    },
                                    "total": {"type": "integer"}
                                },
                                "required": ["items", "total"]
                            }
                        }
                    }
                }
            }
        }
    }
    
    # POST /api/{path_base} - Create
    paths[list_path]["post"] = {
        "tags": [entity_name],
        "summary": f"Create a new {entity_name}",
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{entity_name}Create"}
                }
            }
        },
        "responses": {
            "201": {
                "description": "Created",
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{entity_name}"}
                    }
                }
            }
        }
    }
    
    # GET /api/{path_base}/{id} - Get one
    detail_path = f"/api/{path_base}/{{id}}"
    paths[detail_path] = {
        "get": {
            "tags": [entity_name],
            "summary": f"Get a {entity_name} by ID",
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}, "description": f"{entity_name} ID"}
            ],
            "responses": {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{entity_name}"}
                        }
                    }
                }
            }
        }
    }
    
    # PUT /api/{path_base}/{id} - Replace
    paths[detail_path]["put"] = {
        "tags": [entity_name],
        "summary": f"Replace a {entity_name}",
        "parameters": [
            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}, "description": f"{entity_name} ID"}
        ],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{entity_name}Update"}
                }
            }
        },
        "responses": {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{entity_name}"}
                    }
                }
            }
        }
    }
    
    # PATCH /api/{path_base}/{id} - Partial update
    paths[detail_path]["patch"] = {
        "tags": [entity_name],
        "summary": f"Partially update a {entity_name}",
        "parameters": [
            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}, "description": f"{entity_name} ID"}
        ],
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{entity_name}Update"}
                }
            }
        },
        "responses": {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{entity_name}"}
                    }
                }
            }
        }
    }
    
    # DELETE /api/{path_base}/{id} - Delete
    paths[detail_path]["delete"] = {
        "tags": [entity_name],
        "summary": f"Delete a {entity_name}",
        "parameters": [
            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}, "description": f"{entity_name} ID"}
        ],
        "responses": {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "deleted": {"type": "boolean"}
                            },
                            "required": ["deleted"]
                        }
                    }
                }
            }
        }
    }
    
    return paths


def parse_endpoint_path(endpoint: Dict[str, Any]) -> Optional[tuple[str, str]]:
    """Parse endpoint from endpointsUsed to (method, path)."""
    method = endpoint.get("method", "GET").upper()
    path_hint = endpoint.get("pathHint", "")
    
    if not path_hint or path_hint == "dynamic":
        return None
    
    # Try to extract a clean path
    # Remove protocol and domain if present
    path = path_hint
    if "://" in path:
        # Extract path after domain
        parts = path.split("/", 3)
        if len(parts) >= 4:
            path = "/" + parts[3]
        else:
            path = "/"
    
    # Ensure starts with /
    if not path.startswith("/"):
        path = "/" + path
    
    # Remove query params
    if "?" in path:
        path = path.split("?")[0]
    
    return (method, path)


def scan_api_client_files(source_dir: Path, api_client_files: List[str]) -> List[Dict[str, Any]]:
    """Scan API client files for endpoints (best-effort, never fails)."""
    endpoints = []
    
    if not api_client_files:
        return endpoints
    
    try:
        for client_file in api_client_files:
            file_path = source_dir / client_file
            if not file_path.exists():
                continue
            
            if not file_path.suffix.lower() in {".js", ".ts", ".jsx", ".tsx"}:
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                
                # Look for base URLs
                base_url_patterns = [
                    r'baseURL\s*[:=]\s*["\']([^"\']+)["\']',
                    r'baseUrl\s*[:=]\s*["\']([^"\']+)["\']',
                    r'base_url\s*[:=]\s*["\']([^"\']+)["\']',
                ]
                
                base_url = None
                for pattern in base_url_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        base_url = match.group(1)
                        break
                
                # Look for path patterns: "/functions/", "/api/", "base44"
                path_patterns = [
                    r'["\'](/functions/[^"\']+)["\']',
                    r'["\'](/api/[^"\']+)["\']',
                    r'["\']([^"\']*base44[^"\']*)["\']',
                ]
                
                for pattern in path_patterns:
                    for match in re.finditer(pattern, content, re.IGNORECASE):
                        path = match.group(1)
                        if base_url:
                            full_path = base_url.rstrip("/") + path
                        else:
                            full_path = path
                        
                        endpoints.append({
                            "method": "GET",  # Default, best-effort
                            "path": full_path,
                            "source": client_file,
                        })
            except Exception as e:
                log.debug(f"Error scanning API client file {client_file}: {e}")
                continue
    
    except Exception as e:
        log.debug(f"Error in API client file scanning: {e}")
    
    return endpoints


class DomainModelerAgent(BaseAgent):
    stage = JobStage.DESIGN_DB_SCHEMA
    def run(self, job, ws):
        schema_path = ws.artifacts_dir / "db-schema.md"
        schema_path.write_text(
            "# DB Schema (placeholder)\n\n"
            "- TODO: Infer entities from ui-contract.json\n"
            "- TODO: Generate migrations in the migrated app repo\n",
            encoding="utf-8"
        )
        return AgentResult(self.stage, True, "Wrote placeholder db-schema.md", {"db_schema": str(schema_path.relative_to(ws.root))})


class ApiDesignerAgent(BaseAgent):
    stage = JobStage.DESIGN_API
    
    def run(self, job, ws):
        try:
            contract_path = ws.artifacts_dir / "ui-contract.json"
            
            if not contract_path.exists():
                return AgentResult(
                    self.stage,
                    False,
                    f"ui-contract.json not found at {contract_path}",
                    {}
                )
            
            # Read contract
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            
            entities = contract.get("entities", [])
            endpoints_used = contract.get("endpointsUsed", [])
            api_client_files = contract.get("apiClientFiles", [])
            
            # Validate that we have something to work with
            if not entities and not endpoints_used:
                return AgentResult(
                    self.stage,
                    False,
                    "Cannot generate OpenAPI spec: entities and endpointsUsed are both empty",
                    {}
                )
            
            # Build OpenAPI spec
            schemas = {}
            paths = {}
            tags = []
            
            # Process entities
            entity_count = 0
            schema_count = 0
            path_count = 0
            
            for entity in entities:
                entity_name = entity["name"]
                entity_count += 1
                
                # Generate schemas
                entity_schemas = entity_to_schemas(entity)
                schemas.update(entity_schemas)
                schema_count += len(entity_schemas)
                
                # Generate CRUD paths
                path_base = entity_to_path(entity_name)
                entity_paths = generate_crud_paths(entity_name, path_base)
                paths.update(entity_paths)
                path_count += len(entity_paths)
                
                # Add tag
                tags.append({"name": entity_name})
            
            # Process endpointsUsed
            upstream_paths_added = 0
            if endpoints_used:
                for endpoint in endpoints_used:
                    parsed = parse_endpoint_path(endpoint)
                    if parsed:
                        method, path = parsed
                        # Ensure path starts with /api/ or add it
                        if not path.startswith("/api/"):
                            path = "/api" + path if path.startswith("/") else "/api/" + path
                        
                        if path not in paths:
                            paths[path] = {}
                        
                        # Create best-effort operation
                        operation = {
                            "tags": ["upstream"],
                            "summary": f"{method} {path}",
                            "responses": {
                                "200": {
                                    "description": "Successful response",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "additionalProperties": True
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        # Add request body for POST/PUT/PATCH
                        if method in ("POST", "PUT", "PATCH"):
                            operation["requestBody"] = {
                                "required": True,
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "additionalProperties": True
                                        }
                                    }
                                }
                            }
                        
                        paths[path][method.lower()] = operation
                        upstream_paths_added += 1
            
            # Add upstream tag if we added upstream paths
            if upstream_paths_added > 0 and not any(tag["name"] == "upstream" for tag in tags):
                tags.append({"name": "upstream"})
            
            # Optional: scan API client files (best-effort)
            wrapper_endpoints = []
            if api_client_files and ws.source_dir.exists():
                wrapper_endpoints = scan_api_client_files(ws.source_dir, api_client_files)
                if wrapper_endpoints:
                    for endpoint in wrapper_endpoints:
                        path = endpoint["path"]
                        method = endpoint["method"]
                        
                        if not path.startswith("/api/"):
                            path = "/api" + path if path.startswith("/") else "/api/" + path
                        
                        if path not in paths:
                            paths[path] = {}
                        
                        paths[path][method.lower()] = {
                            "tags": ["upstream"],
                            "summary": f"{method} {path} (from wrapper)",
                            "responses": {
                                "200": {
                                    "description": "Successful response",
                                    "content": {
                                        "application/json": {
                                            "schema": {
                                                "type": "object",
                                                "additionalProperties": True
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    
                    if not any(tag["name"] == "upstream" for tag in tags):
                        tags.append({"name": "upstream"})
            
            # Build OpenAPI document
            openapi_spec = {
                "openapi": "3.0.3",
                "info": {
                    "title": "Generated API",
                    "version": "0.1.0",
                    "description": "API generated from ui-contract.json"
                },
                "servers": [
                    {"url": "http://localhost:8080", "description": "Development server"}
                ],
                "tags": tags,
                "paths": paths,
                "components": {
                    "schemas": schemas
                }
            }
            
            # Write OpenAPI YAML
            openapi_path = ws.artifacts_dir / "openapi.yaml"
            with open(openapi_path, "w", encoding="utf-8") as f:
                yaml.dump(openapi_spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
            
            # Log counts
            log.info(
                f"Generated OpenAPI spec: {entity_count} entities, "
                f"{schema_count} schemas, {path_count + upstream_paths_added + len(wrapper_endpoints)} paths"
            )
            
            return AgentResult(
                self.stage,
                True,
                f"Generated openapi.yaml with {entity_count} entities, {schema_count} schemas, {len(paths)} paths",
                {"openapi": str(openapi_path.relative_to(ws.root))}
            )
        
        except Exception as e:
            log.exception(f"Failed to generate openapi.yaml: {e}")
            return AgentResult(
                self.stage,
                False,
                f"Failed to generate openapi.yaml: {str(e)}",
                {}
            )
