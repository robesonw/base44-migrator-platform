#!/usr/bin/env python3
"""
Fix Base44 patterns in already-migrated frontend code.

This script fixes the Base44 entity patterns that weren't properly mapped
in the initial migration.
"""

import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def to_kebab_case(name: str) -> str:
    """Convert PascalCase or camelCase to kebab-case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1)
    return s2.lower()


def entity_to_slug(entity_name: str) -> str:
    """Convert entity name to API slug (kebab-case)."""
    return to_kebab_case(entity_name)


def fix_base44_patterns(frontend_dir: Path):
    """Fix Base44 patterns in frontend code."""
    log.info("Fixing Base44 patterns...")
    
    # Find all files
    files_to_process = []
    for ext in ["*.js", "*.jsx", "*.ts", "*.tsx"]:
        files_to_process.extend(frontend_dir.rglob(ext))
    
    replacements_made = 0
    for file_path in files_to_process:
        if "node_modules" in str(file_path) or "api/client" in str(file_path):
            continue
        
        try:
            content = file_path.read_text(encoding="utf-8")
            original_content = content
            
            # Map base44.entities.{EntityName}.list() to apiClient.get('/api/{slug}')
            def replace_list(match):
                entity_name = match.group(1)
                params = match.group(2) if match.group(2) else ""
                slug = entity_to_slug(entity_name)
                params_str = params.strip().strip("'\"")
                
                if params_str:
                    # Handle sort params like '-created_date'
                    if params_str.startswith('-'):
                        sort_field = params_str[1:]
                        return f"apiClient.get('/api/{slug}', {{ sort: '{sort_field}', order: 'desc' }})"
                    elif params_str:
                        return f"apiClient.get('/api/{slug}', {{ sort: '{params_str}', order: 'asc' }})"
                return f"apiClient.get('/api/{slug}')"
            
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.list\(([^)]*)\)",
                replace_list,
                content
            )
            
            # Map base44.entities.{EntityName}.create(data) to apiClient.post('/api/{slug}', data)
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.create\(([^)]+)\)",
                lambda m: f"apiClient.post('/api/{entity_to_slug(m.group(1))}', {m.group(2)})",
                content
            )
            
            # Map base44.entities.{EntityName}.get(id) to apiClient.get('/api/{slug}/{id}')
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.get\(([^)]+)\)",
                lambda m: f"apiClient.get(`/api/{entity_to_slug(m.group(1))}/${{{m.group(2).strip()}}}`)",
                content
            )
            
            # Map base44.entities.{EntityName}.update(id, data) to apiClient.patch('/api/{slug}/{id}', data)
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.update\(([^,]+),\s*([^)]+)\)",
                lambda m: f"apiClient.patch(`/api/{entity_to_slug(m.group(1))}/${{{m.group(2).strip()}}}`, {m.group(3)})",
                content
            )
            
            # Map base44.entities.{EntityName}.delete(id) to apiClient.delete('/api/{slug}/{id}')
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.delete\(([^)]+)\)",
                lambda m: f"apiClient.delete(`/api/{entity_to_slug(m.group(1))}/${{{m.group(2).strip()}}}`)",
                content
            )
            
            # Map base44.entities.{EntityName}.filter(params) to apiClient.get('/api/{slug}', params)
            content = re.sub(
                r"base44\.entities\.([A-Za-z][A-Za-z0-9]*)\.filter\(([^)]+)\)",
                lambda m: f"apiClient.get('/api/{entity_to_slug(m.group(1))}', {m.group(2)})",
                content
            )
            
            # Handle auth calls
            content = re.sub(
                r"base44\.auth\.me\(\)",
                "apiClient.get('/api/auth/me')",
                content
            )
            
            # Replace any remaining base44 references
            content = re.sub(
                r"base44\.",
                "apiClient.",
                content
            )
            
            if content != original_content:
                file_path.write_text(content, encoding="utf-8")
                replacements_made += 1
                log.info(f"Fixed {file_path.relative_to(frontend_dir)}")
        except Exception as e:
            log.warning(f"Could not process {file_path}: {e}")
    
    log.info(f"Fixed patterns in {replacements_made} files")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python fix_base44_patterns.py <frontend_dir>")
        sys.exit(1)
    
    frontend_dir = Path(sys.argv[1])
    if not frontend_dir.exists():
        print(f"Error: Directory {frontend_dir} does not exist")
        sys.exit(1)
    
    fix_base44_patterns(frontend_dir)


