"""Utility functions for backend generation."""
import re
from typing import Dict, List, Any


def to_snake_case(name: str) -> str:
    """Convert PascalCase or camelCase to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1)
    return s2.lower()


def to_kebab_case(name: str) -> str:
    """Convert PascalCase or camelCase to kebab-case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1)
    return s2.lower()


def entity_to_slug(entity_name: str) -> str:
    """Convert entity name to slug for Python modules (snake_case)."""
    if '_' in entity_name:
        return to_snake_case(entity_name)
    return to_snake_case(entity_name)


def entity_to_path(entity_name: str) -> str:
    """Convert entity name to API path (kebab-case for URLs)."""
    if '_' in entity_name:
        return to_snake_case(entity_name)
    return to_kebab_case(entity_name)


def get_entity_store(entity_name: str, storage_plan: Dict[str, Any]) -> str:
    """Get the store type (postgres/mongo) for an entity from storage plan."""
    entities = storage_plan.get("entities", [])
    for entity_entry in entities:
        if entity_entry.get("name") == entity_name:
            return entity_entry.get("store", "postgres")
    return "postgres"  # default


def to_plural_snake_case(name: str) -> str:
    """Convert entity name to plural snake_case for MongoDB collections."""
    singular = entity_to_slug(name)
    # Simple pluralization - add 's' or 'es' for common cases
    if singular.endswith('s') or singular.endswith('x') or singular.endswith('z') or singular.endswith('ch') or singular.endswith('sh'):
        return singular + 'es'
    elif singular.endswith('y') and len(singular) > 1 and singular[-2] not in 'aeiou':
        return singular[:-1] + 'ies'
    else:
        return singular + 's'


