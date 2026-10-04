"""Thread-safe snapshot of the latest pipeline output (exchange contract).

The pipeline thread publishes; external consumers (e.g. the webapp package)
only read. This is one of the neutral contracts that keep presentation fully
decoupled from vision processing — vision_system never imports the webapp.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from vision_system.models.data import DetectionResult, PickTarget, RobotStatus


class LiveState:
    """Latest annotated frame (JPEG) and pipeline status, guarded by a lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jpeg: bytes | None = None
        self._status: dict[str, Any] = {
            "running": False,
            "frame_id": None,
            "detection_count": 0,
            "detections": [],
            "targets": [],
            "robot_state": "disconnected",
            "pending_target_id": None,
            "fps": 0.0,
            "updated_at": None,
        }

    def publish(
        self,
        jpeg: bytes,
        result: DetectionResult,
        targets: list[PickTarget],
        robot_status: RobotStatus,
        fps: float,
        pending_target_id: int | None = None,
    ) -> None:
        status = {
            "running": True,
            "frame_id": result.frame_id,
            "detection_count": result.detection_count,
            "detections": [
                {
                    "class_name": d.class_name,
                    "confidence": round(d.confidence, 3),
                    "x_px": round(d.center_x_px, 1),
                    "y_px": round(d.center_y_px, 1),
                }
                for d in result.detections
            ],
            "targets": [
                {
                    "target_id": t.target_id,
                    "x": round(t.coordinate.x, 2),
                    "y": round(t.coordinate.y, 2),
                    "z": round(t.coordinate.z, 2),
                }
                for t in targets
            ],
            "robot_state": robot_status.state.value,
            "pending_target_id": pending_target_id,
            "fps": round(fps, 1),
            "updated_at": time.time(),
        }
        with self._lock:
            self._jpeg = jpeg
            self._status = status

    def mark_stopped(self) -> None:
        with self._lock:
            self._status = {**self._status, "running": False}

    def get_jpeg(self) -> bytes | None:
        with self._lock:
            return self._jpeg

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status)
