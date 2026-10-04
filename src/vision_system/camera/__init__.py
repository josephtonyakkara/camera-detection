"""Camera abstraction layer. Hardware-specific drivers implement CameraInterface."""

from vision_system.camera.base import CameraError, CameraInterface
from vision_system.camera.manager import CameraManager

__all__ = ["CameraError", "CameraInterface", "CameraManager"]
