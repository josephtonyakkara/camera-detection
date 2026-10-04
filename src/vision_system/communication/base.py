"""Abstract robot interface.

Implementations (mock, OPC UA server) expose pick targets to the robot
controller. Communication state is always explicit: sending never silently
succeeds while the robot is unreachable.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from vision_system.app_control import CommunicationInfo
from vision_system.models.data import PickTarget, RobotStatus


class RobotError(Exception):
    """Raised for robot communication failures."""


class RobotInterface(ABC):
    """Common interface for all robot communication implementations."""

    @abstractmethod
    def connect(self) -> None:
        """Establish communication (or start the server for server-mode impls)."""

    @abstractmethod
    def send_pick_target(self, target: PickTarget) -> None:
        """Publish/send a pick target to the robot.

        Raises:
            RobotError: if the target cannot be delivered.
        """

    @abstractmethod
    def get_robot_status(self) -> RobotStatus:
        """Return the current robot communication/readiness state."""

    @abstractmethod
    def is_robot_ready(self) -> bool:
        """True when the robot can accept a new pick target."""

    def publish_detection_count(self, count: int) -> None:
        """Expose the live part count to the robot/HMI. Optional; default no-op."""

    def get_communication_info(self) -> CommunicationInfo | None:
        """Introspection snapshot for frontends. Optional; default None."""
        return None

    @abstractmethod
    def disconnect(self) -> None:
        """Shut down communication. Must be idempotent."""
