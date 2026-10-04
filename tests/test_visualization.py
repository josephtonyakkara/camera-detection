"""Tests for the overlay renderer."""

from __future__ import annotations

import numpy as np

from vision_system.models.data import DetectionResult, PickTarget, RobotCoordinate
from vision_system.visualization.overlay import draw_overlay


def test_overlay_does_not_mutate_input(detection_result: DetectionResult) -> None:
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    original = image.copy()
    annotated = draw_overlay(image, detection_result, fps=30.0)
    assert np.array_equal(image, original)
    assert annotated.shape == image.shape
    assert annotated.any(), "overlay should have drawn something"


def test_overlay_with_targets_and_empty_result(detection_result: DetectionResult) -> None:
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    target = PickTarget(
        target_id=1,
        coordinate=RobotCoordinate(1.0, 2.0, -3.0),
        class_name="round_part",
        confidence=0.9,
        source_frame_id=1,
    )
    assert draw_overlay(image, detection_result, [target]).any()

    detection_result.detections.clear()
    annotated = draw_overlay(image, detection_result)  # count header only
    assert annotated.any()
