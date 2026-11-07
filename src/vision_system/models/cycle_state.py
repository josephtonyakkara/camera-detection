"""Pick-cycle state tracking (exchange contract for frontends).

Handshake-centric states; the camera runs continuously, so per-frame stages
are only recorded while a cycle is advancing. Repeated sets of the same state
update the detail without flooding the history.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from enum import Enum
from typing import Any


class CycleState(Enum):
    WAITING_FOR_REQUEST = "waiting_for_request"
    REQUEST_RECEIVED = "request_received"
    FRAME_CAPTURED = "frame_captured"
    PARTS_DETECTED = "parts_detected"
    NO_PARTS_FOUND = "no_parts_found"
    COORDS_TRANSFORMED = "coordinates_transformed"
    TARGET_PUBLISHED = "target_published"
    PICKING = "picking"
    PICK_COMPLETE = "pick_complete"
    COOLDOWN = "cooldown"
    ERROR = "error"


class CycleTracker:
    """Thread-safe current state + transition history ring buffer."""

    def __init__(self, history_size: int = 100) -> None:
        self._lock = threading.Lock()
        self._state = CycleState.WAITING_FOR_REQUEST
        self._detail = ""
        self._since = time.time()
        self._history: deque[dict[str, Any]] = deque(maxlen=history_size)

    def set(self, state: CycleState, detail: str = "") -> None:
        """Transition to ``state``; same-state calls only refresh the detail."""
        with self._lock:
            if state is self._state:
                self._detail = detail or self._detail
                return
            now = time.time()
            self._history.append(
                {
                    "state": self._state.value,
                    "detail": self._detail,
                    "entered": self._since,
                    "duration_s": round(now - self._since, 3),
                }
            )
            self._state = state
            self._detail = detail
            self._since = now

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self._state.value,
                "detail": self._detail,
                "since": self._since,
                "history": list(self._history)[::-1],  # newest first
            }
