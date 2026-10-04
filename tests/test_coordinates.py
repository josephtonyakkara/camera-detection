"""Tests for coordinate transformation."""

from __future__ import annotations

import numpy as np
import pytest

from vision_system.coordinates.transformer import (
    HomographyTransformer,
    IdentityTransformer,
    TransformError,
)


def test_identity_passes_pixels_through() -> None:
    t = IdentityTransformer(z=-50.0)
    coord = t.image_to_robot(320.5, 240.0)
    assert (coord.x, coord.y, coord.z) == (320.5, 240.0, -50.0)


def test_homography_scale_and_translate() -> None:
    # 0.5 mm/px scale with (100, 200) mm offset
    h = np.array([[0.5, 0, 100], [0, 0.5, 200], [0, 0, 1]])
    t = HomographyTransformer(h, z=-10.0)
    coord = t.image_to_robot(200, 400)
    assert coord.x == pytest.approx(200.0)
    assert coord.y == pytest.approx(400.0)
    assert coord.z == -10.0


def test_invalid_matrix_shape_rejected() -> None:
    with pytest.raises(TransformError):
        HomographyTransformer(np.eye(2), z=0.0)
