"""File writer for backend generation."""
from pathlib import Path
from typing import List
from app.generators.backend_gen.types import GeneratedFile


def write_files(files: List[GeneratedFile], out_dir: Path) -> None:
    """
    Write generated files to the output directory.
    
    Args:
        files: List of GeneratedFile objects to write
        out_dir: Base output directory path
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for file in files:
        file_path = out_dir / file.path
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Write file content
        file_path.write_text(file.content, encoding="utf-8")


