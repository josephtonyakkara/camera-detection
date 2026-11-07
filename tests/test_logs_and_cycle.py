"""Tests for the log buffer, logs API, cycle tracker, and cycle API."""

from __future__ import annotations

import logging
import time

from fastapi import FastAPI
from fastapi.testclient import TestClient

from vision_system.app_control import AppControl, PipelineState, PipelineStatus
from vision_system.models.cycle_state import CycleState, CycleTracker
from vision_system.models.log_buffer import LogBuffer
from webapp.routers.cycle import make_cycle_router
from webapp.routers.logs import make_logs_router


# --- LogBuffer ---


def make_buffer_with_logs(capacity: int = 10) -> LogBuffer:
    buffer = LogBuffer(capacity)
    log = logging.getLogger("test.camera")
    log.setLevel(logging.DEBUG)
    log.propagate = False
    log.handlers = [buffer]
    log.debug("debug msg")
    log.info("camera opened")
    log.warning("reconnect attempt")
    logging.getLogger("test.robot").handlers = [buffer]
    robot = logging.getLogger("test.robot")
    robot.setLevel(logging.DEBUG)
    robot.propagate = False
    robot.error("send failed")
    return buffer


def test_buffer_captures_and_sequences() -> None:
    buffer = make_buffer_with_logs()
    records = buffer.get_records()
    assert [r["message"] for r in records] == [
        "debug msg", "camera opened", "reconnect attempt", "send failed",
    ]
    assert [r["seq"] for r in records] == [1, 2, 3, 4]
    assert buffer.last_seq == 4


def test_buffer_level_and_module_filters() -> None:
    buffer = make_buffer_with_logs()
    warnings = buffer.get_records(min_levelno=logging.WARNING)
    assert [r["message"] for r in warnings] == ["reconnect attempt", "send failed"]
    camera_only = buffer.get_records(module="camera")
    assert all("camera" in r["logger"] for r in camera_only)
    assert len(camera_only) == 3


def test_buffer_incremental_since() -> None:
    buffer = make_buffer_with_logs()
    assert [r["seq"] for r in buffer.get_records(since=2)] == [3, 4]


def test_buffer_capacity_rotation() -> None:
    buffer = LogBuffer(capacity=3)
    log = logging.getLogger("test.rotate")
    log.setLevel(logging.INFO)
    log.propagate = False
    log.handlers = [buffer]
    for i in range(5):
        log.info("msg %d", i)
    records = buffer.get_records()
    assert len(records) == 3
    assert records[0]["message"] == "msg 2"  # oldest two rotated out
    assert buffer.last_seq == 5


def test_logs_api() -> None:
    app = FastAPI()
    app.include_router(make_logs_router(make_buffer_with_logs()))
    client = TestClient(app)
    payload = client.get("/api/logs?level=WARNING").json()
    assert payload["last_seq"] == 4
    assert [r["level"] for r in payload["records"]] == ["WARNING", "ERROR"]
    payload = client.get("/api/logs?since=3").json()
    assert len(payload["records"]) == 1


# --- CycleTracker ---


def test_tracker_records_transitions_with_duration() -> None:
    tracker = CycleTracker()
    tracker.set(CycleState.REQUEST_RECEIVED)
    time.sleep(0.01)
    tracker.set(CycleState.TARGET_PUBLISHED, "T1")
    snapshot = tracker.snapshot()
    assert snapshot["state"] == "target_published"
    assert snapshot["detail"] == "T1"
    assert [h["state"] for h in snapshot["history"]] == [
        "request_received", "waiting_for_request",
    ]  # newest first
    assert snapshot["history"][0]["duration_s"] > 0


def test_tracker_same_state_updates_detail_without_history() -> None:
    tracker = CycleTracker()
    tracker.set(CycleState.PICKING, "T1")
    tracker.set(CycleState.PICKING, "T1 still")
    snapshot = tracker.snapshot()
    assert snapshot["detail"] == "T1 still"
    assert len(snapshot["history"]) == 1  # only the initial waiting state


def test_tracker_history_capacity() -> None:
    tracker = CycleTracker(history_size=5)
    states = [CycleState.REQUEST_RECEIVED, CycleState.PICKING]
    for i in range(10):
        tracker.set(states[i % 2], str(i))
    assert len(tracker.snapshot()["history"]) == 5


def test_cycle_api_unavailable_and_available() -> None:
    class Control(AppControl):
        snapshot: dict | None = None

        def get_status(self) -> PipelineStatus:
            return PipelineStatus(state=PipelineState.RUNNING)

        def mark_restart_required(self) -> None: ...
        def request_restart(self) -> None: ...
        def get_cycle_snapshot(self) -> dict | None:
            return self.snapshot

    control = Control()
    app = FastAPI()
    app.include_router(make_cycle_router(control))
    client = TestClient(app)

    assert client.get("/api/cycle").json()["state"] == "unavailable"

    tracker = CycleTracker()
    tracker.set(CycleState.PICKING, "T7")
    control.snapshot = tracker.snapshot()
    payload = client.get("/api/cycle").json()
    assert payload["state"] == "picking"
    assert payload["detail"] == "T7"
