"""Core data structures exchanged between all vision-system modules.

Coordinate convention (image space):
    Origin = top-left of image, X positive right, Y positive down, unit = pixels.
Coordinate convention (robot space):
    Defined by calibration; unit = millimetres unless configured otherwise.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class ProcessingMode(Enum):
    """Frame-processing modes supported by the application loop."""

    LIVE = "live"
    SINGLE_FRAME = "single_frame"
    DEBUG = "debug"


class RobotState(Enum):
    """Explicit robot communication/readiness states."""

    DISCONNECTED = "disconnected"
    CONNECTED = "connected"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"


@dataclass
class FrameData:
    """A single frame captured from a camera."""

    frame_id: int
    timestamp: float
    image: np.ndarray
    width: int
    height: int
    color_format: str = "BGR"


@dataclass
class ProcessedFrame:
    """A pre-processed frame ready for detection."""

    source: FrameData
    image: np.ndarray
    operations: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BoundingBox:
    """Axis-aligned bounding box in image pixels (top-left origin)."""

    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> tuple[float, float]:
        return (self.x + self.width / 2.0, self.y + self.height / 2.0)


@dataclass
class Detection:
    """One detected part instance in image coordinates."""

    class_name: str
    confidence: float
    center_x_px: float
    center_y_px: float
    bounding_box: BoundingBox
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DetectionResult:
    """Structured output of a detector run on one frame.

    An empty ``detections`` list with ``detection_count == 0`` is a valid
    result, not an error.
    """

    frame_id: int
    timestamp: float
    image_width: int
    image_height: int
    detections: list[Detection] = field(default_factory=list)

    @property
    def detection_count(self) -> int:
        return len(self.detections)


@dataclass(frozen=True)
class RobotCoordinate:
    """A position in the robot coordinate system (millimetres)."""

    x: float
    y: float
    z: float


@dataclass
class PickTarget:
    """A robot-compatible pick target derived from a detection."""

    target_id: int
    coordinate: RobotCoordinate
    class_name: str
    confidence: float
    source_frame_id: int
    created_at: float = field(default_factory=time.time)


@dataclass
class RobotStatus:
    """Snapshot of the robot interface state."""

    state: RobotState
    message: str = ""
    last_pick_target_id: int | None = None
