"""Project-root-based path resolution.

All modules must resolve paths through this module instead of relying on the
current working directory.
"""

from __future__ import annotations

from pathlib import Path

# src/vision_system/utils/paths.py -> project root is 3 levels up from this file's parent
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

CONFIG_DIR: Path = PROJECT_ROOT / "config"
PARTS_DIR: Path = PROJECT_ROOT / "parts"
CALIBRATION_DIR: Path = PROJECT_ROOT / "calibration"
LOGS_DIR: Path = PROJECT_ROOT / "logs"
DOCS_DIR: Path = PROJECT_ROOT / "docs_camera"


def resolve(path: str | Path) -> Path:
    """Resolve ``path`` relative to the project root unless it is absolute."""
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p
