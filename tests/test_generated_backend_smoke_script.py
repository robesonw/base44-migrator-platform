"""Lightweight test for generated backend smoke test scripts."""
import os
from pathlib import Path


def test_smoke_test_scripts_exist():
    """Test that smoke test scripts exist and are in the correct location."""
    script_dir = Path(__file__).parent.parent / "scripts"
    
    bash_script = script_dir / "test_generated_backend.sh"
    ps1_script = script_dir / "test_generated_backend.ps1"
    
    assert bash_script.exists(), f"Bash script not found: {bash_script}"
    assert ps1_script.exists(), f"PowerShell script not found: {ps1_script}"


def test_smoke_payload_helper_exists():
    """Test that smoke_payload.py helper exists."""
    helper_path = Path(__file__).parent.parent / "app" / "generators" / "backend_gen" / "smoke_payload.py"
    assert helper_path.exists(), f"smoke_payload.py not found: {helper_path}"


def test_smoke_payload_helper_importable():
    """Test that smoke_payload helper can be imported."""
    try:
        from app.generators.backend_gen.smoke_payload import build_minimal_payload
        assert callable(build_minimal_payload), "build_minimal_payload should be callable"
    except ImportError as e:
        assert False, f"Failed to import build_minimal_payload: {e}"


def test_scripts_reference_correct_paths():
    """Test that scripts reference correct Python paths."""
    script_dir = Path(__file__).parent.parent / "scripts"
    
    # Read bash script
    bash_script = script_dir / "test_generated_backend.sh"
    bash_content = bash_script.read_text(encoding="utf-8")
    
    # Check that it references the correct modules
    assert "from app.agents.impl_intake import RepoIntakeAgent" in bash_content or "app.agents.impl_intake" in bash_content
    assert "from app.agents.impl_build import BackendBuilderAgent" in bash_content or "app.agents.impl_build" in bash_content
    assert "from app.generators.backend_gen.smoke_payload import build_minimal_payload" in bash_content or "app.generators.backend_gen.smoke_payload" in bash_content
    
    # Read PowerShell script
    ps1_script = script_dir / "test_generated_backend.ps1"
    ps1_content = ps1_script.read_text(encoding="utf-8")
    
    # Check that it references the correct modules
    assert "from app.agents.impl_intake import RepoIntakeAgent" in ps1_content or "app.agents.impl_intake" in ps1_content
    assert "from app.agents.impl_build import BackendBuilderAgent" in ps1_content or "app.agents.impl_build" in ps1_content
    assert "from app.generators.backend_gen.smoke_payload import build_minimal_payload" in ps1_content or "app.generators.backend_gen.smoke_payload" in ps1_content

