"""Orchestrator for backend code generation."""
import json
from pathlib import Path
from typing import List
from app.generators.backend_gen.types import (
    EntitySpec,
    StoragePlan,
    JobInput,
    GeneratedFile,
)
from app.generators.backend_gen.render import (
    render_main_py,
    render_api_init,
    render_api_health,
    render_core_config,
    render_requirements_txt,
    render_dockerfile,
    render_docker_compose,
    render_readme,
    render_db_postgres,
    render_db_mongo,
)
from app.generators.backend_gen.writer import write_files


def generate_backend(
    job_id: str,
    ui_contract_path: Path,
    storage_plan_path: Path,
    out_dir: Path,
) -> List[GeneratedFile]:
    """
    Generate backend skeleton code.
    
    Args:
        job_id: Job identifier
        ui_contract_path: Path to ui-contract.json file
        storage_plan_path: Path to storage-plan.json file
        out_dir: Output directory for generated files
        
    Returns:
        List of GeneratedFile objects
    """
    # Read ui-contract.json
    with open(ui_contract_path, "r", encoding="utf-8") as f:
        ui_contract = json.load(f)
    
    # Read storage-plan.json
    with open(storage_plan_path, "r", encoding="utf-8") as f:
        storage_plan_data = json.load(f)
    
    # Parse entities from ui-contract
    entities = []
    for entity_data in ui_contract.get("entities", []):
        entity = EntitySpec(
            name=entity_data["name"],
            source_path=entity_data.get("sourcePath", ""),
            fields=entity_data.get("fields", []),
            relationships=entity_data.get("relationships", []),
            raw_shape_hint=entity_data.get("rawShapeHint", "fields-array"),
        )
        entities.append(entity)
    
    # Parse storage plan
    storage_plan = StoragePlan(
        mode=storage_plan_data.get("mode", "postgres"),
        entities=storage_plan_data.get("entities", []),
    )
    
    # Generate all files
    files = [
        GeneratedFile(path="app/main.py", content=render_main_py()),
        GeneratedFile(path="app/api/__init__.py", content=render_api_init()),
        GeneratedFile(path="app/api/health.py", content=render_api_health()),
        GeneratedFile(path="app/core/config.py", content=render_core_config()),
        GeneratedFile(path="app/db/postgres.py", content=render_db_postgres()),
        GeneratedFile(path="app/db/mongo.py", content=render_db_mongo()),
        GeneratedFile(path="requirements.txt", content=render_requirements_txt()),
        GeneratedFile(path="Dockerfile", content=render_dockerfile()),
        GeneratedFile(path="docker-compose.yml", content=render_docker_compose()),
        GeneratedFile(path="README.md", content=render_readme()),
    ]
    
    # Write files to disk
    write_files(files, out_dir)
    
    return files

