"""Robot communication layer: protocol implementations behind RobotInterface.

Vision code depends only on RobotInterface; protocols (OPC UA now, e.g.
Modbus later) are interchangeable implementations selected via config.
"""

from vision_system.communication.base import RobotError, RobotInterface
from vision_system.communication.mock_robot import MockRobot

__all__ = ["MockRobot", "RobotError", "RobotInterface"]
