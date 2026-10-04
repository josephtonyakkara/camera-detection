"""Loads and validates reference part datasets from the parts/ directory.

The active part is selected via config (vision.active_part). Swapping the
folder contents or the config value changes the detection target without any
code change.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


class ReferenceDataError(Exception):
    """Raised when the reference dataset is missing or invalid."""


@dataclass
class ReferenceSet:
    """A validated reference dataset for one part class."""

    part_name: str
    directory: Path
    image_paths: list[Path] = field(default_factory=list)

    @property
    def image_count(self) -> int:
        return len(self.image_paths)


def load_reference_set(parts_dir: Path, part_name: str) -> ReferenceSet:
    """Validate and return the reference dataset for ``part_name``.

    Raises:
        ReferenceDataError: if the folder is missing or contains no images.
    """
    directory = parts_dir / part_name
    if not directory.is_dir():
        available = sorted(p.name for p in parts_dir.iterdir() if p.is_dir()) if parts_dir.is_dir() else []
        raise ReferenceDataError(
            f"Reference folder not found: {directory}. Available parts: {available}"
        )
    images = sorted(
        p for p in directory.iterdir() if p.suffix.lower() in _IMAGE_EXTENSIONS
    )
    if not images:
        raise ReferenceDataError(f"No reference images ({sorted(_IMAGE_EXTENSIONS)}) in {directory}")
    logger.info("Loaded reference set '%s' with %d image(s)", part_name, len(images))
    return ReferenceSet(part_name=part_name, directory=directory, image_paths=images)
