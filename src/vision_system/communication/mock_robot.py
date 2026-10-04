"""Mock robot for development and tests without hardware."""

from __future__ import annotations

import logging

from vision_system.communication.base import RobotError, RobotInterface
from vision_system.models.data import PickTarget, RobotState, RobotStatus

logger = logging.getLogger(__name__)


class MockRobot(RobotInterface):
    """Accepts targets, records them, and reports READY immediately."""

    def __init__(self) -> None:
        self._connected = False
        self.received_targets: list[PickTarget] = []
        self.last_published_count: int | None = None

    def connect(self) -> None:
        self._connected = True
        logger.info("MockRobot connected")

    def send_pick_target(self, target: PickTarget) -> None:
        if not self._connected:
            raise RobotError("MockRobot is not connected")
        self.received_targets.append(target)
        logger.info(
            "MockRobot received target %d at (%.1f, %.1f, %.1f)",
            target.target_id,
            target.coordinate.x,
            target.coordinate.y,
            target.coordinate.z,
        )

    def get_robot_status(self) -> RobotStatus:
        if not self._connected:
            return RobotStatus(state=RobotState.DISCONNECTED)
        last = self.received_targets[-1].target_id if self.received_targets else None
        return RobotStatus(state=RobotState.READY, last_pick_target_id=last)

    def is_robot_ready(self) -> bool:
        return self._connected

    def publish_detection_count(self, count: int) -> None:
        self.last_published_count = count

    def disconnect(self) -> None:
        self._connected = False
        logger.info("MockRobot disconnected")
