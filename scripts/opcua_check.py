"""OPC UA server live test (pre-M11), no camera required.

Starts the configured OPC UA server standalone and simulates the vision side
so an external client (e.g. UaExpert) can exercise the full handshake:

    1. Run:  python scripts/opcua_check.py
    2. In UaExpert connect to  opc.tcp://localhost:5000  (Anonymous, no security)
    3. Browse Objects/VisionSystem
    4. mode=request: write TargetRequest=True  -> a dummy target is published
       (TargetReady=True, TargetX/Y/Z filled)
    5. Write PickComplete=True -> flags reset, StatusCode back to 1 (ready)

Ctrl+C stops the server.
"""

from __future__ import annotations

import itertools
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vision_system.communication.opcua_server import OpcUaRobotServer
from vision_system.config.loader import load_config
from vision_system.models.data import PickTarget, RobotCoordinate
from vision_system.utils.logging_setup import setup_logging

logger = logging.getLogger("opcua_check")


def main() -> int:
    config = load_config()
    setup_logging(config.system.log_level)
    opcua = config.communication.opcua

    robot = OpcUaRobotServer(opcua)
    robot.connect()
    robot.publish_detection_count(3)  # dummy count for the DetectedCount node
    logger.info(
        "Server live at %s (mode=%s). Connect UaExpert to opc.tcp://localhost:%s",
        opcua.endpoint,
        opcua.mode,
        opcua.endpoint.rsplit(":", 1)[-1].rstrip("/"),
    )
    if opcua.mode == "request":
        logger.info("Write TargetRequest=True in UaExpert to receive a dummy target")

    ids = itertools.count(1)
    try:
        while True:
            if robot.is_robot_ready():
                target_id = next(ids)
                # dummy coordinates vary per target so updates are visible
                target = PickTarget(
                    target_id=target_id,
                    coordinate=RobotCoordinate(
                        x=25.0 + target_id, y=-10.0 - target_id, z=config.robot.pick_z
                    ),
                    class_name="test_part",
                    confidence=1.0,
                    source_frame_id=0,
                )
                robot.send_pick_target(target)
                logger.info("Dummy target %d published; write PickComplete=True to finish", target_id)
            time.sleep(0.2)
    except KeyboardInterrupt:
        logger.info("Stopping")
    finally:
        robot.disconnect()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
