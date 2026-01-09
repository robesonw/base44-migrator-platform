"""Utility functions for client adapter generation."""
import re
from typing import Dict, List, Any


def to_kebab_case(name: str) -> str:
    """Convert PascalCase or camelCase to kebab-case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1)
    return s2.lower()


def entity_to_slug(entity_name: str) -> str:
    """Convert entity name to API path slug (kebab-case for URLs)."""
    return to_kebab_case(entity_name)


def detect_language(source_dir, ui_contract: Dict[str, Any]) -> str:
    """Detect if source uses TypeScript or JavaScript."""
    # Check framework info first
    framework = ui_contract.get("framework", {})
    if framework.get("name") in ["nextjs", "vite"]:
        # Check for TypeScript config files
        from pathlib import Path
        ts_configs = ["tsconfig.json", "jsconfig.json"]
        for config in ts_configs:
            if (source_dir / config).exists():
                try:
                    content = (source_dir / config).read_text()
                    if '"compilerOptions"' in content or '"allowJs"' in content:
                        # Check if .ts files exist in src
                        if any((source_dir / "src").rglob("*.ts")) or any((source_dir / "src").rglob("*.tsx")):
                            return "ts"
                except:
                    pass
    
    # Default to js
    return "js"

