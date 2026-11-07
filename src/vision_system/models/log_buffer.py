"""Thread-safe ring buffer of log records (exchange contract for frontends).

Attached as a logging.Handler by setup_logging(); the webapp reads records
incrementally by sequence number. vision_system never imports the webapp.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Any


class LogBuffer(logging.Handler):
    """Keeps the newest ``capacity`` log records in memory."""

    def __init__(self, capacity: int = 500) -> None:
        super().__init__(level=logging.DEBUG)
        self._lock_records = threading.Lock()
        self._records: deque[dict[str, Any]] = deque(maxlen=capacity)
        self._seq = 0

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
        except Exception:  # malformed format args must never kill logging
            message = str(record.msg)
        with self._lock_records:
            self._seq += 1
            self._records.append(
                {
                    "seq": self._seq,
                    "ts": record.created,
                    "level": record.levelname,
                    "levelno": record.levelno,
                    "logger": record.name,
                    "message": message,
                }
            )

    def get_records(
        self,
        since: int = 0,
        min_levelno: int = logging.DEBUG,
        module: str = "",
    ) -> list[dict[str, Any]]:
        """Records with seq > since, filtered by level and logger-name substring."""
        with self._lock_records:
            snapshot = list(self._records)
        return [
            r
            for r in snapshot
            if r["seq"] > since
            and r["levelno"] >= min_levelno
            and (module.lower() in r["logger"].lower() if module else True)
        ]

    @property
    def last_seq(self) -> int:
        with self._lock_records:
            return self._seq
