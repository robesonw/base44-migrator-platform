"""
Scanner utilities for detecting Base44 client usage patterns.
"""
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

log = logging.getLogger(__name__)

# Maximum file size to read (100KB)
MAX_FILE_SIZE = 100 * 1024

# Directories to ignore
IGNORE_DIRS = {"node_modules", ".next", "dist", "build", ".git", ".gitignore", ".venv", "venv", "__pycache__"}


def should_ignore_path(path: Path) -> bool:
    """Check if a path should be ignored."""
    parts = path.parts
    return any(part in IGNORE_DIRS for part in parts)


def scan_base44_client_usage(source_dir: Path) -> Dict[str, Any]:
    """
    Scan source repository for base44Client usage patterns.
    
    Returns a dictionary with:
    - clientFiles: List of file paths where base44Client is used
    - usage: Dict with entities, storage, functions, llm usage
    - importLocations: List of import location details
    - notes: Additional notes
    """
    client_files = []
    import_locations = []
    entities_used = set()
    storage_used = False
    functions_used = False
    llm_used = False
    
    # Patterns to search for
    base44_import_pattern = re.compile(
        r'import\s+(?:.*\s+from\s+)?["\']([^"\']*base44Client[^"\']*)["\']|'
        r'from\s+["\']([^"\']*base44Client[^"\']*)["\']',
        re.IGNORECASE
    )
    
    entities_pattern = re.compile(
        r'base44\.entities\.(\w+)\.(list|get|create|update|patch|delete|replace|filter)',
        re.IGNORECASE
    )
    
    storage_pattern = re.compile(
        r'base44\.storage\.',
        re.IGNORECASE
    )
    
    functions_pattern = re.compile(
        r'base44\.functions\.',
        re.IGNORECASE
    )
    
    llm_pattern = re.compile(
        r'base44\.(?:llm|ai|InvokeLLM)\.',
        re.IGNORECASE
    )
    
    # File extensions to scan
    extensions = {'.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs'}
    
    def scan_file(file_path: Path) -> Optional[Dict[str, Any]]:
        """Scan a single file for base44Client usage."""
        try:
            if file_path.stat().st_size > MAX_FILE_SIZE:
                return None
            
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            rel_path = str(file_path.relative_to(source_dir)).replace('\\', '/')
            
            file_info = None
            
            # Check for imports
            import_matches = list(base44_import_pattern.finditer(content))
            if import_matches:
                lines = content.split('\n')
                for match in import_matches:
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = lines[line_num - 1] if line_num <= len(lines) else ''
                    
                    if not file_info:
                        file_info = {
                            'file': rel_path,
                            'imports': [],
                            'entities': set(),
                            'hasStorage': False,
                            'hasFunctions': False,
                            'hasLLM': False
                        }
                        client_files.append(rel_path)
                    
                    file_info['imports'].append({
                        'line': line_num,
                        'snippet': line_content.strip()[:100]
                    })
                    
                    import_locations.append({
                        'file': rel_path,
                        'lineRange': f"{line_num}-{line_num}",
                        'snippetHint': line_content.strip()[:100]
                    })
            
            # Check for entity usage
            entity_matches = list(entities_pattern.finditer(content))
            if entity_matches:
                if not file_info:
                    file_info = {
                        'file': rel_path,
                        'imports': [],
                        'entities': set(),
                        'hasStorage': False,
                        'hasFunctions': False,
                        'hasLLM': False
                    }
                    client_files.append(rel_path)
                
                for match in entity_matches:
                    entity_name = match.group(1)
                    entities_used.add(entity_name)
                    file_info['entities'].add(entity_name)
            
            # Check for storage usage
            if storage_pattern.search(content):
                storage_used = True
                if file_info:
                    file_info['hasStorage'] = True
                elif rel_path not in client_files:
                    client_files.append(rel_path)
            
            # Check for functions usage
            if functions_pattern.search(content):
                functions_used = True
                if file_info:
                    file_info['hasFunctions'] = True
                elif rel_path not in client_files:
                    client_files.append(rel_path)
            
            # Check for LLM usage
            if llm_pattern.search(content):
                llm_used = True
                if file_info:
                    file_info['hasLLM'] = True
                elif rel_path not in client_files:
                    client_files.append(rel_path)
            
            return file_info
            
        except Exception as e:
            log.debug(f"Error scanning file {file_path}: {e}")
            return None
    
    # Walk through source directory
    scanned_files = []
    for file_path in source_dir.rglob('*'):
        if file_path.is_file() and file_path.suffix in extensions:
            if should_ignore_path(file_path):
                continue
            
            file_info = scan_file(file_path)
            if file_info:
                scanned_files.append(file_info)
    
    # Build result
    result = {
        'clientFiles': sorted(list(set(client_files))),
        'usage': {
            'entities': sorted(list(entities_used)),
            'storage': storage_used,
            'functions': functions_used,
            'llm': llm_used
        },
        'importLocations': import_locations,
        'notes': [
            f"Scanned {len(scanned_files)} files with base44Client usage",
            f"Found {len(entities_used)} unique entities used",
            f"Storage API used: {storage_used}",
            f"Functions API used: {functions_used}",
            f"LLM API used: {llm_used}"
        ]
    }
    
    return result

