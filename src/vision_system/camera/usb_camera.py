"""USB camera driver based on OpenCV VideoCapture."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import cv2
import numpy as np

from vision_system.camera.base import CameraError, CameraInterface
from vision_system.config.models import CameraConfig
from vision_system.models.data import FrameData

logger = logging.getLogger(__name__)

# MSMF (Windows default) can hang for minutes opening some external UVC cameras;
# DirectShow opens them immediately.
_BACKENDS = {
    "auto": cv2.CAP_ANY,
    "dshow": cv2.CAP_DSHOW,
    "msmf": cv2.CAP_MSMF,
    "v4l2": cv2.CAP_V4L2,
}


@dataclass(frozen=True)
class CameraProbe:
    """Result of probing one USB device index."""

    device_index: int
    width: int
    height: int
    snapshot: np.ndarray | None = None


def enumerate_usb_cameras(max_index: int = 10, with_snapshot: bool = False) -> list[CameraProbe]:
    """Probe device indices 0..max_index-1 and return the cameras that respond.

    Uses DirectShow on probing for fast failure on absent indices (Windows).
    """
    found: list[CameraProbe] = []
    for index in range(max_index):
        capture = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        try:
            if not capture.isOpened():
                continue
            ok, image = capture.read()
            if not ok or image is None:
                continue
            height, width = image.shape[:2]
            found.append(
                CameraProbe(
                    device_index=index,
                    width=width,
                    height=height,
                    snapshot=image if with_snapshot else None,
                )
            )
        finally:
            capture.release()
    return found


class USBCamera(CameraInterface):
    """RGB USB webcam accessed through cv2.VideoCapture."""

    def __init__(self) -> None:
        self._capture: cv2.VideoCapture | None = None
        self._frame_counter: int = 0

    def open(self, config: CameraConfig) -> None:
        backend = _BACKENDS.get(config.backend)
        if backend is None:
            raise CameraError(
                f"Unknown camera backend {config.backend!r}; expected one of {sorted(_BACKENDS)}"
            )
        logger.info(
            "Opening USB camera %d (backend=%s) ...", config.device_index, config.backend
        )
        capture = cv2.VideoCapture(config.device_index, backend)
        if not capture.isOpened():
            raise CameraError(f"Cannot open USB camera at index {config.device_index}")
        capture.set(cv2.CAP_PROP_FRAME_WIDTH, config.width)
        capture.set(cv2.CAP_PROP_FRAME_HEIGHT, config.height)
        capture.set(cv2.CAP_PROP_FPS, config.fps)
        for _ in range(max(0, config.warmup_frames)):  # let auto-exposure settle
            capture.read()
        self._capture = capture
        logger.info(
            "USB camera %d opened (%dx%d @ %d fps requested)",
            config.device_index,
            config.width,
            config.height,
            config.fps,
        )

    def get_frame(self) -> FrameData:
        if self._capture is None:
            raise CameraError("Camera is not open")
        ok, image = self._capture.read()
        if not ok or image is None:
            raise CameraError("Frame acquisition failed")
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
        return self._capture is not None and self._capture.isOpened()

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()
            self._capture = None
            logger.info("USB camera released")
