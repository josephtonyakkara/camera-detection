"""Tests for the camera manager using a fake driver (no hardware)."""

from __future__ import annotations

import time

import numpy as np
import pytest

from vision_system.camera.base import CameraError, CameraInterface
from vision_system.camera.manager import CameraManager, create_camera
from vision_system.config.models import CameraConfig
from vision_system.models.data import FrameData


class FakeCamera(CameraInterface):
    def __init__(self, fail_opens: int = 0, fail_reads: int = 0) -> None:
        self._fail_opens = fail_opens
        self._fail_reads = fail_reads
        self._open = False
        self._frame_id = 0

    def open(self, config: CameraConfig) -> None:
        if self._fail_opens > 0:
            self._fail_opens -= 1
            raise CameraError("simulated open failure")
        self._open = True

    def get_frame(self) -> FrameData:
        if not self._open:
            raise CameraError("not open")
        if self._fail_reads > 0:
            self._fail_reads -= 1
            raise CameraError("simulated read failure")
        self._frame_id += 1
        return FrameData(
            frame_id=self._frame_id,
            timestamp=time.time(),
            image=np.zeros((4, 4, 3), dtype=np.uint8),
            width=4,
            height=4,
        )

    def is_open(self) -> bool:
        return self._open

    def close(self) -> None:
        self._open = False


def make_config() -> CameraConfig:
    return CameraConfig(reconnect_attempts=3, reconnect_delay_s=0.0)


def test_start_retries_then_succeeds() -> None:
    manager = CameraManager(make_config(), FakeCamera(fail_opens=2))
    manager.start()
    assert manager.is_running()


def test_start_fails_after_max_attempts() -> None:
    manager = CameraManager(make_config(), FakeCamera(fail_opens=99))
    with pytest.raises(CameraError, match="could not be started"):
        manager.start()


def test_get_frame_reconnects_on_read_failure() -> None:
    manager = CameraManager(make_config(), FakeCamera(fail_reads=1))
    manager.start()
    frame = manager.get_frame()
    assert frame.frame_id > 0


def test_stop_is_clean() -> None:
    manager = CameraManager(make_config(), FakeCamera())
    manager.start()
    manager.stop()
    assert not manager.is_running()


def test_unknown_camera_type_rejected() -> None:
    with pytest.raises(CameraError, match="Unknown camera type"):
        create_camera("quantum")
