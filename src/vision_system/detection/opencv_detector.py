"""Classical OpenCV detector: bright-object segmentation + contour shape matching.

Pipeline per frame:
    grayscale -> blur -> Otsu/fixed threshold -> morphology -> external contours
    -> area-fraction filter (derived from references) -> Hu-moment shape match
    -> Detection per accepted contour.

Scale-invariance: reference images and live frames may differ in resolution,
so areas are compared as fractions of the image area, and cv2.matchShapes is
scale/rotation invariant by construction.

Tunables come from vision.detection_params (see CONFIGURATION.md).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import cv2
import numpy as np

from vision_system.detection.base import DetectorError, PartDetector
from vision_system.detection.reference_loader import ReferenceSet
from vision_system.models.data import (
    BoundingBox,
    Detection,
    DetectionResult,
    ProcessedFrame,
)

logger = logging.getLogger(__name__)

_DEFAULT_PARAMS: dict[str, Any] = {
    "blur_kernel": 5,        # odd Gaussian kernel size; 0 disables
    "threshold": "otsu",     # "otsu" or a fixed 0-255 integer
    "invert": False,         # True if parts are darker than the background
    "morph_kernel": 5,       # opening/closing kernel; 0 disables
    "area_tolerance": 2.5,   # accepted area range = reference range widened by this factor
    "min_area_px": 400,      # absolute noise floor in pixels
    "min_reference_area_fraction": 0.01,  # a reference part must fill >=1% of its image
    # scale=3: live blur/tilt vs refs gives d up to ~0.2 -> conf >=0.6; cross-class d>=0.3 -> <0.6
    "match_scale": 3.0,      # confidence = 1 / (1 + match_scale * shape_distance)
}


@dataclass(frozen=True)
class _ReferenceShape:
    contour: np.ndarray
    area_fraction: float


def _binarize(image: np.ndarray, params: dict[str, Any]) -> np.ndarray:
    """Grayscale + blur + threshold + morphology -> binary mask of candidate parts."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blur = int(params["blur_kernel"])
    if blur > 0:
        gray = cv2.GaussianBlur(gray, (blur | 1, blur | 1), 0)
    flags = cv2.THRESH_BINARY_INV if params["invert"] else cv2.THRESH_BINARY
    if params["threshold"] == "otsu":
        _, mask = cv2.threshold(gray, 0, 255, flags + cv2.THRESH_OTSU)
    else:
        _, mask = cv2.threshold(gray, int(params["threshold"]), 255, flags)
    kernel_size = int(params["morph_kernel"])
    if kernel_size > 0:
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    return mask


def _touches_border(contour: np.ndarray, shape: tuple[int, ...], margin: int = 2) -> bool:
    x, y, w, h = cv2.boundingRect(contour)
    height, width = shape[:2]
    return x <= margin or y <= margin or x + w >= width - margin or y + h >= height - margin


class OpenCVDetector(PartDetector):
    """Reference-image-driven classical CV detector."""

    def __init__(self) -> None:
        self._references: ReferenceSet | None = None
        self._confidence_threshold: float = 0.6
        self._params: dict[str, Any] = dict(_DEFAULT_PARAMS)
        self._shapes: list[_ReferenceShape] = []
        self._area_bounds: tuple[float, float] = (0.0, 1.0)

    def configure(
        self,
        references: ReferenceSet,
        confidence_threshold: float,
        params: dict[str, Any] | None = None,
    ) -> None:
        if references.image_count == 0:
            raise DetectorError("Reference set contains no images")
        self._references = references
        self._confidence_threshold = confidence_threshold
        self._params = {**_DEFAULT_PARAMS, **(params or {})}

        self._shapes = []
        for path in references.image_paths:
            image = cv2.imread(str(path))
            if image is None:
                logger.warning("Skipping unreadable reference image %s", path.name)
                continue
            shape = self._extract_reference_shape(image, path.name)
            if shape is not None:
                self._shapes.append(shape)
        if not self._shapes:
            raise DetectorError(
                f"No usable part contour found in any reference image of "
                f"'{references.part_name}'; check lighting/threshold params"
            )
        fractions = [s.area_fraction for s in self._shapes]
        tolerance = float(self._params["area_tolerance"])
        self._area_bounds = (min(fractions) / tolerance, max(fractions) * tolerance)
        logger.info(
            "OpenCVDetector configured for part '%s': %d/%d references usable, "
            "area fraction bounds (%.4f, %.4f)",
            references.part_name,
            len(self._shapes),
            references.image_count,
            *self._area_bounds,
        )

    def _extract_reference_shape(self, image: np.ndarray, name: str) -> _ReferenceShape | None:
        mask = _binarize(image, self._params)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        # a reference part must be fully visible: border-touching blobs are background clutter
        candidates = [c for c in contours if not _touches_border(c, image.shape)]
        if not candidates:
            if contours:
                logger.warning(
                    "Reference %s: all contours touch the image border; "
                    "recapture with the part fully in view",
                    name,
                )
            else:
                logger.warning("No contour found in reference %s", name)
            return None
        contour = max(candidates, key=cv2.contourArea)
        area = cv2.contourArea(contour)
        image_area = image.shape[0] * image.shape[1]
        min_area = max(
            float(self._params["min_area_px"]),
            float(self._params["min_reference_area_fraction"]) * image_area,
        )
        if area < min_area:
            logger.warning(
                "Reference %s: largest fully-visible contour too small (%.0f px < %.0f); "
                "recapture with the part closer/fully in view",
                name,
                area,
                min_area,
            )
            return None
        return _ReferenceShape(contour=contour, area_fraction=area / image_area)

    def detect(self, frame: ProcessedFrame) -> DetectionResult:
        if self._references is None:
            raise DetectorError("Detector not configured; call configure() first")

        mask = _binarize(frame.image, self._params)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        image_area = frame.image.shape[0] * frame.image.shape[1]
        detections: list[Detection] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < float(self._params["min_area_px"]):
                continue
            fraction = area / image_area
            if not (self._area_bounds[0] <= fraction <= self._area_bounds[1]):
                continue
            distance = min(
                cv2.matchShapes(contour, ref.contour, cv2.CONTOURS_MATCH_I1, 0.0)
                for ref in self._shapes
            )
            confidence = 1.0 / (1.0 + float(self._params["match_scale"]) * distance)
            if confidence < self._confidence_threshold:
                continue
            moments = cv2.moments(contour)
            if moments["m00"] == 0:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            detections.append(
                Detection(
                    class_name=self._references.part_name,
                    confidence=round(confidence, 4),
                    center_x_px=moments["m10"] / moments["m00"],
                    center_y_px=moments["m01"] / moments["m00"],
                    bounding_box=BoundingBox(x, y, w, h),
                    metadata={"area_px": area, "shape_distance": round(distance, 4)},
                )
            )

        return DetectionResult(
            frame_id=frame.source.frame_id,
            timestamp=frame.source.timestamp,
            image_width=frame.source.width,
            image_height=frame.source.height,
            detections=detections,
        )
