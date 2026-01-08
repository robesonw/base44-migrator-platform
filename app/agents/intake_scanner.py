"""
Scanner utilities for RepoIntakeAgent to detect entities, frameworks, endpoints, etc.
Uses fast file walking and regex patterns (no full AST parsing) for performance.
"""
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

# Maximum file size to read (100KB)
MAX_FILE_SIZE = 100 * 1024

# Directories to ignore
IGNORE_DIRS = {"node_modules", ".next", "dist", "build", ".git", ".gitignore"}


@dataclass
class EntitySpec:
    """Normalized entity specification."""
    name: str
    sourcePath: str
    fields: List[Dict[str, Any]] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    rawShapeHint: str = "unknown"
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EntityDetectionResult:
    """Result of entity detection scan."""
    entities: List[EntitySpec] = field(default_factory=list)
    directoriesFound: List[str] = field(default_factory=list)
    filesParsed: int = 0
    filesFailed: List[Dict[str, str]] = field(default_factory=list)


def should_ignore_path(path: Path) -> bool:
    """Check if a path should be ignored."""
    parts = path.parts
    return any(part in IGNORE_DIRS for part in parts)


def find_json_files_in_dir(base_dir: Path, pattern: str) -> List[Path]:
    """Find JSON files matching a pattern (case-insensitive directory matching)."""
    json_files = []
    
    # Normalize pattern (handle ** wildcards)
    if "**" in pattern:
        # Recursive search: e.g., "src/Entities/**/*.json"
        dir_parts_str = pattern.split("/**")[0]
        file_pattern = pattern.split("**/")[-1]  # Should be "*.json"
        
        dir_parts = dir_parts_str.split("/")
        
        # Recursive case-insensitive directory search
        def find_dirs_recursive(current: Path, remaining_parts: List[str]) -> List[Path]:
            if not remaining_parts:
                return [current] if current.exists() and current.is_dir() else []
            if not current.exists() or not current.is_dir():
                return []
            
            results = []
            next_part = remaining_parts[0]
            for item in current.iterdir():
                if item.is_dir() and item.name.lower() == next_part.lower():
                    results.extend(find_dirs_recursive(item, remaining_parts[1:]))
            return results
        
        found_dirs = find_dirs_recursive(base_dir, dir_parts)
        for dir_path in found_dirs:
            json_files.extend(dir_path.rglob(file_pattern))
    else:
        # Simple pattern without **
        pattern_parts = pattern.split("/")
        dir_part = "/".join(pattern_parts[:-1])
        file_pattern = pattern_parts[-1]
        
        # Try exact match first
        target_dir = base_dir / dir_part
        if target_dir.exists() and target_dir.is_dir():
            json_files.extend(target_dir.rglob(file_pattern))
        else:
            # Case-insensitive search
            dir_parts = dir_part.split("/")
            def find_dir_case_insensitive(current: Path, parts: List[str]) -> Optional[Path]:
                if not parts:
                    return current if current.exists() and current.is_dir() else None
                if not current.exists() or not current.is_dir():
                    return None
                for item in current.iterdir():
                    if item.is_dir() and item.name.lower() == parts[0].lower():
                        result = find_dir_case_insensitive(item, parts[1:])
                        if result:
                            return result
                return None
            
            found_dir = find_dir_case_insensitive(base_dir, dir_parts)
            if found_dir:
                json_files.extend(found_dir.rglob(file_pattern))
    
    # Filter out ignored paths and ensure files exist and are JSON
    result = []
    for f in json_files:
        if f.exists() and f.is_file() and f.suffix == ".json" and not should_ignore_path(f):
            result.append(f)
    return result


def parse_entity_json(json_data: Dict[str, Any], file_path: Path, base_dir: Path) -> Optional[EntitySpec]:
    """Parse entity JSON into normalized EntitySpec, handling multiple shapes."""
    try:
        rel_path = str(file_path.relative_to(base_dir))
        entity_name = file_path.stem  # Default to filename
        
        fields = []
        relationships = []
        raw_shape = "unknown"
        
        # Shape 1: Fields array
        # {"name":"Recipe","fields":[{"name":"id","type":"string","required":true}]}
        if "fields" in json_data and isinstance(json_data["fields"], list):
            raw_shape = "fields-array"
            entity_name = json_data.get("name", entity_name)
            for field_def in json_data["fields"]:
                if isinstance(field_def, dict) and "name" in field_def:
                    fields.append({
                        "name": field_def["name"],
                        "type": field_def.get("type", "unknown"),
                        "required": field_def.get("required", False),
                        "nullable": field_def.get("nullable", False),
                        "raw": field_def
                    })
            # Check for relationships in this shape
            if "relationships" in json_data and isinstance(json_data["relationships"], list):
                relationships = json_data["relationships"]
        
        # Shape 2: Key->type map
        # {"id":"string","title":"string","rating":"number"}
        elif all(isinstance(v, str) for k, v in json_data.items() if not k.startswith("_")):
            raw_shape = "key-map"
            for key, type_str in json_data.items():
                if not key.startswith("_"):
                    fields.append({
                        "name": key,
                        "type": type_str,
                        "required": True,  # Assume required for key-map
                        "nullable": False,
                        "raw": {}
                    })
        
        # Shape 3: Embedded schema
        # {"entity":"Recipe","schema":{"id":{"type":"uuid"},"title":{"type":"string"}}}
        elif "schema" in json_data and isinstance(json_data["schema"], dict):
            raw_shape = "embedded-schema"
            entity_name = json_data.get("entity", entity_name)
            schema = json_data["schema"]
            for key, field_def in schema.items():
                if isinstance(field_def, dict):
                    fields.append({
                        "name": key,
                        "type": field_def.get("type", "unknown"),
                        "required": field_def.get("required", True),
                        "nullable": field_def.get("nullable", False),
                        "raw": field_def
                    })
                elif isinstance(field_def, str):
                    fields.append({
                        "name": key,
                        "type": field_def,
                        "required": True,
                        "nullable": False,
                        "raw": {}
                    })
        
        # Shape 4: JSON Schema-like
        # {"title":"Recipe","type":"object","properties":{"id":{"type":"string"}},"required":["id"]}
        elif "properties" in json_data and json_data.get("type") == "object":
            raw_shape = "json-schema"
            entity_name = json_data.get("title", entity_name)
            properties = json_data.get("properties", {})
            required_fields = set(json_data.get("required", []))
            
            for key, prop_def in properties.items():
                if isinstance(prop_def, dict):
                    fields.append({
                        "name": key,
                        "type": prop_def.get("type", "unknown"),
                        "required": key in required_fields,
                        "nullable": prop_def.get("nullable", False),
                        "raw": prop_def
                    })
        
        return EntitySpec(
            name=entity_name,
            sourcePath=rel_path,
            fields=fields,
            relationships=relationships,
            rawShapeHint=raw_shape,
            raw=json_data
        )
    
    except Exception as e:
        log.warning(f"Failed to parse entity JSON {file_path}: {e}")
        return None


def discover_entities(source_dir: Path) -> EntityDetectionResult:
    """Discover entities from JSON files in priority order."""
    result = EntityDetectionResult()
    
    # Priority order of directories to check
    priority_patterns = [
        "src/Entities/**/*.json",
        "src/entities/**/*.json",
        "src/models/**/*.json",
        "src/model/**/*.json",
        "app/Entities/**/*.json",
        "app/entities/**/*.json",
    ]
    
    found_files = set()
    
    for pattern in priority_patterns:
        json_files = find_json_files_in_dir(source_dir, pattern)
        if json_files:
            # Extract directory from pattern (e.g., "src/Entities" from "src/Entities/**/*.json")
            dir_part = pattern.split("/**")[0]
            if dir_part not in result.directoriesFound:
                result.directoriesFound.append(dir_part)
            
            for json_file in json_files:
                if json_file in found_files:
                    continue
                found_files.add(json_file)
                
                try:
                    # Read and parse JSON
                    content = json_file.read_text(encoding="utf-8")
                    json_data = json.loads(content)
                    
                    entity = parse_entity_json(json_data, json_file, source_dir)
                    if entity:
                        result.entities.append(entity)
                        result.filesParsed += 1
                    else:
                        result.filesFailed.append({
                            "path": str(json_file.relative_to(source_dir)),
                            "error": "Could not parse entity structure"
                        })
                
                except json.JSONDecodeError as e:
                    result.filesFailed.append({
                        "path": str(json_file.relative_to(source_dir)),
                        "error": f"Invalid JSON: {str(e)}"
                    })
                except Exception as e:
                    result.filesFailed.append({
                        "path": str(json_file.relative_to(source_dir)),
                        "error": str(e)
                    })
    
    return result


def detect_framework(source_dir: Path) -> Dict[str, Any]:
    """Detect frontend framework from package.json and config files."""
    package_json_path = source_dir / "package.json"
    
    framework_info = {"name": "unknown", "versionHint": ""}
    
    if not package_json_path.exists():
        return framework_info
    
    try:
        package_json = json.loads(package_json_path.read_text(encoding="utf-8"))
        deps = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
        
        # Check for Next.js
        if "next" in deps:
            framework_info["name"] = "nextjs"
            framework_info["versionHint"] = deps["next"]
        elif (source_dir / "next.config.js").exists() or (source_dir / "next.config.ts").exists() or \
             (source_dir / "next.config.mjs").exists():
            framework_info["name"] = "nextjs"
        elif (source_dir / "app").exists() or (source_dir / "pages").exists():
            # Check for app/ or pages/ directories (Next.js patterns)
            framework_info["name"] = "nextjs"
        
        # Check for Vite
        elif "vite" in deps:
            framework_info["name"] = "vite"
            framework_info["versionHint"] = deps["vite"]
        elif any((source_dir / f"vite.config.{ext}").exists() for ext in ["js", "ts", "mjs"]):
            framework_info["name"] = "vite"
        
        # Check for CRA
        elif "react-scripts" in deps:
            framework_info["name"] = "cra"
            framework_info["versionHint"] = deps["react-scripts"]
    
    except Exception as e:
        log.warning(f"Failed to parse package.json: {e}")
    
    return framework_info


def detect_env_vars(source_dir: Path) -> List[Dict[str, Any]]:
    """Detect environment variables (NEXT_PUBLIC_*, VITE_*) and their usage locations."""
    env_vars = {}
    
    # Patterns to match
    patterns = [
        (r"NEXT_PUBLIC_(\w+)", "NEXT_PUBLIC_"),
        (r"VITE_(\w+)", "VITE_"),
    ]
    
    # Scan TypeScript/JavaScript files
    source_extensions = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}
    
    for file_path in source_dir.rglob("*"):
        if should_ignore_path(file_path):
            continue
        
        if file_path.suffix not in source_extensions:
            continue
        
        try:
            # Read only first N KB for performance
            content_bytes = file_path.read_bytes()
            if len(content_bytes) > MAX_FILE_SIZE:
                content = content_bytes[:MAX_FILE_SIZE].decode("utf-8", errors="ignore")
            else:
                content = content_bytes.decode("utf-8", errors="ignore")
            
            lines = content.split("\n")
            rel_path = str(file_path.relative_to(source_dir))
            
            for line_num, line in enumerate(lines, start=1):
                for pattern, prefix in patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        var_name = prefix + match.group(1)
                        if var_name not in env_vars:
                            env_vars[var_name] = []
                        env_vars[var_name].append(f"{rel_path}:{line_num}")
        
        except Exception as e:
            log.warning(f"Error scanning {file_path}: {e}")
    
    # Convert to list format, combining line numbers into ranges
    result = []
    for var_name, locations in env_vars.items():
        # Group consecutive line numbers into ranges
        location_list = []
        for loc in locations:
            file_part, line_str = loc.rsplit(":", 1)
            line_num = int(line_str)
            location_list.append(f"{file_part}:{line_num}-{line_num}")
        
        result.append({
            "name": var_name,
            "sourceLocations": location_list
        })
    
    return result


def scan_endpoints(source_dir: Path) -> List[Dict[str, Any]]:
    """Scan source files for fetch/axios API calls."""
    endpoints = []
    source_extensions = {".ts", ".tsx", ".js", ".jsx"}
    
    # Patterns for fetch/axios calls
    fetch_pattern = re.compile(r'fetch\s*\([^)]+\)', re.MULTILINE | re.DOTALL)
    axios_method_pattern = re.compile(r'axios\.(get|post|put|patch|delete)\s*\([^)]+\)', re.MULTILINE | re.DOTALL)
    # More lenient pattern for axios config - match opening brace, then find matching closing brace
    axios_config_pattern = re.compile(r'axios\s*\(\s*\{', re.MULTILINE)
    
    for file_path in source_dir.rglob("*"):
        if should_ignore_path(file_path):
            continue
        
        if file_path.suffix not in source_extensions:
            continue
        
        try:
            # Read only first N KB for performance
            content_bytes = file_path.read_bytes()
            if len(content_bytes) > MAX_FILE_SIZE:
                content = content_bytes[:MAX_FILE_SIZE].decode("utf-8", errors="ignore")
            else:
                content = content_bytes.decode("utf-8", errors="ignore")
            
            lines = content.split("\n")
            rel_path = str(file_path.relative_to(source_dir))
            
            # Find fetch calls
            for match in fetch_pattern.finditer(content):
                start_line = content[:match.start()].count("\n") + 1
                end_line = content[:match.end()].count("\n") + 1
                
                call_text = match.group(0)
                endpoint = parse_fetch_call(call_text, rel_path, start_line, end_line)
                if endpoint:
                    endpoints.append(endpoint)
            
            # Find axios method calls (get, post, etc.)
            for match in axios_method_pattern.finditer(content):
                start_line = content[:match.start()].count("\n") + 1
                end_line = content[:match.end()].count("\n") + 1
                
                method = match.group(1).upper()
                call_text = match.group(0)
                endpoint = parse_axios_method_call(call_text, method, rel_path, start_line, end_line)
                if endpoint:
                    endpoints.append(endpoint)
            
            # Find axios config object calls - need to extract full call including nested braces
            for match in axios_config_pattern.finditer(content):
                start_pos = match.start()
                # Find the matching closing brace and parenthesis
                brace_count = 0
                paren_count = 0
                in_string = False
                string_char = None
                pos = start_pos
                
                while pos < len(content):
                    char = content[pos]
                    
                    if char in ('"', "'", "`") and (pos == 0 or content[pos-1] != "\\"):
                        if not in_string:
                            in_string = True
                            string_char = char
                        elif char == string_char:
                            in_string = False
                            string_char = None
                    elif not in_string:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                # Found closing brace, now find closing paren
                                pos += 1
                                while pos < len(content) and content[pos] in (' ', '\n', '\t'):
                                    pos += 1
                                if pos < len(content) and content[pos] == ')':
                                    call_text = content[start_pos:pos+1]
                                    start_line = content[:start_pos].count("\n") + 1
                                    end_line = content[:pos+1].count("\n") + 1
                                    endpoint = parse_axios_config_call(call_text, rel_path, start_line, end_line)
                                    if endpoint:
                                        endpoints.append(endpoint)
                                    break
                        elif char == '(' and brace_count == 0:
                            paren_count += 1
                        elif char == ')' and brace_count == 0:
                            paren_count -= 1
                            if paren_count < 0:
                                break
                    pos += 1
        
        except Exception as e:
            log.warning(f"Error scanning endpoints in {file_path}: {e}")
    
    return endpoints


def parse_fetch_call(call_text: str, file_path: str, start_line: int, end_line: int) -> Optional[Dict[str, Any]]:
    """Parse a fetch() call to extract endpoint information."""
    # Extract URL argument (first argument)
    # Match strings, template literals, or variables
    url_match = re.search(r'fetch\s*\(\s*(["\'`])(.*?)\1', call_text, re.DOTALL)
    if not url_match:
        # Try template literal
        url_match = re.search(r'fetch\s*\(\s*`([^`]+)`', call_text)
    
    if url_match:
        url = url_match.group(2) if url_match else url_match.group(1)
        # Check if dynamic (contains ${} or concatenation)
        is_dynamic = "${" in url or "+" in url or "`" in url_match.group(0)
        
        # Extract method from options (second arg or in first arg object)
        method = "GET"
        options_match = re.search(r'fetch\s*\([^,)]+,\s*\{[^}]*method\s*:\s*["\'](\w+)["\']', call_text, re.IGNORECASE)
        if options_match:
            method = options_match.group(1).upper()
        
        return {
            "method": method,
            "pathHint": url if not is_dynamic else url[:50] + "...",  # Truncate long paths
            "dynamic": is_dynamic,
            "sourceLocations": [f"{file_path}:{start_line}-{end_line}"],
            "requestBodyHint": extract_body_hint(call_text),
            "responseShapeHint": None
        }
    
    # Could not extract URL - mark as dynamic
    return {
        "method": "GET",
        "pathHint": "dynamic",
        "dynamic": True,
        "sourceLocations": [f"{file_path}:{start_line}-{end_line}"],
        "requestBodyHint": None,
        "responseShapeHint": None
    }


def parse_axios_method_call(call_text: str, method: str, file_path: str, start_line: int, end_line: int) -> Optional[Dict[str, Any]]:
    """Parse axios.get/post/put/patch/delete() call."""
    # Extract URL (first argument) - can be string, template literal, or variable
    # Try template literal first (most common)
    url_match = re.search(r'axios\.\w+\s*\(\s*`([^`]+)`', call_text, re.DOTALL)
    if url_match:
        url = url_match.group(1)
        is_dynamic = "${" in url
        # Extract just the path part if it's a template literal with variables
        if "/" in url:
            # Try to extract the path segment
            path_match = re.search(r'([/\w-]+)', url)
            if path_match:
                url = path_match.group(1)
    else:
        # Try single/double quoted string
        url_match = re.search(r'axios\.\w+\s*\(\s*(["\'])([^"\']+)\1', call_text)
        if url_match:
            url = url_match.group(2)
            is_dynamic = False
        else:
            # Try to match unquoted path starting with /
            url_match = re.search(r'axios\.\w+\s*\(\s*(/[^\s,)]+)', call_text)
            if url_match:
                url = url_match.group(1).rstrip(",)")
                is_dynamic = False
            else:
                # Cannot extract URL - mark as dynamic
                return {
                    "method": method,
                    "pathHint": "dynamic",
                    "dynamic": True,
                    "sourceLocations": [f"{file_path}:{start_line}-{end_line}"],
                    "requestBodyHint": extract_body_hint(call_text),
                    "responseShapeHint": None
                }
    
    return {
        "method": method,
        "pathHint": url if not is_dynamic else url[:50] + "...",
        "dynamic": is_dynamic,
        "sourceLocations": [f"{file_path}:{start_line}-{end_line}"],
        "requestBodyHint": extract_body_hint(call_text),
        "responseShapeHint": None
    }


def parse_axios_config_call(call_text: str, file_path: str, start_line: int, end_line: int) -> Optional[Dict[str, Any]]:
    """Parse axios({...}) config object call."""
    # Extract URL and method from config object
    # Try template literal first
    url_match = re.search(r'url\s*:\s*`([^`]+)`', call_text, re.IGNORECASE | re.DOTALL)
    if url_match:
        url = url_match.group(1)
        is_dynamic = "${" in url
        if "/" in url and not is_dynamic:
            path_match = re.search(r'([/\w-]+)', url)
            if path_match:
                url = path_match.group(1)
    else:
        # Try single/double quoted string
        url_match = re.search(r'url\s*:\s*(["\'])([^"\']+)\1', call_text, re.IGNORECASE)
        if url_match:
            url = url_match.group(2)
            is_dynamic = False
        else:
            # Try unquoted path starting with /
            url_match = re.search(r'url\s*:\s*(/[^\s,}]+)', call_text, re.IGNORECASE)
            if url_match:
                url = url_match.group(1).rstrip(",}")
                is_dynamic = False
            else:
                url = None
                is_dynamic = True
    
    method = "GET"
    method_match = re.search(r'method\s*:\s*["\'](\w+)["\']', call_text, re.IGNORECASE)
    if method_match:
        method = method_match.group(1).upper()
    
    if url:
        return {
            "method": method,
            "pathHint": url if not is_dynamic else url[:50] + "..." if url else "dynamic",
            "dynamic": is_dynamic,
            "sourceLocations": [f"{file_path}:{start_line}-{end_line}"],
            "requestBodyHint": extract_body_hint(call_text),
            "responseShapeHint": None
        }
    
    return {
        "method": method,
        "pathHint": "dynamic",
        "dynamic": True,
        "sourceLocations": [f"{file_path}:{start_line}-{end_line}"],
        "requestBodyHint": None,
        "responseShapeHint": None
    }


def extract_body_hint(call_text: str) -> Optional[str]:
    """Extract request body hint from API call text."""
    # Look for body/data in the call
    body_match = re.search(r'(?:body|data)\s*:\s*\{[^}]+', call_text, re.IGNORECASE | re.DOTALL)
    if body_match:
        body_text = body_match.group(0)[:100]  # First 100 chars
        return body_text
    return None


def detect_api_client_files(source_dir: Path) -> List[str]:
    """Detect common API client wrapper files."""
    api_client_patterns = [
        "src/lib/api.ts",
        "src/lib/api.js",
        "src/services/api.ts",
        "src/services/api.js",
        "src/api/index.ts",
        "src/api/index.js",
        "src/api/client.ts",
        "src/api/client.js",
    ]
    
    found_files = []
    for pattern in api_client_patterns:
        file_path = source_dir / pattern
        if file_path.exists():
            # Normalize path separators to forward slashes
            rel_path = str(file_path.relative_to(source_dir)).replace("\\", "/")
            found_files.append(rel_path)
    
    # Also check for any file in src/api/ directory
    api_dir = source_dir / "src" / "api"
    if api_dir.exists() and api_dir.is_dir():
        for file_path in api_dir.rglob("*.ts"):
            rel_path = str(file_path.relative_to(source_dir)).replace("\\", "/")
            if rel_path not in found_files:
                found_files.append(rel_path)
        for file_path in api_dir.rglob("*.js"):
            rel_path = str(file_path.relative_to(source_dir)).replace("\\", "/")
            if rel_path not in found_files:
                found_files.append(rel_path)
    
    return found_files

