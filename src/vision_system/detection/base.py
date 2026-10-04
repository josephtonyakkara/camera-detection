"""Abstract part-detector interface.

Detectors receive processed frames and return structured DetectionResults.
They must not access the camera, the robot, or coordinate calibration.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from vision_system.detection.reference_loader import ReferenceSet
from vision_system.models.data import DetectionResult, ProcessedFrame


class DetectorError(Exception):
    """Raised when a detector cannot be configured or run."""


class PartDetector(ABC):
    """Common interface for all detection implementations (OpenCV, YOLO, ...)."""

    @abstractmethod
    def configure(
        self,
        references: ReferenceSet,
        confidence_threshold: float,
        params: dict[str, Any] | None = None,
    ) -> None:
        """Prepare the detector for the given reference part dataset.

        ``params`` carries implementation-specific tuning from
        vision.detection_params; unknown keys must be ignored or rejected
        explicitly by the implementation.

        Raises:
            DetectorError: if the reference data is unusable.
        """

    @abstractmethod
    def detect(self, frame: ProcessedFrame) -> DetectionResult:
        """Detect all instances of the configured part in the frame.

        Zero detections is a valid result (count=0, empty list), not an error.
        """
