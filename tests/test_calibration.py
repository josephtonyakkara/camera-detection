"""Tests for homography calibration computation, persistence, and loading."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from vision_system.coordinates.calibration import (
    CalibrationError,
    CalibrationPoint,
    compute_homography,
    load_calibration,
    load_transformer,
    save_calibration,
)
from vision_system.coordinates.transformer import HomographyTransformer, IdentityTransformer


def make_points(scale: float = 0.5, dx: float = 100.0, dy: float = -50.0) -> list[CalibrationPoint]:
    """Point pairs following robot = scale*pixel + offset."""
    pixels = [(100, 100), (1100, 120), (1080, 620), (150, 600), (640, 360)]
    return [
        CalibrationPoint(px, py, scale * px + dx, scale * py + dy) for px, py in pixels
    ]


def test_compute_homography_recovers_transform() -> None:
    result = compute_homography(make_points())
    assert result.rms_error_mm < 1e-6
    assert result.max_error_mm < 1e-6
    # verify an unseen point maps correctly
    vec = result.homography @ np.array([500.0, 250.0, 1.0])
    assert vec[0] / vec[2] == pytest.approx(0.5 * 500 + 100)
    assert vec[1] / vec[2] == pytest.approx(0.5 * 250 - 50)


def test_too_few_points_rejected() -> None:
    with pytest.raises(CalibrationError, match="at least 4"):
        compute_homography(make_points()[:3])


def test_collinear_points_rejected() -> None:
    points = [CalibrationPoint(x, 100, x * 0.5, 50) for x in (100, 300, 500, 700)]
    with pytest.raises(CalibrationError, match="Degenerate"):
        compute_homography(points)


def test_save_load_roundtrip(tmp_path: Path) -> None:
    result = compute_homography(make_points())
    path = tmp_path / "calib" / "homography.yaml"
    save_calibration(path, result)
    matrix = load_calibration(path)
    assert np.allclose(matrix, result.homography)


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(CalibrationError, match="not found"):
        load_calibration(tmp_path / "nope.yaml")


def test_load_invalid_file_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("homography: [1, 2, 3]\n")
    with pytest.raises(CalibrationError, match="must be 3x3"):
        load_calibration(bad)


def test_load_transformer_with_calibration(tmp_path: Path) -> None:
    path = tmp_path / "homography.yaml"
    save_calibration(path, compute_homography(make_points()))
    transformer = load_transformer(path, pick_z=-40.0)
    assert isinstance(transformer, HomographyTransformer)
    coord = transformer.image_to_robot(200, 400)
    assert coord.x == pytest.approx(0.5 * 200 + 100)
    assert coord.y == pytest.approx(0.5 * 400 - 50)
    assert coord.z == -40.0


def test_load_transformer_fallback_without_calibration(tmp_path: Path) -> None:
    transformer = load_transformer(tmp_path / "missing.yaml", pick_z=-40.0)
    assert isinstance(transformer, IdentityTransformer)
    assert transformer.image_to_robot(10, 20).z == -40.0
