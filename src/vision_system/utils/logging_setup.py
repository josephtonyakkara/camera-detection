"""Central logging configuration for the vision system."""

from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

from vision_system.models.log_buffer import LogBuffer

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging(
    level: str = "INFO", log_dir: Path | None = None, buffer: LogBuffer | None = None
) -> None:
    """Configure root logging with console, optional rotating file, and web buffer.

    Safe to call once at application start; repeated calls reset handlers.
    """
    root = logging.getLogger()
    root.setLevel(level.upper())
    root.handlers.clear()

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(console)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "vision_system.log", maxBytes=5_000_000, backupCount=3
        )
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(file_handler)

    if buffer is not None:
        root.addHandler(buffer)
