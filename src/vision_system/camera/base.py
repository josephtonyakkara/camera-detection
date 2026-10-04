"""Abstract camera interface.

The rest of the application depends only on this interface, never on a
specific camera SDK. Camera implementations must not contain detection,
coordinate, or robot logic.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from vision_system.config.models import CameraConfig
from vision_system.models.data import FrameData


class CameraError(Exception):
    """Raised for camera connection or acquisition failures."""


class CameraInterface(ABC):
    """Common interface every camera driver must implement."""

    @abstractmethod
    def open(self, config: CameraConfig) -> None:
        """Open the device and apply resolution/FPS settings.

        Raises:
            CameraError: if the device cannot be opened or configured.
        """

    @abstractmethod
    def get_frame(self) -> FrameData:
        """Retrieve the latest frame.

        Raises:
            CameraError: if acquisition fails or the camera is not open.
        """

    @abstractmethod
    def is_open(self) -> bool:
        """Return True while the device is connected and streaming."""

    @abstractmethod
    def close(self) -> None:
        """Stop streaming and release the device. Must be idempotent."""
