"""Tests for the robot interface contract using the mock implementation."""

from __future__ import annotations

import pytest

from vision_system.models.data import PickTarget, RobotCoordinate, RobotState
from vision_system.communication.base import RobotError
from vision_system.communication.mock_robot import MockRobot


def make_target(target_id: int = 1) -> PickTarget:
    return PickTarget(
        target_id=target_id,
        coordinate=RobotCoordinate(10.0, 20.0, -30.0),
        class_name="round_part",
        confidence=0.9,
        source_frame_id=1,
    )


def test_disconnected_robot_rejects_targets() -> None:
    robot = MockRobot()
    assert robot.get_robot_status().state is RobotState.DISCONNECTED
    with pytest.raises(RobotError):
        robot.send_pick_target(make_target())


def test_connected_robot_accepts_and_tracks_targets() -> None:
    robot = MockRobot()
    robot.connect()
    assert robot.is_robot_ready()
    robot.send_pick_target(make_target(7))
    status = robot.get_robot_status()
    assert status.state is RobotState.READY
    assert status.last_pick_target_id == 7
    assert len(robot.received_targets) == 1


def test_disconnect_is_idempotent() -> None:
    robot = MockRobot()
    robot.connect()
    robot.disconnect()
    robot.disconnect()
    assert not robot.is_robot_ready()
