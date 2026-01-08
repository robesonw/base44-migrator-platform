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


def to_camel_case(name: str) -> str:
    """Convert PascalCase to camelCase."""
    if not name:
        return name
    return name[0].lower() + name[1:]


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


def get_error_responses() -> Dict[str, Any]:
    """Get standard error responses for operations."""
    return {
        "400": {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        },
        "404": {
            "description": "Not Found",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        },
        "500": {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/Error"}
                }
            }
        }
    }


def generate_crud_paths(entity_name: str, path_base: str) -> Dict[str, Any]:
    """Generate CRUD paths for an entity."""
    paths = {}
    entity_camel = to_camel_case(entity_name)
    error_responses = get_error_responses()
    
    # GET /api/{path_base} - List
    list_path = f"/api/{path_base}"
    list_responses = {
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
    list_responses.update(error_responses)
    
    paths[list_path] = {
        "get": {
            "operationId": f"{entity_camel}_list",
            "tags": [entity_name],
            "summary": f"List {entity_name} entities",
            "parameters": [
                {"name": "limit", "in": "query", "schema": {"type": "integer", "minimum": 1, "default": 100}, "description": "Maximum number of items to return"},
                {"name": "offset", "in": "query", "schema": {"type": "integer", "minimum": 0, "default": 0}, "description": "Number of items to skip"},
                {"name": "q", "in": "query", "schema": {"type": "string"}, "description": "Search query", "required": False},
            ],
            "responses": list_responses
        }
    }
    
    # POST /api/{path_base} - Create
    create_responses = {
        "201": {
            "description": "Created",
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{entity_name}"}
                }
            }
        }
    }
    create_responses.update(error_responses)
    
    paths[list_path]["post"] = {
        "operationId": f"{entity_camel}_create",
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
        "responses": create_responses
    }
    
    # GET /api/{path_base}/{id} - Get one
    detail_path = f"/api/{path_base}/{{id}}"
    get_responses = {
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{entity_name}"}
                }
            }
        }
    }
    get_responses.update(error_responses)
    
    paths[detail_path] = {
        "get": {
            "operationId": f"{entity_camel}_get",
            "tags": [entity_name],
            "summary": f"Get a {entity_name} by ID",
            "parameters": [
                {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}, "description": f"{entity_name} ID"}
            ],
            "responses": get_responses
        }
    }
    
    # PUT /api/{path_base}/{id} - Replace
    update_responses = {
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{entity_name}"}
                }
            }
        }
    }
    update_responses.update(error_responses)
    
    paths[detail_path]["put"] = {
        "operationId": f"{entity_camel}_update",
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
        "responses": update_responses
    }
    
    # PATCH /api/{path_base}/{id} - Partial update
    patch_responses = {
        "200": {
            "description": "Successful response",
            "content": {
                "application/json": {
                    "schema": {"$ref": f"#/components/schemas/{entity_name}"}
                }
            }
        }
    }
    patch_responses.update(error_responses)
    
    paths[detail_path]["patch"] = {
        "operationId": f"{entity_camel}_patch",
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
        "responses": patch_responses
    }
    
    # DELETE /api/{path_base}/{id} - Delete
    delete_responses = {
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
    delete_responses.update(error_responses)
    
    paths[detail_path]["delete"] = {
        "operationId": f"{entity_camel}_delete",
        "tags": [entity_name],
        "summary": f"Delete a {entity_name}",
        "parameters": [
            {"name": "id", "in": "path", "required": True, "schema": {"type": "string"}, "description": f"{entity_name} ID"}
        ],
        "responses": delete_responses
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
    
    # Constants for AUTO classification
    MAX_POSTGRES_FIELDS = 25
    
    def run(self, job, ws):
        try:
            contract_path = ws.artifacts_dir / "ui-contract.json"
            
            if not contract_path.exists():
                return AgentResult(
                    self.stage,
                    False,
                    "ui-contract.json not found in workspace artifacts",
                    {}
                )
            
            # Load contract
            with open(contract_path, "r", encoding="utf-8") as f:
                contract = json.load(f)
            
            entities = contract.get("entities", [])
            if not entities:
                return AgentResult(
                    self.stage,
                    False,
                    "No entities found in ui-contract.json",
                    {}
                )
            
            # Get db_stack and preferences
            db_stack = job.db_stack
            # Get db_preferences from artifacts (optional field stored in JSON)
            artifacts = getattr(job, 'artifacts', {})
            db_preferences = artifacts.get('db_preferences', {}) if isinstance(artifacts, dict) else {}
            
            # Determine strategy (default: docToMongo for hybrid)
            hybrid_strategy = db_preferences.get("hybridStrategy", "docToMongo" if db_stack == "hybrid" else None)
            
            # Classify entities
            storage_plan = self._classify_entities(entities, db_stack, db_preferences, hybrid_strategy)
            
            # Write storage-plan.json
            storage_plan_path = ws.artifacts_dir / "storage-plan.json"
            storage_plan_path.write_text(
                json.dumps(storage_plan, indent=2),
            encoding="utf-8"
        )
            
            # Generate artifacts
            artifacts_index = {
                "storage_plan": str(storage_plan_path.relative_to(ws.root))
            }
            
            # Always write db-schema.md
            db_schema_md_path = ws.artifacts_dir / "db-schema.md"
            db_schema_md = self._generate_db_schema_md(storage_plan, entities)
            db_schema_md_path.write_text(db_schema_md, encoding="utf-8")
            artifacts_index["db_schema"] = str(db_schema_md_path.relative_to(ws.root))
            
            # Count entities by store
            postgres_entities = [e for e in storage_plan["entities"] if e["store"] == "postgres"]
            mongo_entities = [e for e in storage_plan["entities"] if e["store"] == "mongo"]
            
            # Generate Postgres artifacts if needed
            if db_stack in ("postgres", "hybrid") and postgres_entities:
                pg_artifacts = self._generate_postgres_artifacts(
                    ws, storage_plan, entities, postgres_entities
                )
                artifacts_index.update(pg_artifacts)
            
            # Generate Mongo artifacts if needed
            if db_stack in ("mongo", "hybrid") and mongo_entities:
                mongo_artifacts = self._generate_mongo_artifacts(
                    ws, storage_plan, entities, mongo_entities
                )
                artifacts_index.update(mongo_artifacts)
            
            # Log counts
            log.info(
                f"DomainModelerAgent: {len(entities)} total entities, "
                f"{len(postgres_entities)} postgres, {len(mongo_entities)} mongo, "
                f"{len(artifacts_index)} artifacts written",
                extra={"job_id": getattr(job, 'id', 'unknown'), "stage": str(self.stage)}
            )
            
            return AgentResult(
                self.stage,
                True,
                f"Generated storage plan and artifacts for {len(entities)} entities",
                artifacts_index
            )
        
        except Exception as e:
            log.error(f"DomainModelerAgent failed: {e}", exc_info=True)
            return AgentResult(
                self.stage,
                False,
                f"DomainModelerAgent failed: {str(e)}",
                {}
            )
    
    def _classify_entities(
        self,
        entities: List[Dict[str, Any]],
        db_stack: str,
        db_preferences: Dict[str, Any],
        hybrid_strategy: Optional[str]
    ) -> Dict[str, Any]:
        """Classify entities into postgres/mongo stores."""
        mode = db_stack
        
        # Get explicit overrides
        mongo_overrides = set(db_preferences.get("mongoEntities", []))
        postgres_overrides = set(db_preferences.get("postgresEntities", []))
        
        classified = []
        
        for entity in entities:
            entity_name = entity["name"]
            
            # Check explicit overrides first
            if entity_name in mongo_overrides:
                classified.append({
                    "name": entity_name,
                    "store": "mongo",
                    "reason": "explicit override in db_preferences.mongoEntities"
                })
                continue
            
            if entity_name in postgres_overrides:
                classified.append({
                    "name": entity_name,
                    "store": "postgres",
                    "reason": "explicit override in db_preferences.postgresEntities"
                })
                continue
            
            # AUTO classification (only if hybrid)
            if db_stack == "hybrid":
                # Determine strategy (auto is kept for backwards compatibility, maps to docToMongo)
                if hybrid_strategy in ("docToMongo", "postgresJsonbFirst", "auto"):
                    strategy = hybrid_strategy if hybrid_strategy != "auto" else "docToMongo"
                    store, reason = self._classify_entity_auto(entity, strategy)
                    classified.append({
                        "name": entity_name,
                        "store": store,
                        "reason": reason
                    })
                else:
                    # Fallback to docToMongo if unknown strategy
                    store, reason = self._classify_entity_auto(entity, "docToMongo")
                    classified.append({
                        "name": entity_name,
                        "store": store,
                        "reason": reason
                    })
            elif db_stack == "postgres":
                classified.append({
                    "name": entity_name,
                    "store": "postgres",
                    "reason": "db_stack is postgres"
                })
            elif db_stack == "mongo":
                classified.append({
                    "name": entity_name,
                    "store": "mongo",
                    "reason": "db_stack is mongo"
                })
            else:
                # Fallback (shouldn't happen)
                classified.append({
                    "name": entity_name,
                    "store": "postgres",
                    "reason": "default fallback"
                })
        
        return {
            "mode": mode,
            "entities": classified
        }
    
    def _classify_entity_auto(self, entity: Dict[str, Any], strategy: str = "docToMongo") -> tuple[str, str]:
        """Classify entity using AUTO strategy rules.
        
        Args:
            entity: Entity to classify
            strategy: Classification strategy - "docToMongo" (default) or "postgresJsonbFirst"
        """
        fields = entity.get("fields", [])
        entity_name = entity["name"]
        
        if strategy == "docToMongo":
            # docToMongo strategy: any complex object/map/array-of-object → mongo
            # Treat as complex → Mongo if any field:
            # - field.type == "object" AND (raw.additionalProperties is truthy OR raw.properties exists)
            # - OR field.type == "array" AND (raw.items.type == "object" OR raw.items.properties exists)
            for field in fields:
                field_type = field.get("type", "").lower()
                raw = field.get("raw", {})
                
                if field_type == "object":
                    # Check if additionalProperties is truthy (can be True, dict, or any truthy value)
                    has_additional_properties = "additionalProperties" in raw and raw.get("additionalProperties")
                    # Check if properties exists (even if empty, we check existence)
                    has_properties = "properties" in raw
                    
                    if has_additional_properties or has_properties:
                        if has_additional_properties:
                            return "mongo", f"field '{field['name']}' has additionalProperties"
                        elif has_properties:
                            return "mongo", f"field '{field['name']}' has properties"
                elif field_type == "array":
                    items = raw.get("items", {})
                    if isinstance(items, dict):
                        # Check if items.type == "object" OR items.properties exists
                        if items.get("type") == "object" or "properties" in items:
                            if items.get("type") == "object":
                                return "mongo", f"field '{field['name']}' is array of objects"
                            elif "properties" in items:
                                return "mongo", f"field '{field['name']}' is array of objects with properties"
        
        elif strategy == "postgresJsonbFirst":
            # postgresJsonbFirst strategy: keep postgres unless deep nesting detected
            for field in fields:
                field_type = field.get("type", "").lower()
                raw = field.get("raw", {})
                
                if field_type == "array":
                    items = raw.get("items", {})
                    if isinstance(items, dict) and items.get("type") == "object":
                        # Array of objects - deep nesting
                        return "mongo", f"field '{field['name']}' is array of objects (deep nesting)"
                    if isinstance(items, dict) and "properties" in items:
                        # Array of complex objects - deep nesting
                        return "mongo", f"field '{field['name']}' is array of objects with nested properties (deep nesting)"
                elif field_type == "object":
                    # Check nesting depth > 1
                    if "properties" in raw and raw["properties"]:
                        depth = self._calculate_field_nesting_depth(raw)
                        if depth > 1:
                            return "mongo", f"field '{field['name']}' has nested properties (depth {depth} > 1)"
                    # additionalProperties maps can stay in postgres (stored as JSONB)
                    # Only reject if it has nested properties with depth > 1
                    if "additionalProperties" in raw and raw.get("additionalProperties") is True:
                        # Check if it has properties that are nested
                        if "properties" in raw and raw["properties"]:
                            depth = self._calculate_field_nesting_depth(raw)
                            if depth > 1:
                                return "mongo", f"field '{field['name']}' has additionalProperties map with nested properties (depth {depth} > 1)"
        
        # Rule 3: Check field count
        if len(fields) > self.MAX_POSTGRES_FIELDS:
            return "mongo", f"entity has {len(fields)} fields (exceeds {self.MAX_POSTGRES_FIELDS})"
        
        # Rule 4: Check for relational patterns (optional heuristic)
        if self._is_relational_pattern(entity_name, fields):
            return "postgres", f"entity matches relational pattern and has only primitive fields"
        
        # Default to postgres
        return "postgres", "entity has only primitive fields or simple structures"
    
    def _calculate_field_nesting_depth(self, raw_schema: Dict[str, Any]) -> int:
        """Calculate nesting depth of a single field's schema."""
        if not isinstance(raw_schema, dict):
            return 0
        
        if "properties" not in raw_schema or not raw_schema["properties"]:
            return 0
        
        max_depth = 1
        for prop_value in raw_schema["properties"].values():
            if isinstance(prop_value, dict):
                prop_type = prop_value.get("type")
                if prop_type == "object" and "properties" in prop_value:
                    depth = 1 + self._calculate_field_nesting_depth(prop_value)
                    max_depth = max(max_depth, depth)
                elif prop_type == "array" and "items" in prop_value:
                    items = prop_value["items"]
                    if isinstance(items, dict) and items.get("type") == "object":
                        depth = 1 + self._calculate_field_nesting_depth(items)
                        max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _calculate_max_nesting_depth(self, fields: List[Dict[str, Any]]) -> int:
        """Calculate maximum nesting depth in entity fields."""
        max_depth = 0
        
        def depth_of_schema(schema: Any, current_depth: int = 0) -> int:
            if not isinstance(schema, dict):
                return current_depth
            
            if schema.get("type") == "object":
                props = schema.get("properties", {})
                if props:
                    return max(
                        depth_of_schema(v, current_depth + 1) for v in props.values()
                    ) if props else current_depth + 1
            elif schema.get("type") == "array":
                items = schema.get("items", {})
                return depth_of_schema(items, current_depth + 1)
            
            return current_depth
        
        for field in fields:
            raw = field.get("raw", {})
            depth = depth_of_schema(raw, 0)
            max_depth = max(max_depth, depth)
        
        return max_depth
    
    def _is_relational_pattern(self, entity_name: str, fields: List[Dict[str, Any]]) -> bool:
        """Check if entity matches relational naming patterns."""
        patterns = ["Link", "Join", "Map", "Follow", "Interaction"]
        if any(entity_name.endswith(pattern) for pattern in patterns):
            # Check if all fields are primitives
            primitive_types = {"string", "number", "integer", "boolean", "datetime", "date"}
            for field in fields:
                field_type = field.get("type", "").lower()
                if field_type not in primitive_types:
                    return False
            return True
        return False
    
    def _generate_db_schema_md(
        self,
        storage_plan: Dict[str, Any],
        entities: List[Dict[str, Any]]
    ) -> str:
        """Generate human-readable db-schema.md."""
        lines = ["# Database Schema"]
        lines.append("")
        lines.append(f"**Storage Mode:** {storage_plan['mode']}")
        lines.append("")
        lines.append("## Entity Classification")
        lines.append("")
        
        entity_map = {e["name"]: e for e in entities}
        
        for classified in storage_plan["entities"]:
            entity_name = classified["name"]
            store = classified["store"]
            reason = classified["reason"]
            entity = entity_map.get(entity_name, {})
            fields = entity.get("fields", [])
            
            lines.append(f"### {entity_name}")
            lines.append(f"- **Store:** {store}")
            lines.append(f"- **Reason:** {reason}")
            lines.append(f"- **Fields:** {len(fields)}")
            lines.append("")
        
        lines.append("## Field Details")
        lines.append("")
        
        for entity in entities:
            entity_name = entity["name"]
            fields = entity.get("fields", [])
            classified = next(
                (e for e in storage_plan["entities"] if e["name"] == entity_name),
                None
            )
            store = classified["store"] if classified else "unknown"
            
            lines.append(f"### {entity_name} ({store})")
            lines.append("")
            for field in fields:
                field_type = field.get("type", "unknown")
                required = field.get("required", False)
                nullable = field.get("nullable", False)
                req_str = "required" if required else "optional"
                null_str = "nullable" if nullable else "not nullable"
                lines.append(f"- `{field['name']}`: {field_type} ({req_str}, {null_str})")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_postgres_artifacts(
        self,
        ws,
        storage_plan: Dict[str, Any],
        entities: List[Dict[str, Any]],
        postgres_entities: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Generate Postgres artifacts."""
        artifacts = {}
        entity_map = {e["name"]: e for e in entities}
        pg_entity_names = {e["name"] for e in postgres_entities}
        pg_entities = [entity_map[name] for name in pg_entity_names if name in entity_map]
        
        # Generate db-schema.sql
        sql_path = ws.artifacts_dir / "db-schema.sql"
        sql_content = self._generate_postgres_sql(pg_entities)
        sql_path.write_text(sql_content, encoding="utf-8")
        artifacts["db_schema_sql"] = str(sql_path.relative_to(ws.root))
        
        # Generate models_postgres.py
        models_path = ws.artifacts_dir / "models_postgres.py"
        models_content = self._generate_postgres_models(pg_entities)
        models_path.write_text(models_content, encoding="utf-8")
        artifacts["models_postgres"] = str(models_path.relative_to(ws.root))
        
        # Generate Alembic migration
        migrations_dir = ws.artifacts_dir / "migrations"
        migrations_dir.mkdir(exist_ok=True)
        migration_path = migrations_dir / "0001_initial_schema.py"
        migration_content = self._generate_alembic_migration(pg_entities)
        migration_path.write_text(migration_content, encoding="utf-8")
        artifacts["alembic_migration"] = str(migration_path.relative_to(ws.root))
        
        return artifacts
    
    def _generate_postgres_sql(self, entities: List[Dict[str, Any]]) -> str:
        """Generate PostgreSQL CREATE TABLE statements."""
        lines = []
        
        for entity in entities:
            entity_name = entity["name"]
            table_name = to_snake_case(entity_name)
            fields = entity.get("fields", [])
            
            lines.append(f"CREATE TABLE {table_name} (")
            
            # Check for id field
            has_id = any(f.get("name") == "id" for f in fields)
            if not has_id:
                lines.append("    id TEXT PRIMARY KEY,")
            
            # Check for system timestamp fields
            created_at_field = next((f for f in fields if f.get("name") in ("created_at", "createdAt")), None)
            updated_at_field = next((f for f in fields if f.get("name") in ("updated_at", "updatedAt")), None)
            
            # Generate columns
            column_lines = []
            for field in fields:
                field_name_raw = field["name"]
                field_name = to_snake_case(field_name_raw)
                field_type = field.get("type", "string").lower()
                required = field.get("required", False)
                nullable = field.get("nullable", False)
                raw = field.get("raw", {})
                
                # Handle id field specially
                if field_name == "id":
                    column_lines.append(f"    {field_name} TEXT PRIMARY KEY")
                    continue
                
                # Skip system timestamp fields - handle separately
                if field_name_raw in ("created_at", "createdAt", "updated_at", "updatedAt"):
                    continue
                
                # Map to PostgreSQL type
                pg_type = self._map_postgres_type(field_type, raw)
                
                # Build column definition
                col_def = f"    {field_name} {pg_type}"
                if not nullable and required:
                    col_def += " NOT NULL"
                
                # Add CHECK constraint for enums
                if "enum" in raw:
                    enum_values = ", ".join(f"'{v}'" for v in raw["enum"])
                    col_def = col_def.rstrip()
                    col_def += f" CHECK ({field_name} IN ({enum_values}))"
                
                column_lines.append(col_def)
            
            # Handle created_at
            if created_at_field:
                # Field exists - check if user-supplied (default to system-managed)
                field_name = to_snake_case(created_at_field["name"])
                raw = created_at_field.get("raw", {})
                # Check if description indicates user-supplied
                description = raw.get("description", "").lower()
                is_user_supplied = any(word in description for word in ["user", "supplied", "provided", "input"])
                default_clause = "" if is_user_supplied else " DEFAULT now()"
                required = created_at_field.get("required", False)
                nullable = created_at_field.get("nullable", False)
                not_null = " NOT NULL" if not nullable and required else ""
                column_lines.append(f"    {field_name} TIMESTAMPTZ{not_null}{default_clause}")
            else:
                # Add system-managed created_at
                column_lines.append("    created_at TIMESTAMPTZ NOT NULL DEFAULT now()")
            
            # Handle updated_at (always system-managed with DEFAULT now())
            if updated_at_field:
                field_name = to_snake_case(updated_at_field["name"])
                required = updated_at_field.get("required", False)
                nullable = updated_at_field.get("nullable", False)
                not_null = " NOT NULL" if not nullable and required else ""
                column_lines.append(f"    {field_name} TIMESTAMPTZ{not_null} DEFAULT now()")
            else:
                # Add system-managed updated_at
                column_lines.append("    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()")
            
            lines.append(",\n".join(column_lines))
            lines.append(");")
            lines.append("")
        
        return "\n".join(lines)
    
    def _map_postgres_type(self, field_type: str, raw: Dict[str, Any]) -> str:
        """Map field type to PostgreSQL type."""
        type_map = {
            "string": "TEXT",
            "number": "DOUBLE PRECISION",
            "integer": "BIGINT",
            "int": "BIGINT",
            "boolean": "BOOLEAN",
            "bool": "BOOLEAN",
            "datetime": "TIMESTAMPTZ",
            "date": "DATE",
        }
        
        # Check for array/object - use JSONB
        if field_type in ("array", "object"):
            return "JSONB"
        
        return type_map.get(field_type.lower(), "TEXT")
    
    def _generate_postgres_models(self, entities: List[Dict[str, Any]]) -> str:
        """Generate SQLAlchemy models for Postgres entities."""
        lines = [
            "from sqlalchemy import Column, String, BigInteger, Boolean, Double, DateTime, Text, CheckConstraint, JSON",
            "from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ",
            "from sqlalchemy.ext.declarative import declarative_base",
            "from datetime import datetime",
            "",
            "Base = declarative_base()",
            "",
        ]
        
        for entity in entities:
            entity_name = entity["name"]
            table_name = to_snake_case(entity_name)
            fields = entity.get("fields", [])
            
            lines.append(f"class {entity_name}(Base):")
            lines.append(f'    __tablename__ = "{table_name}"')
            lines.append("")
            
            # Check for system timestamp fields
            created_at_field = next((f for f in fields if f.get("name") in ("created_at", "createdAt")), None)
            updated_at_field = next((f for f in fields if f.get("name") in ("updated_at", "updatedAt")), None)
            
            # Generate columns
            has_id = False
            for field in fields:
                field_name = field["name"]
                snake_name = to_snake_case(field_name)
                field_type = field.get("type", "string").lower()
                required = field.get("required", False)
                nullable = field.get("nullable", False)
                raw = field.get("raw", {})
                
                if field_name == "id":
                    has_id = True
                    lines.append(f'    {snake_name} = Column(String, primary_key=True)')
                    continue
                
                # Skip system timestamp fields - handle separately
                if field_name in ("created_at", "createdAt", "updated_at", "updatedAt"):
                    continue
                
                # Map to SQLAlchemy type
                sa_type = self._map_sqlalchemy_type(field_type, raw)
                
                # Build column definition
                col_parts = [f"Column({sa_type}"]
                if not nullable and required:
                    col_parts.append("nullable=False")
                col_parts.append(")")
                col_def = ", ".join(col_parts)
                
                lines.append(f"    {snake_name} = {col_def}")
            
            # Add id if missing
            if not has_id:
                lines.append("    id = Column(String, primary_key=True)")
            
            # Handle created_at
            if created_at_field:
                field_name = to_snake_case(created_at_field["name"])
                raw = created_at_field.get("raw", {})
                description = raw.get("description", "").lower()
                is_user_supplied = any(word in description for word in ["user", "supplied", "provided", "input"])
                server_default = "" if is_user_supplied else ", server_default='now()'"
                required = created_at_field.get("required", False)
                nullable = created_at_field.get("nullable", False)
                nullable_str = ", nullable=False" if not nullable and required else ""
                lines.append(f"    {field_name} = Column(TIMESTAMPTZ{nullable_str}{server_default})")
            else:
                lines.append("    created_at = Column(TIMESTAMPTZ, nullable=False, server_default='now()')")
            
            # Handle updated_at (always system-managed)
            if updated_at_field:
                field_name = to_snake_case(updated_at_field["name"])
                required = updated_at_field.get("required", False)
                nullable = updated_at_field.get("nullable", False)
                nullable_str = ", nullable=False" if not nullable and required else ""
                lines.append(f"    {field_name} = Column(TIMESTAMPTZ{nullable_str}, server_default='now()')")
            else:
                lines.append("    updated_at = Column(TIMESTAMPTZ, nullable=False, server_default='now()')")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _map_sqlalchemy_type(self, field_type: str, raw: Dict[str, Any]) -> str:
        """Map field type to SQLAlchemy type."""
        type_map = {
            "string": "String",
            "number": "Double",
            "integer": "BigInteger",
            "int": "BigInteger",
            "boolean": "Boolean",
            "bool": "Boolean",
            "datetime": "TIMESTAMPTZ",
            "date": "DateTime",
        }
        
        if field_type in ("array", "object"):
            return "JSON"
        
        return type_map.get(field_type.lower(), "String")
    
    def _generate_alembic_migration(self, entities: List[Dict[str, Any]]) -> str:
        """Generate Alembic migration file."""
        from datetime import datetime
        
        create_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            '"""initial_schema',
            "",
            "Revision ID: 0001",
            "Revises:",
            f"Create Date: {create_date}",
            '"""',
            "",
            "from alembic import op",
            "import sqlalchemy as sa",
            "from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMPTZ",
            "",
            "revision = '0001'",
            "down_revision = None",
            "branch_labels = None",
            "depends_on = None",
            "",
            "def upgrade():",
        ]
        
        for entity in entities:
            entity_name = entity["name"]
            table_name = to_snake_case(entity_name)
            fields = entity.get("fields", [])
            
            lines.append(f"    op.create_table(")
            lines.append(f'        "{table_name}",')
            
            # Generate columns
            has_id = False
            column_defs = []
            
            for field in fields:
                field_name = field["name"]
                snake_name = to_snake_case(field_name)
                field_type = field.get("type", "string").lower()
                required = field.get("required", False)
                nullable = field.get("nullable", False)
                raw = field.get("raw", {})
                
                if field_name == "id":
                    has_id = True
                    column_defs.append(f'        sa.Column("{snake_name}", sa.String(), primary_key=True),')
                    continue
                
                # Map to Alembic type
                alembic_type = self._map_alembic_type(field_type, raw)
                
                col_parts = [f'sa.Column("{snake_name}", {alembic_type})']
                if not nullable and required:
                    col_parts[-1] = col_parts[-1].rstrip(')') + ", nullable=False)"
                column_defs.append("        " + col_parts[0])
            
            if not has_id:
                column_defs.insert(0, '        sa.Column("id", sa.String(), primary_key=True),')
            
            # Handle system timestamp fields
            created_at_field = next((f for f in fields if f.get("name") in ("created_at", "createdAt")), None)
            updated_at_field = next((f for f in fields if f.get("name") in ("updated_at", "updatedAt")), None)
            
            # Handle created_at
            if created_at_field:
                field_name = to_snake_case(created_at_field["name"])
                raw = created_at_field.get("raw", {})
                description = raw.get("description", "").lower()
                is_user_supplied = any(word in description for word in ["user", "supplied", "provided", "input"])
                server_default = "" if is_user_supplied else ', server_default=sa.text("now()")'
                required = created_at_field.get("required", False)
                nullable = created_at_field.get("nullable", False)
                nullable_str = ", nullable=False" if not nullable and required else ""
                column_defs.append(f'        sa.Column("{field_name}", TIMESTAMPTZ(){nullable_str}{server_default}),')
            else:
                column_defs.append('        sa.Column("created_at", TIMESTAMPTZ(), nullable=False, server_default=sa.text("now()")),')
            
            # Handle updated_at (always system-managed)
            if updated_at_field:
                field_name = to_snake_case(updated_at_field["name"])
                required = updated_at_field.get("required", False)
                nullable = updated_at_field.get("nullable", False)
                nullable_str = ", nullable=False" if not nullable and required else ""
                column_defs.append(f'        sa.Column("{field_name}", TIMESTAMPTZ(){nullable_str}, server_default=sa.text("now()")),')
            else:
                column_defs.append('        sa.Column("updated_at", TIMESTAMPTZ(), nullable=False, server_default=sa.text("now()")),')
            
            lines.extend(column_defs)
            lines.append("    )")
            lines.append("")
        
        lines.extend([
            "def downgrade():",
        ])
        
        for entity in reversed(entities):  # Reverse for downgrade
            table_name = to_snake_case(entity["name"])
            lines.append(f'    op.drop_table("{table_name}")')
        
        return "\n".join(lines)
    
    def _map_alembic_type(self, field_type: str, raw: Dict[str, Any]) -> str:
        """Map field type to Alembic/sqlalchemy type."""
        type_map = {
            "string": "sa.String()",
            "number": "sa.Double()",
            "integer": "sa.BigInteger()",
            "int": "sa.BigInteger()",
            "boolean": "sa.Boolean()",
            "bool": "sa.Boolean()",
            "datetime": "TIMESTAMPTZ()",
            "date": "sa.Date()",
        }
        
        if field_type in ("array", "object"):
            return "JSONB()"
        
        return type_map.get(field_type.lower(), "sa.String()")
    
    def _generate_mongo_artifacts(
        self,
        ws,
        storage_plan: Dict[str, Any],
        entities: List[Dict[str, Any]],
        mongo_entities: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Generate Mongo artifacts."""
        artifacts = {}
        entity_map = {e["name"]: e for e in entities}
        mongo_entity_names = {e["name"] for e in mongo_entities}
        mongo_entities_list = [entity_map[name] for name in mongo_entity_names if name in entity_map]
        
        # Generate mongo-collections.md
        collections_path = ws.artifacts_dir / "mongo-collections.md"
        collections_content = self._generate_mongo_collections_md(mongo_entities_list)
        collections_path.write_text(collections_content, encoding="utf-8")
        artifacts["mongo_collections"] = str(collections_path.relative_to(ws.root))
        
        # Generate mongo-schemas.json
        schemas_path = ws.artifacts_dir / "mongo-schemas.json"
        schemas_content = self._generate_mongo_schemas_json(mongo_entities_list)
        schemas_path.write_text(json.dumps(schemas_content, indent=2), encoding="utf-8")
        artifacts["mongo_schemas"] = str(schemas_path.relative_to(ws.root))
        
        # Generate models_mongo.py
        models_path = ws.artifacts_dir / "models_mongo.py"
        models_content = self._generate_mongo_models(mongo_entities_list)
        models_path.write_text(models_content, encoding="utf-8")
        artifacts["models_mongo"] = str(models_path.relative_to(ws.root))
        
        return artifacts
    
    def _generate_mongo_collections_md(self, entities: List[Dict[str, Any]]) -> str:
        """Generate mongo-collections.md document."""
        lines = ["# MongoDB Collections"]
        lines.append("")
        
        for entity in entities:
            entity_name = entity["name"]
            collection_name = self._to_mongo_collection_name(entity_name)
            fields = entity.get("fields", [])
            
            lines.append(f"## {collection_name}")
            lines.append(f"- **Entity:** {entity_name}")
            lines.append(f"- **Fields:** {len(fields)}")
            lines.append("")
            lines.append("### Schema Summary")
            lines.append("")
            
            for field in fields:
                field_type = field.get("type", "unknown")
                required = field.get("required", False)
                lines.append(f"- `{field['name']}`: {field_type} ({'required' if required else 'optional'})")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _to_mongo_collection_name(self, entity_name: str) -> str:
        """Convert entity name to MongoDB collection name (snake_case plural)."""
        snake = to_snake_case(entity_name)
        # Simple pluralization (add 's')
        if not snake.endswith('s'):
            return snake + "s"
        return snake
    
    def _generate_mongo_schemas_json(self, entities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate JSON Schema-like definitions for MongoDB collections."""
        schemas = {}
        
        for entity in entities:
            entity_name = entity["name"]
            collection_name = self._to_mongo_collection_name(entity_name)
            fields = entity.get("fields", [])
            
            schema = {
                "type": "object",
                "properties": {},
                "required": []
            }
            
            # Check if entity has id field
            has_id_field = any(f.get("name") == "id" for f in fields)
            
            # Add _id field (prefer string for Base44 IDs)
            schema["properties"]["_id"] = {
                "type": "string",
                "description": "Document ID"
            }
            
            # Add entity fields (skip id field if it exists, since we use _id)
            for field in fields:
                field_name = field["name"]
                
                # Skip id field - _id is used instead
                if field_name == "id":
                    continue
                
                raw = field.get("raw", {})
                
                # Convert field to JSON schema property
                field_schema = self._field_to_mongo_schema_property(raw, field)
                schema["properties"][field_name] = field_schema
                
                if field.get("required", False):
                    schema["required"].append(field_name)
            
            schemas[collection_name] = schema
        
        return schemas
    
    def _field_to_mongo_schema_property(self, raw: Dict[str, Any], field: Dict[str, Any]) -> Dict[str, Any]:
        """Convert field to MongoDB JSON schema property."""
        field_type = field.get("type", "string").lower()
        schema = {}
        
        # Map types
        type_map = {
            "string": "string",
            "number": "number",
            "integer": "integer",
            "boolean": "boolean",
            "datetime": "string",
            "date": "string",
            "array": "array",
            "object": "object",
        }
        
        schema["type"] = type_map.get(field_type, "string")
        
        # Preserve nested structures
        if "properties" in raw:
            schema["properties"] = raw["properties"]
        if "additionalProperties" in raw:
            schema["additionalProperties"] = raw["additionalProperties"]
        if "items" in raw:
            schema["items"] = raw["items"]
        
        # Preserve enums
        if "enum" in raw:
            schema["enum"] = raw["enum"]
        
        # Preserve formats
        if "format" in raw:
            schema["format"] = raw["format"]
        elif field_type == "datetime":
            schema["format"] = "date-time"
        elif field_type == "date":
            schema["format"] = "date"
        
        # Preserve description
        if "description" in raw:
            schema["description"] = raw["description"]
        
        return schema
    
    def _generate_mongo_models(self, entities: List[Dict[str, Any]]) -> str:
        """Generate Pydantic models for Mongo entities."""
        lines = [
            "from pydantic import BaseModel, Field",
            "from typing import Optional, List, Dict, Any",
            "from datetime import datetime",
            "",
        ]
        
        for entity in entities:
            entity_name = entity["name"]
            collection_name = self._to_mongo_collection_name(entity_name)
            fields = entity.get("fields", [])
            
            lines.append(f"class {entity_name}(BaseModel):")
            lines.append(f'    """MongoDB model for {collection_name} collection."""')
            lines.append("")
            
            # Generate fields
            has_id = False
            for field in fields:
                field_name = field["name"]
                field_type = field.get("type", "string").lower()
                required = field.get("required", False)
                nullable = field.get("nullable", False)
                raw = field.get("raw", {})
                
                if field_name == "id":
                    has_id = True
                    lines.append(f'    id: str = Field(..., alias="_id", description="Document ID")')
                    continue
                
                # Map to Python type
                python_type = self._map_python_type(field_type, raw, required and not nullable)
                field_def = f"    {field_name}: {python_type}"
                
                # Add Field() if needed
                field_args = []
                if not required or nullable:
                    field_args.append("default=None")
                if "description" in raw:
                    field_args.append(f'description="{raw["description"]}"')
                
                if field_args:
                    field_def += " = Field(" + ", ".join(field_args) + ")"
                
                lines.append(field_def)
            
            if not has_id:
                lines.append('    id: str = Field(..., alias="_id", description="Document ID")')
            
            lines.append("")
            lines.append("    class Config:")
            lines.append("        populate_by_name = True")
            lines.append("")
            lines.append("")
            lines.append(f"class {entity_name}Repository:")
            lines.append(f'    """Repository interface for {entity_name}."""')
            lines.append("")
            lines.append(f"    def find_by_id(self, id: str) -> Optional[{entity_name}]:")
            lines.append(f'        """Find {entity_name.lower()} by ID."""')
            lines.append("        raise NotImplementedError")
            lines.append("")
            lines.append(f"    def find_all(self) -> List[{entity_name}]:")
            lines.append(f'        """Find all {entity_name.lower()} entities."""')
            lines.append("        raise NotImplementedError")
            lines.append("")
            lines.append(f"    def create(self, entity: {entity_name}) -> {entity_name}:")
            lines.append(f'        """Create a new {entity_name.lower()}."""')
            lines.append("        raise NotImplementedError")
            lines.append("")
            lines.append(f"    def update(self, id: str, entity: {entity_name}) -> Optional[{entity_name}]:")
            lines.append(f'        """Update a {entity_name.lower()} by ID."""')
            lines.append("        raise NotImplementedError")
            lines.append("")
            lines.append(f"    def delete(self, id: str) -> bool:")
            lines.append(f'        """Delete a {entity_name.lower()} by ID."""')
            lines.append("        raise NotImplementedError")
            lines.append("")
        
        return "\n".join(lines)
    
    def _map_python_type(self, field_type: str, raw: Dict[str, Any], required: bool) -> str:
        """Map field type to Python type annotation."""
        type_map = {
            "string": "str",
            "number": "float",
            "integer": "int",
            "boolean": "bool",
            "datetime": "datetime",
            "date": "datetime",
        }
        
        if field_type == "array":
            items = raw.get("items", {})
            if isinstance(items, dict):
                item_type = items.get("type", "string")
                python_item_type = type_map.get(item_type, "Any")
                return f"List[{python_item_type}]"
            return "List[Any]"
        
        if field_type == "object":
            return "Dict[str, Any]"
        
        python_type = type_map.get(field_type.lower(), "str")
        if not required:
            return f"Optional[{python_type}]"
        
        return python_type


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
            schemas = {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Error message"
                        },
                        "code": {
                            "type": "string",
                            "description": "Error code"
                        }
                    },
                    "required": ["error"]
                }
            }
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
