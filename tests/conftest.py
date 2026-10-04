"""Shared test fixtures."""

from __future__ import annotations

import time

import numpy as np
import pytest

from vision_system.models.data import (
    BoundingBox,
    Detection,
    DetectionResult,
    FrameData,
)


@pytest.fixture
def frame() -> FrameData:
    image = np.zeros((720, 1280, 3), dtype=np.uint8)
    return FrameData(
        frame_id=1, timestamp=time.time(), image=image, width=1280, height=720
    )


def make_detection(cx: float, cy: float, confidence: float = 0.9) -> Detection:
    return Detection(
        class_name="round_part",
        confidence=confidence,
        center_x_px=cx,
        center_y_px=cy,
        bounding_box=BoundingBox(int(cx) - 10, int(cy) - 10, 20, 20),
    )


@pytest.fixture
def detection_result() -> DetectionResult:
    return DetectionResult(
        frame_id=1,
        timestamp=time.time(),
        image_width=1280,
        image_height=720,
        detections=[
            make_detection(100, 50),
            make_detection(30, 40, confidence=0.7),
            make_detection(150, 10, confidence=0.95),
        ],
    )
