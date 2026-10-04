"""Draws detection results onto frames for the debug window and web stream.

Pure presentation: consumes the shared data models, never mutates them.
"""

from __future__ import annotations

import cv2
import numpy as np

from vision_system.models.data import DetectionResult, PickTarget

_GREEN = (0, 255, 0)
_YELLOW = (0, 220, 255)
_WHITE = (255, 255, 255)


def draw_overlay(
    image: np.ndarray,
    result: DetectionResult,
    targets: list[PickTarget] | None = None,
    fps: float | None = None,
) -> np.ndarray:
    """Return a copy of ``image`` annotated with boxes, centers, count, and fps."""
    out = image.copy()

    for detection in result.detections:
        box = detection.bounding_box
        cv2.rectangle(out, (box.x, box.y), (box.x + box.width, box.y + box.height), _GREEN, 2)
        cx, cy = int(detection.center_x_px), int(detection.center_y_px)
        cv2.drawMarker(out, (cx, cy), _GREEN, cv2.MARKER_CROSS, 14, 2)
        cv2.putText(
            out,
            f"{detection.class_name} {detection.confidence:.2f} ({cx},{cy})",
            (box.x, max(box.y - 8, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            _GREEN,
            1,
        )

    for target in targets or []:
        coord = target.coordinate
        cv2.putText(
            out,
            f"T{target.target_id}: ({coord.x:.1f}, {coord.y:.1f}, {coord.z:.1f})",
            (10, out.shape[0] - 12 - 18 * (target.target_id % 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            _YELLOW,
            1,
        )

    header = f"Parts: {result.detection_count}"
    if fps is not None:
        header += f"  |  {fps:.1f} fps"
    cv2.putText(out, header, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, _WHITE, 2)
    return out
