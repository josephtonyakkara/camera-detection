"""Hardware smoke tests for the real USB camera.

Run with: pytest -m hardware
Requires a physical camera at the configured device index.
"""

from __future__ import annotations

import numpy as np
import pytest

from vision_system.camera.manager import CameraManager
from vision_system.config.loader import load_config

pytestmark = pytest.mark.hardware


@pytest.fixture(scope="module")
def camera() -> CameraManager:
    manager = CameraManager(load_config().camera)
    manager.start()
    yield manager
    manager.stop()


def test_camera_opens_and_streams(camera: CameraManager) -> None:
    assert camera.is_running()


def test_frame_has_expected_structure(camera: CameraManager) -> None:
    frame = camera.get_frame()
    assert isinstance(frame.image, np.ndarray)
    assert frame.image.shape == (frame.height, frame.width, 3)
    assert frame.image.dtype == np.uint8
    assert frame.color_format == "BGR"
    assert frame.width > 0 and frame.height > 0
    assert frame.timestamp > 0


def test_frame_ids_are_monotonic(camera: CameraManager) -> None:
    ids = [camera.get_frame().frame_id for _ in range(5)]
    assert ids == sorted(ids)
    assert len(set(ids)) == 5


def test_frames_contain_signal_not_black(camera: CameraManager) -> None:
    # a covered/broken sensor typically yields a near-constant image
    frame = camera.get_frame()
    assert frame.image.std() > 1.0, "Frame looks blank; is the lens covered?"
