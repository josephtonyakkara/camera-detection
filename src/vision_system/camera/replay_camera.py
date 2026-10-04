"""Replay camera: serves images from a folder through CameraInterface.

Used for end-to-end integration tests and development without physical
hardware (camera.type: replay). Images loop forever in sorted order.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import cv2
import numpy as np

from vision_system.camera.base import CameraError, CameraInterface
from vision_system.config.models import CameraConfig
from vision_system.models.data import FrameData
from vision_system.utils.paths import resolve

logger = logging.getLogger(__name__)

_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


class ReplayCamera(CameraInterface):
    """Loops over image files from camera.replay_dir."""

    def __init__(self) -> None:
        self._images: list[np.ndarray] = []
        self._open = False
        self._frame_counter = 0

    def open(self, config: CameraConfig) -> None:
        directory = resolve(config.replay_dir)
        if not directory.is_dir():
            raise CameraError(f"Replay directory not found: {directory}")
        paths = sorted(
            p for p in directory.iterdir() if p.suffix.lower() in _IMAGE_EXTENSIONS
        )
        images = [img for img in (cv2.imread(str(p)) for p in paths) if img is not None]
        if not images:
            raise CameraError(f"No readable images in replay directory: {directory}")
        self._images = images
        self._open = True
        logger.info("Replay camera opened with %d image(s) from %s", len(images), directory)

    def get_frame(self) -> FrameData:
        if not self._open:
            raise CameraError("Replay camera is not open")
        image = self._images[self._frame_counter % len(self._images)]
        self._frame_counter += 1
        height, width = image.shape[:2]
        return FrameData(
            frame_id=self._frame_counter,
            timestamp=time.time(),
            image=image,
            width=width,
            height=height,
            color_format="BGR",
        )

    def is_open(self) -> bool:
        return self._open

    def close(self) -> None:
        self._open = False
