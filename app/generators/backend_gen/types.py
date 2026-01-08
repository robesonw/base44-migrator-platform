"""Dataclasses for backend generation."""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class EntitySpec:
    """Entity specification from ui-contract.json."""
    name: str
    source_path: str
    fields: List[Dict[str, Any]]
    relationships: List[Dict[str, Any]]
    raw_shape_hint: str


@dataclass
class StoragePlan:
    """Storage plan from storage-plan.json."""
    mode: str  # "postgres", "mongo", or "hybrid"
    entities: List[Dict[str, str]]  # List of {"name": str, "store": str, "reason": str}


@dataclass
class JobInput:
    """Input data for backend generation."""
    entities: List[EntitySpec]
    storage_plan: StoragePlan


@dataclass
class GeneratedFile:
    """Represents a generated file."""
    path: str  # Relative path from output directory
    content: str  # File contents

