"""Orchestrator for backend code generation."""
import json
from pathlib import Path
from typing import List, Dict, Any
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
    render_repos_base,
    render_repos_postgres_repo,
    render_repos_mongo_repo,
)
from app.generators.backend_gen.render_entity import (
    render_entity_model,
    render_entity_router,
)
from app.generators.backend_gen.utils import (
    entity_to_slug,
    entity_to_path,
    get_entity_store,
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
    
    # Build entity store mapping
    entity_store_map = {}
    for entity_entry in storage_plan.entities:
        entity_store_map[entity_entry["name"]] = entity_entry.get("store", "postgres")
    
    # Generate base files
    files = [
        GeneratedFile(path="app/api/__init__.py", content=render_api_init()),
        GeneratedFile(path="app/api/health.py", content=render_api_health()),
        GeneratedFile(path="app/core/config.py", content=render_core_config()),
        GeneratedFile(path="app/db/postgres.py", content=render_db_postgres()),
        GeneratedFile(path="app/db/mongo.py", content=render_db_mongo()),
        GeneratedFile(path="app/repos/__init__.py", content="# Repositories package\n"),
        GeneratedFile(path="app/repos/base.py", content=render_repos_base()),
        GeneratedFile(path="app/repos/postgres_repo.py", content=render_repos_postgres_repo()),
        GeneratedFile(path="app/repos/mongo_repo.py", content=render_repos_mongo_repo()),
        GeneratedFile(path="app/models/__init__.py", content="# Models package\n"),
        GeneratedFile(path="app/api/entities/__init__.py", content="# Entity routers package\n"),
        GeneratedFile(path="requirements.txt", content=render_requirements_txt()),
        GeneratedFile(path="Dockerfile", content=render_dockerfile()),
        GeneratedFile(path="docker-compose.yml", content=render_docker_compose()),
        GeneratedFile(path="README.md", content=render_readme()),
    ]
    
    # Generate entity-specific files
    entity_routers = []
    for entity in entities:
        entity_name = entity.name
        entity_slug = entity_to_slug(entity_name)
        path_slug = entity_to_path(entity_name)
        store_type = entity_store_map.get(entity_name, "postgres")
        
        # Generate model
        model_content = render_entity_model(entity_name, entity.fields)
        files.append(GeneratedFile(
            path=f"app/models/{entity_slug}.py",
            content=model_content
        ))
        
        # Generate router
        router_content = render_entity_router(
            entity_name, entity_slug, path_slug, store_type, entity.fields
        )
        files.append(GeneratedFile(
            path=f"app/api/entities/{entity_slug}.py",
            content=router_content
        ))
        
        entity_routers.append({
            "entity_name": entity_name,
            "entity_slug": entity_slug,
            "path_slug": path_slug,
        })
    
    # Generate main.py with entity routers
    files.append(GeneratedFile(
        path="app/main.py",
        content=render_main_py(entity_routers)
    ))
    
    # Write files to disk
    write_files(files, out_dir)
    
    return files

