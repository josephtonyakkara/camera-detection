"""Camera lifecycle management: driver selection, reconnection, clean shutdown."""

from __future__ import annotations

import logging
import time

from vision_system.camera.base import CameraError, CameraInterface
from vision_system.config.models import CameraConfig
from vision_system.models.data import FrameData

logger = logging.getLogger(__name__)


def create_camera(camera_type: str) -> CameraInterface:
    """Factory returning a camera driver for the configured type."""
    if camera_type == "usb":
        # imported lazily so tests without OpenCV can still use the manager
        from vision_system.camera.usb_camera import USBCamera

        return USBCamera()
    if camera_type == "replay":
        from vision_system.camera.replay_camera import ReplayCamera

        return ReplayCamera()
    raise CameraError(f"Unknown camera type: {camera_type!r}")


class CameraManager:
    """Owns a camera driver and adds reconnect/error handling on top of it."""

    def __init__(self, config: CameraConfig, camera: CameraInterface | None = None) -> None:
        self._config = config
        self._camera = camera if camera is not None else create_camera(config.type)

    def start(self) -> None:
        """Open the camera, retrying per the configured reconnect policy."""
        last_error: CameraError | None = None
        for attempt in range(1, self._config.reconnect_attempts + 1):
            try:
                self._camera.open(self._config)
                logger.info("Camera started (attempt %d)", attempt)
                return
            except CameraError as exc:
                last_error = exc
                logger.warning("Camera open attempt %d failed: %s", attempt, exc)
                time.sleep(self._config.reconnect_delay_s)
        raise CameraError(f"Camera could not be started: {last_error}")

    def get_frame(self) -> FrameData:
        """Return the latest frame; attempts one reconnect on failure."""
        try:
            return self._camera.get_frame()
        except CameraError:
            logger.warning("Frame acquisition failed; attempting reconnect")
            self._camera.close()
            self.start()
            return self._camera.get_frame()

    def is_running(self) -> bool:
        return self._camera.is_open()

    def stop(self) -> None:
        self._camera.close()
        logger.info("Camera stopped")
