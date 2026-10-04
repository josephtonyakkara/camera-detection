"""Tests for the web dashboard: LiveState and FastAPI endpoints."""

from __future__ import annotations

import time

import numpy as np
from fastapi.testclient import TestClient

from vision_system.models.data import (
    DetectionResult,
    PickTarget,
    RobotCoordinate,
    RobotState,
    RobotStatus,
)
from vision_system.models.live_state import LiveState
from webapp.server import create_app


def make_result(count: int = 2) -> DetectionResult:
    from tests.conftest import make_detection

    return DetectionResult(
        frame_id=42,
        timestamp=time.time(),
        image_width=1280,
        image_height=720,
        detections=[make_detection(100 * i + 50, 60) for i in range(count)],
    )


def make_target() -> PickTarget:
    return PickTarget(
        target_id=1,
        coordinate=RobotCoordinate(10.0, 20.0, -30.0),
        class_name="round_part",
        confidence=0.9,
        source_frame_id=42,
    )


def publish_sample(state: LiveState) -> None:
    state.publish(
        jpeg=b"\xff\xd8fakejpeg\xff\xd9",
        result=make_result(),
        targets=[make_target()],
        robot_status=RobotStatus(state=RobotState.READY),
        fps=24.5,
    )


def test_live_state_initial_status() -> None:
    status = LiveState().get_status()
    assert status["running"] is False
    assert status["detection_count"] == 0
    assert LiveState().get_jpeg() is None


def test_live_state_publish_and_snapshot() -> None:
    state = LiveState()
    publish_sample(state)
    status = state.get_status()
    assert status["running"] is True
    assert status["frame_id"] == 42
    assert status["detection_count"] == 2
    assert status["targets"][0] == {"target_id": 1, "x": 10.0, "y": 20.0, "z": -30.0}
    assert status["robot_state"] == "ready"
    assert status["fps"] == 24.5
    assert state.get_jpeg().startswith(b"\xff\xd8")


def test_live_state_mark_stopped_keeps_last_data() -> None:
    state = LiveState()
    publish_sample(state)
    state.mark_stopped()
    status = state.get_status()
    assert status["running"] is False
    assert status["detection_count"] == 2


def test_status_endpoint() -> None:
    state = LiveState()
    publish_sample(state)
    client = TestClient(create_app(state))
    payload = client.get("/api/status").json()
    assert payload["detection_count"] == 2
    assert payload["robot_state"] == "ready"


def test_index_serves_dashboard() -> None:
    client = TestClient(create_app(LiveState()))
    response = client.get("/")
    assert response.status_code == 200
    assert "Vision System" in response.text
    assert "/stream" in response.text
