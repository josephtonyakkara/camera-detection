"""Tests for reference dataset loading and the OpenCV contour detector.

Detector tests use synthetic images: bright shapes on dark background,
matching the confirmed physical setup (shiny part, dark workspace).
"""

from __future__ import annotations

import time
from pathlib import Path

import cv2
import numpy as np
import pytest

from vision_system.detection.base import DetectorError
from vision_system.detection.opencv_detector import OpenCVDetector
from vision_system.detection.reference_loader import (
    ReferenceDataError,
    load_reference_set,
)
from vision_system.models.data import FrameData, ProcessedFrame

BG = 30  # dark background gray level
FG = 220  # bright part gray level


def make_image(shapes: list[tuple[str, int, int, int]], size=(720, 1280)) -> np.ndarray:
    """Draw bright shapes: (kind, cx, cy, radius) with kind 'circle'|'square'|'bar'."""
    image = np.full((*size, 3), BG, dtype=np.uint8)
    for kind, cx, cy, r in shapes:
        color = (FG, FG, FG)
        if kind == "circle":
            cv2.circle(image, (cx, cy), r, color, -1)
        elif kind == "square":
            cv2.rectangle(image, (cx - r, cy - r), (cx + r, cy + r), color, -1)
        elif kind == "bar":  # elongated rectangle, same-ish area as circle r
            half_w, half_h = 6 * r // 2, r // 3
            cv2.rectangle(image, (cx - half_w, cy - half_h), (cx + half_w, cy + half_h), color, -1)
    return image


def make_frame(image: np.ndarray, frame_id: int = 1) -> ProcessedFrame:
    height, width = image.shape[:2]
    source = FrameData(
        frame_id=frame_id, timestamp=time.time(), image=image, width=width, height=height
    )
    return ProcessedFrame(source=source, image=image)


def write_references(tmp_path: Path, count: int = 2, radius: int = 90) -> Path:
    part_dir = tmp_path / "round_part"
    part_dir.mkdir(parents=True)
    for i in range(count):
        image = make_image([("circle", 640, 360, radius + 5 * i)])
        cv2.imwrite(str(part_dir / f"reference_{i:02d}.jpg"), image)
    return tmp_path


def make_detector(tmp_path: Path, threshold: float = 0.6, **params) -> OpenCVDetector:
    detector = OpenCVDetector()
    references = load_reference_set(write_references(tmp_path), "round_part")
    detector.configure(references, threshold, params or None)
    return detector


# --- reference loader (filesystem only) ---


def test_load_valid_reference_set(tmp_path: Path) -> None:
    refs = load_reference_set(write_references(tmp_path, count=3), "round_part")
    assert refs.part_name == "round_part"
    assert refs.image_count == 3


def test_missing_part_folder_lists_available(tmp_path: Path) -> None:
    write_references(tmp_path)
    with pytest.raises(ReferenceDataError, match="round_part"):
        load_reference_set(tmp_path, "square_part")


def test_empty_part_folder_rejected(tmp_path: Path) -> None:
    (tmp_path / "round_part").mkdir()
    with pytest.raises(ReferenceDataError, match="No reference images"):
        load_reference_set(tmp_path, "round_part")


# --- detector ---


def test_detector_requires_configuration() -> None:
    detector = OpenCVDetector()
    with pytest.raises(DetectorError, match="not configured"):
        detector.detect(make_frame(make_image([])))


def test_unreadable_references_rejected(tmp_path: Path) -> None:
    part_dir = tmp_path / "round_part"
    part_dir.mkdir()
    (part_dir / "reference_01.jpg").write_bytes(b"\xff\xd8\xff\xd9")
    detector = OpenCVDetector()
    with pytest.raises(DetectorError, match="No usable part contour"):
        detector.configure(load_reference_set(tmp_path, "round_part"), 0.6)


def test_detects_single_circle(tmp_path: Path) -> None:
    detector = make_detector(tmp_path)
    result = detector.detect(make_frame(make_image([("circle", 400, 300, 90)])))
    assert result.detection_count == 1
    detection = result.detections[0]
    assert detection.class_name == "round_part"
    assert detection.confidence >= 0.9
    assert detection.center_x_px == pytest.approx(400, abs=3)
    assert detection.center_y_px == pytest.approx(300, abs=3)
    box = detection.bounding_box
    assert box.x < 400 < box.x + box.width
    assert box.y < 300 < box.y + box.height


def test_detects_multiple_circles(tmp_path: Path) -> None:
    detector = make_detector(tmp_path)
    image = make_image(
        [("circle", 200, 200, 85), ("circle", 640, 400, 95), ("circle", 1050, 250, 90)]
    )
    result = detector.detect(make_frame(image))
    assert result.detection_count == 3
    centers = sorted((d.center_x_px, d.center_y_px) for d in result.detections)
    assert centers[0][0] == pytest.approx(200, abs=3)
    assert centers[1][0] == pytest.approx(640, abs=3)
    assert centers[2][0] == pytest.approx(1050, abs=3)


def test_empty_frame_returns_zero_count(tmp_path: Path) -> None:
    detector = make_detector(tmp_path)
    result = detector.detect(make_frame(make_image([])))
    assert result.detection_count == 0
    assert result.detections == []


def test_wrong_shape_rejected(tmp_path: Path) -> None:
    # bar has circle-comparable area but very different shape
    detector = make_detector(tmp_path)
    result = detector.detect(make_frame(make_image([("bar", 640, 360, 90)])))
    assert result.detection_count == 0


def test_too_small_and_too_large_blobs_rejected(tmp_path: Path) -> None:
    detector = make_detector(tmp_path)
    image = make_image([("circle", 300, 300, 8), ("circle", 640, 360, 340)])
    result = detector.detect(make_frame(image))
    assert result.detection_count == 0


def test_detection_scale_invariance_across_resolutions(tmp_path: Path) -> None:
    # references at 720p, frame at 480p with proportionally smaller circle
    detector = make_detector(tmp_path)
    image = make_image([("circle", 320, 240, 60)], size=(480, 640))
    result = detector.detect(make_frame(image))
    assert result.detection_count == 1


def test_invert_param_detects_dark_parts(tmp_path: Path) -> None:
    part_dir = tmp_path / "dark_part"
    part_dir.mkdir()
    dark_ref = np.full((720, 1280, 3), FG, dtype=np.uint8)
    cv2.circle(dark_ref, (640, 360), 90, (BG, BG, BG), -1)
    cv2.imwrite(str(part_dir / "reference_01.jpg"), dark_ref)

    detector = OpenCVDetector()
    detector.configure(load_reference_set(tmp_path, "dark_part"), 0.6, {"invert": True})
    frame_img = np.full((720, 1280, 3), FG, dtype=np.uint8)
    cv2.circle(frame_img, (500, 300), 88, (BG, BG, BG), -1)
    result = detector.detect(make_frame(frame_img))
    assert result.detection_count == 1


def test_reference_ignores_border_touching_clutter(tmp_path: Path) -> None:
    # clutter at the image edge is larger than the part but must not become the reference
    part_dir = tmp_path / "round_part"
    part_dir.mkdir()
    image = make_image([("circle", 400, 360, 90)])
    cv2.rectangle(image, (980, 300), (1279, 719), (FG, FG, FG), -1)  # border blob
    cv2.imwrite(str(part_dir / "reference_01.jpg"), image)

    detector = OpenCVDetector()
    detector.configure(load_reference_set(tmp_path, "round_part"), 0.6)
    result = detector.detect(make_frame(make_image([("circle", 300, 300, 88)])))
    assert result.detection_count == 1  # circle reference was used, not the clutter


def test_reference_with_only_border_contours_rejected(tmp_path: Path) -> None:
    part_dir = tmp_path / "round_part"
    part_dir.mkdir()
    image = make_image([])
    cv2.rectangle(image, (0, 0), (200, 719), (FG, FG, FG), -1)  # touches border
    cv2.imwrite(str(part_dir / "reference_01.jpg"), image)

    detector = OpenCVDetector()
    with pytest.raises(DetectorError, match="No usable part contour"):
        detector.configure(load_reference_set(tmp_path, "round_part"), 0.6)


def test_tiny_reference_blob_rejected(tmp_path: Path) -> None:
    # blob above min_area_px but below min_reference_area_fraction of the image
    part_dir = tmp_path / "round_part"
    part_dir.mkdir()
    cv2.imwrite(
        str(part_dir / "reference_01.jpg"), make_image([("circle", 640, 360, 30)])
    )
    detector = OpenCVDetector()
    with pytest.raises(DetectorError, match="No usable part contour"):
        detector.configure(load_reference_set(tmp_path, "round_part"), 0.6)
