"""Homography calibration: computation, persistence, and transformer loading.

Calibration maps image pixels to robot XY (mm) on the workspace plane using
point pairs collected with scripts/calibrate.py. The result is stored as YAML
(path from system.calibration_file) and loaded at application start.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import yaml

from vision_system.coordinates.transformer import (
    CoordinateTransformer,
    HomographyTransformer,
    IdentityTransformer,
    TransformError,
)

logger = logging.getLogger(__name__)


class CalibrationError(Exception):
    """Raised when calibration data is insufficient or invalid."""


@dataclass(frozen=True)
class CalibrationPoint:
    """One measured correspondence: image pixel -> robot coordinate (mm)."""

    pixel_x: float
    pixel_y: float
    robot_x: float
    robot_y: float


@dataclass(frozen=True)
class CalibrationResult:
    homography: np.ndarray
    points: list[CalibrationPoint]
    rms_error_mm: float
    max_error_mm: float


def compute_homography(points: list[CalibrationPoint]) -> CalibrationResult:
    """Fit a pixel->robot homography (least squares for >4 points).

    Raises:
        CalibrationError: fewer than 4 points or degenerate geometry.
    """
    if len(points) < 4:
        raise CalibrationError(f"Need at least 4 calibration points, got {len(points)}")
    src = np.array([[p.pixel_x, p.pixel_y] for p in points], dtype=np.float64)
    dst = np.array([[p.robot_x, p.robot_y] for p in points], dtype=np.float64)
    homography, _ = cv2.findHomography(src, dst, method=0)
    if homography is None:
        raise CalibrationError("Degenerate point configuration (collinear points?)")

    errors = []
    for point in points:
        vec = homography @ np.array([point.pixel_x, point.pixel_y, 1.0])
        px, py = vec[0] / vec[2], vec[1] / vec[2]
        errors.append(float(np.hypot(px - point.robot_x, py - point.robot_y)))
    rms = float(np.sqrt(np.mean(np.square(errors))))
    return CalibrationResult(
        homography=homography,
        points=list(points),
        rms_error_mm=rms,
        max_error_mm=max(errors),
    )


def save_calibration(path: Path, result: CalibrationResult) -> None:
    """Persist a calibration result as YAML."""
    payload = {
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "rms_error_mm": round(result.rms_error_mm, 4),
        "max_error_mm": round(result.max_error_mm, 4),
        "points": [
            {"pixel": [p.pixel_x, p.pixel_y], "robot": [p.robot_x, p.robot_y]}
            for p in result.points
        ],
        "homography": result.homography.tolist(),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    logger.info("Calibration saved to %s (RMS %.3f mm)", path, result.rms_error_mm)


def load_calibration(path: Path) -> np.ndarray:
    """Load the homography matrix from a calibration YAML file.

    Raises:
        CalibrationError: file missing or malformed.
    """
    if not path.exists():
        raise CalibrationError(f"Calibration file not found: {path}")
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        matrix = np.array(data["homography"], dtype=np.float64)
    except (yaml.YAMLError, KeyError, TypeError, ValueError) as exc:
        raise CalibrationError(f"Invalid calibration file {path}: {exc}") from exc
    if matrix.shape != (3, 3):
        raise CalibrationError(f"Calibration matrix must be 3x3, got {matrix.shape}")
    return matrix


def load_transformer(calibration_file: Path, pick_z: float) -> CoordinateTransformer:
    """Build the coordinate transformer for the application.

    Returns a HomographyTransformer when a valid calibration exists, otherwise
    falls back to IdentityTransformer (pixel passthrough) with a warning so
    development can continue before the workspace is calibrated.
    """
    try:
        matrix = load_calibration(calibration_file)
        logger.info("Loaded calibration from %s", calibration_file)
        return HomographyTransformer(matrix, z=pick_z)
    except (CalibrationError, TransformError) as exc:
        logger.warning(
            "No usable calibration (%s); using IdentityTransformer — "
            "robot coordinates are raw pixels until calibrated",
            exc,
        )
        return IdentityTransformer(z=pick_z)
