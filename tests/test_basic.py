"""
Basic pytest smoke tests for the project.
"""

import importlib.util
from pathlib import Path


def test_project_root_exists():
    """Verify the project root exists."""
    assert Path(".").exists()


def test_session_manager_exists():
    """Verify session_manager.py exists."""
    assert Path("session_manager.py").exists()


def test_session_manager_is_importable():
    """Verify session_manager.py has valid Python syntax."""
    spec = importlib.util.spec_from_file_location(
        "session_manager",
        Path("session_manager.py"),
    )

    assert spec is not None
    assert spec.loader is not None