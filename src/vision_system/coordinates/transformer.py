"""Transforms image pixel coordinates into robot coordinates.

Setup assumption (confirmed): fixed camera perpendicular above a flat
workspace, constant pick height -> a 3x3 planar homography maps
(x_px, y_px) to robot (x_mm, y_mm); Z comes from configuration.

Calibration data acquisition (point collection) is Milestone 7.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from vision_system.models.data import RobotCoordinate


class TransformError(Exception):
    """Raised when a coordinate cannot be transformed."""


class CoordinateTransformer(ABC):
    """Interface separating detection from the calibration method used."""

    @abstractmethod
    def image_to_robot(self, x_px: float, y_px: float) -> RobotCoordinate:
        """Convert an image pixel coordinate to a robot coordinate."""


class IdentityTransformer(CoordinateTransformer):
    """Development transformer: passes pixels through unchanged (Z fixed).

    Used until a real calibration exists so the pipeline can run end-to-end.
    """

    def __init__(self, z: float = 0.0) -> None:
        self._z = z

    def image_to_robot(self, x_px: float, y_px: float) -> RobotCoordinate:
        return RobotCoordinate(x=x_px, y=y_px, z=self._z)


class HomographyTransformer(CoordinateTransformer):
    """Planar homography (pixel plane -> robot XY plane) with constant Z."""

    def __init__(self, homography: np.ndarray, z: float) -> None:
        matrix = np.asarray(homography, dtype=float)
        if matrix.shape != (3, 3):
            raise TransformError(f"Homography must be 3x3, got {matrix.shape}")
        self._h = matrix
        self._z = z

    def image_to_robot(self, x_px: float, y_px: float) -> RobotCoordinate:
        vec = self._h @ np.array([x_px, y_px, 1.0])
        if abs(vec[2]) < 1e-12:
            raise TransformError(f"Degenerate homography result for ({x_px}, {y_px})")
        return RobotCoordinate(x=vec[0] / vec[2], y=vec[1] / vec[2], z=self._z)
